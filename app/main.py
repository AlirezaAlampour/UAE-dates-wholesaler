"""FastAPI entry point for the Step 1 WhatsApp echo loop."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.agent import generate_reply
from app.wa import send_text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="UAE Dates Wholesaler WhatsApp Echo Demo")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOUND_LOG_PATH = PROJECT_ROOT / "logs" / "inbound.jsonl"
REPLAY_HEADER = "X-WA-Replay"

# Demo-only state. Losing dedupe history on restart is acceptable for this MVP.
processed_message_ids: set[str] = set()


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request) -> PlainTextResponse:
    """Complete Meta's webhook verification handshake."""
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    expected_token = os.getenv("WA_VERIFY_TOKEN")

    if not expected_token:
        logger.error("Cannot verify webhook: WA_VERIFY_TOKEN is not configured")
        raise HTTPException(status_code=500, detail="Webhook verification is not configured")

    if mode != "subscribe" or verify_token != expected_token or challenge is None:
        logger.warning("Rejected invalid webhook verification request: mode=%r", mode)
        raise HTTPException(status_code=403, detail="Invalid webhook verification request")

    logger.info("Meta webhook verification succeeded")
    return PlainTextResponse(content=challenge)


@app.post("/webhook")
async def receive_webhook(request: Request) -> dict[str, str]:
    """Log webhook payloads and echo each new inbound text message."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Rejected webhook request with invalid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        logger.warning("Rejected webhook payload because its root is not an object")
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    _append_inbound_log(payload)

    replay_mode = request.headers.get(REPLAY_HEADER) == "1"
    if replay_mode:
        logger.info("Replay request detected; outbound WhatsApp sends are disabled")

    messages = list(_iter_messages(payload))
    if not messages:
        logger.info("Webhook contained no inbound messages; callback acknowledged and ignored")
        return {"status": "ignored"}

    logger.info("Webhook contains %d inbound message(s)", len(messages))
    for message in messages:
        await _handle_message(message, suppress_outbound=replay_mode)

    return {"status": "ok"}


def _append_inbound_log(payload: dict[str, Any]) -> None:
    INBOUND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INBOUND_LOG_PATH.open("a", encoding="utf-8") as log_file:
        json.dump(payload, log_file, ensure_ascii=False, separators=(",", ":"))
        log_file.write("\n")
    logger.info("Webhook payload appended to %s", INBOUND_LOG_PATH)


def _iter_messages(payload: dict[str, Any]):
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            for message in value.get("messages") or []:
                if isinstance(message, dict):
                    yield message


async def _handle_message(
    message: dict[str, Any],
    *,
    suppress_outbound: bool = False,
) -> None:
    message_id = message.get("id")
    sender = message.get("from")
    message_type = message.get("type")

    if message_type != "text":
        logger.info(
            "Ignoring non-text inbound message: id=%s type=%s",
            message_id or "missing",
            message_type or "missing",
        )
        return

    text = (message.get("text") or {}).get("body")
    if not message_id or not sender or not isinstance(text, str):
        logger.warning(
            "Ignoring malformed text message: id=%s sender_present=%s text_present=%s",
            message_id or "missing",
            bool(sender),
            isinstance(text, str),
        )
        return

    if message_id in processed_message_ids:
        logger.info("Ignoring duplicate inbound message: id=%s", message_id)
        return

    processed_message_ids.add(message_id)
    logger.info("Processing inbound text: id=%s from=%s", message_id, sender)

    try:
        reply = await generate_reply(contact_id=sender, customer_text=text)
        if suppress_outbound:
            logger.info(
                "Replay mode suppressed outbound WhatsApp send: id=%s reply=%s",
                message_id,
                reply,
            )
            return

        await send_text(to=sender, text=reply)
    except Exception:
        # Let Meta retry a transient failure instead of permanently deduping it.
        processed_message_ids.discard(message_id)
        logger.exception("Failed to process inbound message: id=%s", message_id)
        raise
