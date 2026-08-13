# Phase 2 — Moodle Ingestion (.ics)

Status: implemented and passing against the synthetic fixture — PASSED 2026-08-13
(fixture-only; real-data validation deferred, see Known limitation below). Test gate
(PROJECT.md): pull and parse the live .ics feed into structured JSON data; dump events
to JSON, verify dates by hand.

## Testing problem (why this spec differs from a normal live-data test)
Between semesters there's no live Moodle data to test against. The current
`MOODLE_ICS_URL` (from Phase 0) also returns **zero events**, not just zero upcoming
ones — confirmed by fetching it directly and parsing all `VEVENT`s with no date filter.
The URL has `preset_time=custom` but no `timestart`/`timeend` embedded, so Moodle isn't
scoping it to any range. Separately, there's no way to pull last semester's historical
calendar either — no archive access.

**Decision**: build a synthetic fixture by hand instead of pulling real data.
1. `tests/fixtures/moodle_sample.ics` — hand-written, following standard Moodle ICS
   export conventions (a handful of `VEVENT`s: a few assignments, a quiz, an exam, each
   with realistic `SUMMARY`/`DTSTART`/`URL` fields). Since it's synthetic, not real
   academic data, it's safe to commit — unlike a real export, which would've stayed in
   the gitignored `data/` dir.
2. Parsing logic must be network-decoupled (see below) so it can run against this file
   directly, with no `.env`/network dependency — makes the test gate reproducible on any
   machine.
3. **Known limitation**: the `course`/`type` extraction heuristics are based on my best
   understanding of Moodle's typical ICS summary format, not a verified real sample from
   NC State's Wolfware instance. Not blocking Phase 2 completion — tracked as a dedicated
   roadmap phase instead, **Phase 12: Moodle real-data validation** (see PROJECT.md), to
   run once a real semester feeds `MOODLE_ICS_URL`.

## Scope
Parse Moodle's ICS feed into structured JSON: event name, course (best-effort), type
(assignment/quiz/exam/other), due datetime, and source URL if present. No grade weights
here — those come from the syllabus in Phase 3. No merging with other sources — that's
Phase 4.

## Refactor of `src/integrations/moodle.py`
Current `_via_ics()` conflates fetching and parsing, and hardcodes an "upcoming only"
filter — that filter is correct for the Phase 0 hello-world script but wrong for Phase 2,
which must also parse past events out of a historical fixture. Split it:

```python
def fetch_ics_text(url: str) -> str: ...        # network only, unchanged behavior
def parse_ics(ics_text: str) -> list[dict]: ...  # pure, no network, no upcoming filter
def list_upcoming_events() -> list[dict]: ...    # Phase 0 behavior, now = fetch + parse + filter
```

`parse_ics` is what Phase 2 tests exercise directly — feed it the fixture file's text,
no network involved.

## Data model (per event)
| field | type | notes |
|---|---|---|
| name | str | cleaned title |
| raw_summary | str | original `SUMMARY`, kept for debugging parse misses |
| course | str \| None | best-effort extraction — exact regex TBD once we see a real sample's `SUMMARY`/`DESCRIPTION`/`CATEGORIES` format |
| type | str | one of `assignment`, `quiz`, `exam`, `other` — keyword heuristic on `raw_summary` |
| due | str (ISO 8601) | from `DTSTART`, normalized to UTC like the existing code |
| url | str \| None | from the ICS `URL` property, if present — links back to the Moodle activity |

The `course`/`type` heuristics are provisional (see Known limitation above) — first real
task once real data exists is to inspect a few raw `VEVENT` blocks from the live feed and
confirm the actual summary format NC State's Moodle produces, then lock in the parsing
rules for real.

## New script: dump to JSON for inspection
`scripts/dump_moodle_events.py <path-to-ics>` → prints structured JSON to stdout. Useful
now to eyeball the synthetic fixture's parse output, and later to inspect real output
once `MOODLE_ICS_URL` has live events.

## Test gate
`tests/test_moodle_parse.py`, using `tests/fixtures/moodle_sample.ics` (committed,
synthetic — no skip logic needed since it doesn't depend on anything local):
- Parse the fixture, assert the event count matches, and assert each hand-written event's
  name/type/due date/course come through correctly.

This validates the parser's mechanics (ICS → structured JSON) against a known-correct
input. It does **not** validate the `course`/`type` heuristics against Moodle's real
formatting — that check is deferred (see Known limitation).

## Out of scope
Grade weights (Phase 3, from syllabus). Merging with other calendars (Phase 4). Live
resync / dedupe (Phase 5). Fixing the `MOODLE_ICS_URL` date-range bug for production use
and re-validating the `course`/`type` heuristics against real data — both belong to
Phase 12 (Moodle real-data validation), not here; the fixture-based test gate doesn't
need either fixed.
</content>
