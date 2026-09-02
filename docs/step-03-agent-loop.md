# Step 03 — Claude Agent Loop

## Goal

Replace text echoing with a minimal `claude-sonnet-5` reply path that can call four deterministic demo tools, while preserving the known-good webhook, deduplication, logging, replay safety, and official Meta sender.

## Files changed

- `app/agent.py` — Claude Messages API loop, tool definitions, prompt caching, and in-memory history.
- `app/tools.py` — deterministic fake implementations of the four future tools.
- `app/main.py` — passes inbound text to the agent and sends or suppresses its final reply.
- `.env.example`, `requirements.txt` — `ANTHROPIC_API_KEY` and the Anthropic SDK.
- `docs/step-03-agent-loop.md` — this checkpoint.

## Agent loop

`generate_reply(contact_id, customer_text)` calls `claude-sonnet-5` with a small temporary system instruction and the four Anthropic tool schemas. When Claude returns one or more `tool_use` blocks, the matching local stubs run and their JSON results return in `tool_result` blocks. The loop stops on final text or fails after five API iterations.

The static system block and final tool definition contain ephemeral cache breakpoints, covering the system prompt and tool-definition prefix. The full Step 4 bilingual prompt is intentionally absent.

## History and fake tools

History is a module-level dictionary keyed by WhatsApp sender ID. It retains the latest 10 completed user/assistant exchanges per sender and resets when the process restarts.

- `record_inquiry` returns `demo-lead-001`.
- `get_price_quote` uses a fixed variety-price map, 10 kg MOQ, and calculated fake total.
- `check_availability` returns 10:00 and 14:00 UAE-offset slots for the requested date.
- `book_meeting` returns fixed fake event/link data.

No Google service is called and no external state is written.

## Replay usage

With FastAPI running and `ANTHROPIC_API_KEY` configured:

```bash
.venv/bin/python scripts/replay.py text "hello"
.venv/bin/python scripts/replay.py text "What is the price of 20 kg of Medjool dates?"
.venv/bin/python scripts/replay.py text "Can I arrange a meeting tomorrow?"
```

Replay requests traverse the real `/webhook` parsing, logging, deduplication, history, Claude, and tool paths. The generated reply is logged, then `X-WA-Replay: 1` prevents any Meta send.

## Acceptance

Passed through a running Uvicorn HTTP endpoint using the existing replay CLI and a deterministic fake Anthropic client:

- Simple response with no tool.
- Price request called `get_price_quote`.
- Meeting request called `check_availability`.
- Inquiry request called `record_inquiry`.
- Same-sender second turn used prior name context; another sender did not receive that history.
- Duplicate message ID was ignored.
- Status callback was logged and ignored.
- Replay never invoked the mocked Meta sender.
- A non-replay webhook invoked mocked `send_text` with the agent reply.

Additional checks covered all four stub functions, the 10-turn cap, five-iteration guard, cached Anthropic request serialization, JSONL logging, webhook verification, dependency consistency, and Uvicorn startup. No real Anthropic API call was made because this workspace had no `ANTHROPIC_API_KEY`; live Claude behavior requires a configured key.

## Limitations and deferred work

- Tool data is fake and deterministic; Sheets and Calendar remain Step 5.
- The system prompt is intentionally minimal. Language matching, Gulf Arabic examples, qualification, escalation, and final sales behavior remain Step 4.
- History and deduplication are in memory and disappear on restart.
- Voice, approvals, follow-ups, database, state machine, dashboard, and all other Step 4+ work remain unimplemented.
