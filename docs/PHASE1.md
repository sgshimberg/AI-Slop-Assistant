# Phase 1 — Google Calendar Core (CRUD)

Status: complete — PASSED 2026-08-13. Test gate (PROJECT.md): round-trip a test event via code.

## Scope
CRUD for calendar events in `src/integrations/google_calendar.py`. No dedupe, recurrence,
attendees, reminders, retries — deferred to later phases (see Out of scope).

## OAuth
- `src/integrations/google_auth.py::SCOPES`: change
  `.../auth/calendar.readonly` → `.../auth/calendar` (write access).
- Delete `token.json` before first Phase 1 run — cached readonly-scope token won't
  authorize writes; forces one-time re-consent.

## Functions (signatures — `google_calendar.py`)
```python
create_event(summary: str, start: datetime, end: datetime,
             description: str = "", timezone: str = "America/New_York") -> dict
get_event(event_id: str) -> dict
update_event(event_id: str, **fields) -> dict
delete_event(event_id: str) -> None
list_upcoming_events(max_results: int = 5) -> list[dict]   # existing, unchanged
```
All use `calendarId="primary"`.

## Data model (minimal)
| field | type | notes |
|---|---|---|
| summary | str | title |
| start/end | datetime | send as `dateTime` + explicit `timeZone` (not UTC `Z` — avoid DST bugs) |
| description | str | optional, default "" |

Not modeled yet: recurrence, attendees, reminders, location.

## Error handling
Let `googleapiclient.errors.HttpError` propagate uncaught. No retry/backoff — that's
Phase 12 Hardening.

## Dedupe / idempotency
Out of scope. Belongs to Phase 5 (Calendar sync).

## Test gate
New `tests/test_google_calendar_roundtrip.py`:
1. `create_event` → capture id
2. `get_event(id)` → assert summary/start match
3. `update_event(id, summary=...)` → `get_event` → assert changed
4. `delete_event(id)` → `get_event` → assert 404 / status `cancelled`

## Out of scope (later phases)
Dedupe (5), recurrence, batch ops, retries/backoff (12), attendees/reminders (not yet planned).
