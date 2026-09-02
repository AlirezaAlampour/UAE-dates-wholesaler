"""Minimal WhatsApp Cloud API client for text messages."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v26.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


async def send_text(to: str, text: str) -> None:
    """Send one text message through the official WhatsApp Cloud API."""
    token = os.getenv("WA_TOKEN")
    phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")

    missing = [
        name
        for name, value in (
            ("WA_TOKEN", token),
            ("WA_PHONE_NUMBER_ID", phone_number_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text,
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.is_error:
        logger.error(
            "WhatsApp Cloud API rejected text message: status=%s body=%s",
            response.status_code,
            response.text,
        )
        response.raise_for_status()

    response_data = response.json()
    sent_message_id = (response_data.get("messages") or [{}])[0].get("id", "unknown")
    logger.info("Echo sent through WhatsApp Cloud API: message_id=%s", sent_message_id)
