# Step 02 — Webhook Replay Harness

## Goal

Exercise WhatsApp webhook behavior locally through the real FastAPI `/webhook` HTTP endpoint without using a phone or sending a real WhatsApp reply.

## Implementation

- `scripts/replay.py text` builds a realistic inbound Meta text payload with a stable fake sender, current Unix timestamp, and generated or supplied message ID.
- `scripts/replay.py file` validates and posts one saved JSON payload without changing its body bytes.
- The target defaults to `http://127.0.0.1:18080/webhook` and can be changed with `--url` or `REPLAY_WEBHOOK_URL`.
- The CLI prints the target, replay type, available message ID, HTTP status, and response body. HTTP, URL, file, JSON, and network failures return non-zero.

## CLI examples

Start the existing app, then run:

```bash
.venv/bin/python scripts/replay.py text "hello"
.venv/bin/python scripts/replay.py text "مرحبا"
.venv/bin/python scripts/replay.py text "duplicate" --message-id wamid.REPLAY.fixed-1
.venv/bin/python scripts/replay.py file /path/to/payload.json
.venv/bin/python scripts/replay.py --url http://127.0.0.1:9000/webhook text "hello"
REPLAY_WEBHOOK_URL=http://127.0.0.1:9000/webhook .venv/bin/python scripts/replay.py text "hello"
```

`logs/inbound.jsonl` contains one JSON object per line. Extract the desired line into a `.json` file before using `file`; the whole multi-line JSONL file is not one webhook payload.

## Outbound safety

Every replay request includes `X-WA-Replay: 1`. `app/main.py` recognizes that marker after normal JSON logging and before message processing completes. Parsing and in-memory deduplication run normally, but the final `send_text` call is skipped with a clear log entry. Requests without the header retain the live-tested Step 1 Cloud API behavior. Replay mode therefore needs no Meta credentials.

Restart the app after pulling Step 2 before replaying saved payloads: an older Step 1 process does not know the replay marker, and a saved payload may contain a real sender number.

## Acceptance

Passed through a running FastAPI HTTP server:

- Synthesized English and Arabic text payloads.
- Saved JSON payload posted unchanged.
- Same fixed message ID sent twice; the second was logged and ignored as a duplicate.
- Status callback without `messages`; it was logged, acknowledged, and ignored.
- HTTP 404 and unreachable target; diagnostics were printed and the CLI exited `1`.
- Six successful replay requests produced six JSONL records.
- The server used a test sender that raises if called; every replay remained `200`, proving no outbound sender was invoked.

Known-good Step 1 behavior was regression-checked: verification, status ignoring, normal non-replay text sending through the injected sender, exact body preservation, duplicate suppression, Cloud API request construction, JSONL logging, and Uvicorn startup.

## Deferred

Claude, agent history, prompts, tools, Google integrations, voice notes, approvals, follow-ups, persistent state, and all Step 3+ work remain unimplemented.

## Troubleshooting and limitations

- Start the FastAPI server on the same port used in the replay URL (`18080` by default).
- Put global `--url` before the `text` or `file` subcommand.
- The `file` command accepts exactly one valid JSON value, not a complete multi-record JSONL file.
- Reusing a message ID in the same server process intentionally triggers deduplication; restart clears the in-memory set.
- A non-2xx response or connection error is a failed replay even when the server returns a useful response body.
