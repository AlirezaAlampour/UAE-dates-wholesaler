# Step 04 — Customer-Facing System Prompt

## Goal

Make the existing Claude agent a concise, natural WhatsApp sales representative for a UAE dates wholesaler without changing the Step 1–3 runtime paths.

## Implementation

- `app/prompts.py` contains the final Step 4 prompt and exactly three concise Gulf Arabic examples.
- `app/agent.py` imports that prompt in place of the temporary Step 3 instruction; the agent loop, tools, history, caching, webhook, and Meta sender are unchanged.
- The prompt matches English, Modern Standard Arabic, or Gulf Arabic per message; limits qualification to missing variety, quantity, and city; prevents invented pricing; escalates orders of 100 kg or more; controls lead capture and meeting claims; consolidates replies; and redirects off-topic questions.
- UAE date is calculated when the app starts so relative meeting dates can use UAE time.

## Live acceptance

Passed against the real `claude-sonnet-5` API through the replay HTTP endpoint:

- English 20 kg Medjool inquiry: price and lead tools used; concise English result with no invented price or currency.
- Gulf Arabic 20 kg Khalas inquiry: canonical `Khalas` tool lookup returned 18/kg and 360 total; Arabic-only reply.
- 300 kg Medjool inquiry: no price tool or standard quote; sales call offered.
- Two-turn Medjool inquiry: retained variety, asked only for missing quantity/city, then quoted and recorded once.
- Tomorrow-afternoon call: checked the correct UAE date, offered the returned 2 PM slot, and did not claim a booking.
- Football question: brief redirect with no guessed result.
- Additional formal-Arabic Ajwa inquiry stayed in Modern Standard Arabic and used the correct tool price; a same-inquiry follow-up did not repeat lead capture.

All replay requests used guarded outbound sending; Meta send calls remained zero. Prompt-cache creation and read hits were observed.

## Known limitations and mocked behavior

- Price, lead, availability, and booking tools remain deterministic Step 3 stubs; Sheets and Calendar are intentionally deferred to Step 5.
- Fake price results have no currency, so replies give tool-returned figures and leave currency confirmation to sales.
- History, lead state, and deduplication remain in memory and reset on restart.
- Restart the app before the demo so the prompt's UAE date is current.
- The replay CLI has its existing 10-second timeout; an extra three-iteration MSA check completed server-side just after that timeout. The six required acceptance scenarios completed successfully through the CLI.
- Voice, approvals, follow-ups, databases, dashboards, and other Step 5+ work remain deferred.
