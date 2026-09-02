#!/usr/bin/env python3
"""Replay realistic WhatsApp webhook payloads through the HTTP endpoint."""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

DEFAULT_TARGET_URL = "http://127.0.0.1:18080/webhook"
TARGET_URL_ENV = "REPLAY_WEBHOOK_URL"
REPLAY_HEADER = "X-WA-Replay"

FAKE_SENDER = "15550100123"
FAKE_WABA_ID = "123456789012345"
FAKE_PHONE_NUMBER_ID = "123456789012345"
FAKE_DISPLAY_PHONE_NUMBER = "15550100999"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="POST synthesized or saved WhatsApp payloads to /webhook.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv(TARGET_URL_ENV, DEFAULT_TARGET_URL),
        help=f"webhook URL (default: ${TARGET_URL_ENV} or {DEFAULT_TARGET_URL})",
    )

    subparsers = parser.add_subparsers(dest="replay_type", required=True)

    text_parser = subparsers.add_parser("text", help="send a synthesized text message")
    text_parser.add_argument("text", help="text body to replay")
    text_parser.add_argument(
        "--message-id",
        help="fixed WhatsApp message ID (default: generate a unique replay ID)",
    )

    file_parser = subparsers.add_parser("file", help="send a saved JSON payload unchanged")
    file_parser.add_argument("path", type=Path, help="path to one JSON webhook payload")

    return parser


def synthesize_text_payload(text: str, message_id: str | None) -> dict[str, Any]:
    resolved_message_id = message_id or f"wamid.REPLAY.{uuid.uuid4().hex}"
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": FAKE_WABA_ID,
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": FAKE_DISPLAY_PHONE_NUMBER,
                                "phone_number_id": FAKE_PHONE_NUMBER_ID,
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Replay Customer"},
                                    "wa_id": FAKE_SENDER,
                                }
                            ],
                            "messages": [
                                {
                                    "from": FAKE_SENDER,
                                    "id": resolved_message_id,
                                    "timestamp": str(int(time.time())),
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def find_message_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

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
                if isinstance(message, dict) and message.get("id"):
                    return str(message["id"])
    return None


def load_replay(args: argparse.Namespace) -> tuple[str, Any, bytes]:
    if args.replay_type == "text":
        payload = synthesize_text_payload(args.text, args.message_id)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        return "synthesized text", payload, body

    try:
        body = args.path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read {args.path}: {exc}") from exc

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{args.path} is not one valid JSON payload: {exc}") from exc

    return f"saved file ({args.path})", payload, body


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        replay_label, payload, body = load_replay(args)
    except ValueError as exc:
        print(f"Replay error: {exc}", file=sys.stderr)
        return 2

    print(f"Target: {args.url}")
    print(f"Replay: {replay_label}")
    message_id = find_message_id(payload)
    if message_id:
        print(f"Message ID: {message_id}")
    sys.stdout.flush()

    try:
        response = httpx.post(
            args.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                REPLAY_HEADER: "1",
            },
            timeout=10.0,
        )
    except (httpx.RequestError, httpx.InvalidURL) as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP status: {response.status_code}")
    print(f"Response: {response.text or '<empty>'}")

    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(run())
