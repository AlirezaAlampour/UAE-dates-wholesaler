"""Minimal Claude tool-calling loop with in-memory conversation history."""

import json
import logging
import os
from typing import Any

from anthropic import AsyncAnthropic

from app import tools as demo_tools

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
MAX_AGENT_ITERATIONS = 5
MAX_HISTORY_TURNS = 10
MAX_RESPONSE_TOKENS = 1024

SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": (
            "You are a helpful sales assistant for a dates wholesaler. "
            "Use the provided tools when appropriate. "
            "Never fabricate tool results. Return one concise response."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]

TOOL_DEFINITIONS = [
    {
        "name": "record_inquiry",
        "description": "Record a qualified customer inquiry in the demo CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "variety": {"type": "string"},
                "quantity_kg": {"type": "number"},
                "packaging": {"type": "string"},
                "city": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": [
                "name",
                "variety",
                "quantity_kg",
                "packaging",
                "city",
                "notes",
            ],
        },
    },
    {
        "name": "get_price_quote",
        "description": "Get a deterministic demo price quote for a dates variety and quantity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variety": {"type": "string"},
                "quantity_kg": {"type": "number"},
            },
            "required": ["variety", "quantity_kg"],
        },
    },
    {
        "name": "check_availability",
        "description": "Get deterministic demo meeting slots for a date in YYYY-MM-DD format.",
        "input_schema": {
            "type": "object",
            "properties": {"date_iso": {"type": "string"}},
            "required": ["date_iso"],
        },
    },
    {
        "name": "book_meeting",
        "description": "Create a deterministic fake calendar booking after a slot is chosen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "start_iso": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["name", "phone", "start_iso", "notes"],
        },
        "cache_control": {"type": "ephemeral"},
    },
]

TOOL_HANDLERS = {
    "record_inquiry": demo_tools.record_inquiry,
    "get_price_quote": demo_tools.get_price_quote,
    "check_availability": demo_tools.check_availability,
    "book_meeting": demo_tools.book_meeting,
}

# Each item is one completed user/assistant exchange. Demo state resets on restart.
conversation_history: dict[str, list[dict[str, str]]] = {}

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client

    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing required environment variable: ANTHROPIC_API_KEY")
        _client = AsyncAnthropic(api_key=api_key)

    return _client


def _messages_for(contact_id: str, customer_text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in conversation_history.get(contact_id, []):
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": customer_text})
    return messages


def _run_tool(name: str, tool_input: dict[str, Any]) -> Any:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")

    logger.info("Agent tool called: name=%s", name)
    return handler(**tool_input)


def _save_turn(contact_id: str, customer_text: str, final_reply: str) -> None:
    turns = conversation_history.setdefault(contact_id, [])
    turns.append({"user": customer_text, "assistant": final_reply})
    del turns[:-MAX_HISTORY_TURNS]


async def generate_reply(contact_id: str, customer_text: str) -> str:
    """Run Claude until it returns final text or the iteration limit is reached."""
    logger.info("Agent request received: contact=%s", contact_id)
    messages = _messages_for(contact_id, customer_text)
    client = _get_client()

    for _ in range(MAX_AGENT_ITERATIONS):
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if tool_uses:
            tool_results = []
            for tool_use in tool_uses:
                try:
                    result = _run_tool(tool_use.name, tool_use.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                except Exception as exc:
                    logger.exception("Agent tool failed: name=%s", tool_use.name)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": str(exc),
                            "is_error": True,
                        }
                    )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        final_reply = "\n".join(
            block.text.strip()
            for block in response.content
            if block.type == "text" and block.text.strip()
        )
        if not final_reply:
            raise RuntimeError(
                f"Claude returned no final text (stop_reason={response.stop_reason})"
            )

        _save_turn(contact_id, customer_text, final_reply)
        logger.info("Agent final reply: contact=%s reply=%s", contact_id, final_reply)
        return final_reply

    raise RuntimeError(f"Claude exceeded the {MAX_AGENT_ITERATIONS}-iteration limit")
