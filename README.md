# AI-Slop-Assistant

A WhatsApp-based personal assistant that unifies my class schedule, Moodle due dates,
syllabi, and fraternity calendar into one prioritized Google Calendar, sends a 4AM daily
digest, and supports 2-way chat for updates and conflict resolution.

Full vision, priority-scoring design, and the phased roadmap live in
[PROJECT.md](PROJECT.md) — treat that as the source of truth and re-read it before
picking up work. Credential setup steps are in [CREDENTIALS.md](CREDENTIALS.md).

## Status

**Phase 1 complete** (Google Calendar CRUD). See [docs/PHASE1.md](docs/PHASE1.md) for
the design spec. Next up: Phase 2, Moodle `.ics` ingestion.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` per [CREDENTIALS.md](CREDENTIALS.md) (Twilio, Google, Moodle, weather,
Anthropic). Google Calendar/Tasks share one OAuth client — the first script run opens a
browser for one-time consent and caches a refresh token to `token.json`.

## Project layout

```
src/
  integrations/    # one module per external service (Google Calendar/Tasks, Moodle, Twilio, weather, Claude)
  bot.py           # WhatsApp bot entrypoint
  config.py        # env/config loading
scripts/           # one-off/manual utilities (test calendar setup, round-trip demo)
tests/             # pytest suite
docs/              # per-phase design specs
```

## Tests

```
pytest
```

The Calendar test suite runs against a dedicated `testing` Google Calendar (not
primary) — see `GOOGLE_TEST_CALENDAR_ID` in `.env.example` and
`scripts/create_test_calendar.py`.

## Test bench

```
python -m scripts.test_bench
```

A single interactive menu covering every automated test and manual/live check
across Phases 0–3 — no need to remember each module's own `python -m ...`
invocation. Items that cost money, send a real message, or hit a live API are
labeled and, where they have a real-world side effect (e.g. sending a WhatsApp
message), prompt for confirmation first.
