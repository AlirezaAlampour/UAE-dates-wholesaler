# Client Demo Runbook

The customer experience is WhatsApp. Keep terminals visible only to diagnose problems.

## Start the demo

Use the machine that has the working `.env` and the existing named Cloudflare tunnel configuration.

Terminal 1 — start FastAPI and leave it running:

```bash
cd /home/alireza/Projects/UAE-dates-wholesaler
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18080
```

Terminal 2 — confirm the local webhook and required environment variables:

```bash
cd /home/alireza/Projects/UAE-dates-wholesaler
.venv/bin/python scripts/demo_check.py
```

Terminal 3 — start the existing named tunnel. Replace the placeholder with its existing name; do not use a quick tunnel:

```bash
cloudflared tunnel run <TUNNEL_NAME>
```

The tunnel's existing ingress must route `https://<STABLE_HOSTNAME>/webhook` to `http://127.0.0.1:18080`. Confirm the public route without exposing the verification token in shell history:

```bash
cd /home/alireza/Projects/UAE-dates-wholesaler
.venv/bin/python scripts/demo_check.py --url https://<STABLE_HOSTNAME>/webhook
```

Both checks must end with `DEMO CHECK PASSED`.

## Confirm the Meta sandbox

Before the client arrives:

1. In Meta **WhatsApp → Configuration**, confirm the callback is `https://<STABLE_HOSTNAME>/webhook` and the `messages` webhook field is subscribed.
2. In **WhatsApp → API Setup**, confirm the sandbox test number is selected and the demo phone appears as an approved test recipient.
3. Send a unique test message from that phone. Confirm one inbound request appears in the FastAPI terminal, one new record appears in `logs/inbound.jsonl`, and exactly one reply reaches the phone.
4. Restart FastAPI after this test to clear demo-only conversation history and deduplication state.

## Exact phone demo sequence

Send these messages one at a time from the same approved recipient and wait for each reply.

1. `Hi, I need 20kg of Medjool dates delivered to Dubai.`

   Expected: one concise English reply; the price tool supplies 42/kg and 840 total; no made-up price or currency.

2. `أبغي 20 كيلو خلاص للتوصيل في دبي`

   Expected: one natural Gulf Arabic reply with no unnecessary English; the Khalas lookup supplies 18/kg and 360 total.

3. `Actually I need 300kg of Medjool.`

   Expected: recognizes a bulk order, gives no standard quote, and moves toward a direct sales conversation or meeting.

4. `Can we speak tomorrow afternoon?`

   Expected: checks the existing availability stub and offers the returned afternoon slot in one concise reply; it does not claim the meeting is booked.

Memory scenario:

5. `I also need some Ajwa dates.`

   Expected: remembers Ajwa and asks only for the missing approximate quantity and delivery city.

6. `About 15kg, delivery to Sharjah.`

   Expected: remembers Ajwa, uses the price tool, gives 55/kg and 825 total without inventing a currency, and does not ask for already provided information.

## Fast recovery

- No local response: confirm Terminal 1 is still running on port `18080`, then rerun the local `demo_check.py` command.
- Public check fails: restart the named tunnel, confirm its ingress still points to port `18080`, and rerun the public check.
- Webhook verifies but phone messages do not arrive: confirm Meta is subscribed to `messages` and the phone is still an approved sandbox recipient.
- Inbound arrives but sending fails: refresh the Meta token if it is temporary and confirm `WA_PHONE_NUMBER_ID` is the phone number ID, not the WABA ID.
- Claude returns an error: confirm the Anthropic key is active, workspace-scoped, and has available credit.
- Duplicate or confusing replies: stop and restart FastAPI to clear in-memory history/deduplication, then resume with a fresh customer message.
- Relative meeting date looks wrong: restart FastAPI so the prompt reloads the current UAE date.
- If recovery takes more than a minute, show the known-good replay path while keeping Meta sending suppressed: `.venv/bin/python scripts/replay.py text "I need 20kg of Medjool dates delivered to Dubai."`
