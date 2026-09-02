# Step 01 — WhatsApp Echo Loop

## Goal

Prove the official Meta WhatsApp Cloud API path end to end: receive a sandbox text webhook, log it, and send the exact text back once.

## Implemented behavior

- `GET /webhook` validates `hub.mode` and `hub.verify_token`, then returns `hub.challenge` as plain text.
- `POST /webhook` appends valid JSON payloads to `logs/inbound.jsonl`.
- Status callbacks and payloads without an inbound `messages` array are acknowledged and ignored.
- Only inbound text messages are handled. The exact body is echoed to the sender through the official Cloud API.
- WhatsApp message IDs are deduplicated in memory. A failed send removes the ID so Meta can retry.

## Files

- `app/main.py` — FastAPI routes, JSONL logging, parsing, and deduplication.
- `app/wa.py` — official WhatsApp Cloud API text sender.
- `app/__init__.py` — application package marker.
- `.env.example` — required configuration template.
- `requirements.txt` — minimal runtime dependencies.
- `.gitignore`, `logs/.gitkeep` — keep secrets, runtime logs, and generated files out of Git while retaining the log directory.

## Environment

```dotenv
WA_TOKEN=
WA_PHONE_NUMBER_ID=
WA_VERIFY_TOKEN=
```

`WA_PHONE_NUMBER_ID` is the phone number ID, not the WABA ID. A temporary Meta token expires after 24 hours; use the intended System User token for a scheduled demo.

## Local startup

Port `8000` was already occupied in the development environment, so Step 1 uses `18080`:

```bash
cd /home/alireza/Projects/UAE-dates-wholesaler
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18080
```

## Webhook and tunnel

- Use a named Cloudflare tunnel with a stable hostname; do not use a changing quick-tunnel URL.
- Route `https://<stable-hostname>/webhook` to `http://127.0.0.1:18080`.
- In Meta **WhatsApp → Configuration**, set that HTTPS callback URL and the same value as `WA_VERIFY_TOKEN`, then verify and save.
- Under webhook fields, subscribe to `messages`; successful endpoint verification alone does not deliver message events.

## Checks and acceptance

Local checks passed:

- Python compilation and dependency consistency.
- Valid and invalid webhook verification.
- Status/no-message callback ignoring.
- Exact text echo, duplicate suppression, non-text ignoring, invalid JSON rejection, and JSONL logging using mocked sends.
- Cloud API URL, authorization header, and request body construction using a mocked HTTP client.
- Uvicorn startup on `127.0.0.1:18080`.

Live acceptance passed against the real Meta WhatsApp sandbox: an inbound phone message reached `/webhook`, its payload was logged, and the phone received exactly one reply containing the identical text.

Expected result: one JSONL record for each received webhook payload and exactly one identical WhatsApp reply for a new inbound text message ID.

## Intentionally deferred

- Replay harness (Step 2).
- Claude agent, prompt, and tool calling (Steps 3–4).
- Google Sheets and Calendar (Step 5).
- Voice notes (Step 6).
- Follow-up approvals and daily brief (Step 7).
- Non-text processing and persistent history/deduplication. In-memory dedupe resets when the process restarts, as allowed for the demo.

## Troubleshooting

- Keep the Uvicorn port and tunnel origin port identical (`18080` here).
- If verification works but messages never arrive, confirm the `messages` webhook field is subscribed.
- If sending fails, confirm `WA_TOKEN` is current and `WA_PHONE_NUMBER_ID` is not the WABA ID; inspect the logged Cloud API response without exposing the token.
- Meta sends delivery/read status callbacks to the same endpoint. Their lack of a `messages` array is expected and they are ignored.
- Runtime payloads are written to `logs/inbound.jsonl`, which is intentionally ignored by Git and may contain customer phone numbers.
