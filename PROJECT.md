# WhatsApp Life/Academic Assistant — Living Project Doc

Status: Phase 2 complete (fixture-tested; real-data validation deferred to next semester). Last updated 2026-08-13.
This is the source of truth. Re-read this file at the start of every session on this project.

Repo: https://github.com/sgshimberg/AI-Slop-Assistant (main branch)

## Vision
A WhatsApp-based assistant that ingests my syllabi, Moodle data, class schedule, and
fraternity calendar, then maintains a combined Google Calendar + phone checklist, and
sends me a 4AM daily digest — with full 2-way chat for updates and conflict resolution.

## Priority & Conflict Scoring Engine
To resolve conflicts automatically, the system uses a **Dynamic Priority Score (P)** rather than a static list. This allows high-stakes items from lower categories to naturally bump low-stakes items from higher categories.

### 1. Category Base Values (B)
- School: 100
- Research: 80
- Internship: 70
- Career Development: 50
- Fraternity: 30
- Relationship: 25
- Cleaning: 10

### 2. Item Weight Modifier (W)
- **Syllabus Items**: Math matches assignment grade weight (e.g., Exam = 0.30, Homework = 0.05).
- **Fixed Events**: Baseline attendance items (Classes, Mandatory Frat Chapter) default to a weight of 1.0.
- **Optional Events**: Default to a weight of 0.20 (e.g., optional social events).

### 3. Core Math Formula
Whenever two calendar events overlap, the backend calculates:
`Priority Score (P) = (Category Base Value × Item Weight) + Urgency Escalator`

*The Urgency Escalator automatically increases an item's score by +5 points for every day it draws closer to its due date (anti-procrastination algorithm).*

## Inputs

| Source | Data | Rule / Strategy |
|---|---|---|
| Syllabi (start of semester) | Grade weights, due dates, exam dates | LLM-parsed once, extracts JSON weight objects to feed calendar engine |
| Moodle Feed | Calendar, due dates | Continuous sync via Moodle `.ics` live calendar export URL fallback |
| Class schedule | Recurring weekly baseline | Fixed (Weight 1.0), must attend |
| Homework/exam planning | — | Generates 3–4 hr working calendar blocks; exam study starts ≥1 week before |
| Fraternity calendar | Required meetings, events, parties | Monday triage workflow flags items as Required (1.0) vs Optional (0.20) |
| WhatsApp chat | Ad hoc requests, RSVPs, schedule changes | 2-way, real-time context ingestion |

## Outputs
- **Google Calendar**: daily-synced master. Combines chosen frat events, calculated syllabus study blocks, research blocks, internship work, and life events (incl. time with girlfriend).
- **Phone checklist app**: Google Tasks handles final checkboxes for deadlines. *Note: 3–4 hour study blocks are created directly on the Calendar as events, not as tasks, due to API duration limitations.*
- **WhatsApp daily digest, 4:00 AM sharp**: date, Raleigh weather, day breakdown, prioritized working schedule, active schedule conflicts requiring human decisions, and today's frat events.
- **WhatsApp 2-way chat**: on-demand Q&A, manual conflict resolution overrides, and free-form updates ("just grabbed dinner with X, adjust my day").
- **Meals**: 3 food blocks/day must always be reserved on the calendar.

## Weekly Rhythms
- **Monday**: bot asks which frat events I want to attend that week → yes (add to calendar) / yes-but-conflict (resolve in chat) / no (flagged, not scheduled).
- **Daily 4AM**: digest sent automatically.
- **Anytime**: I can chat to query status or push updates; bot maintains calendar all semester.

## Decisions (Updated 2026-08-13)
- **WhatsApp**: Twilio WhatsApp API. *Development Trap: Twilio Sandbox requires inbound message every 24 hours. Workaround: Include a quick reply loop or buy a live production number early to prevent 4AM silent failures.*
- **Checklist app**: Google Tasks (same Google account/OAuth client as Calendar).
- **Hosting**: small always-on cloud VPS (needed for a guaranteed 4AM send); deferred until Phase 7.
- **Stack**: Python.
- **LLM**: Claude API (for structured syllabus JSON parsing and conversational agent routing).
- **Weather**: OpenWeatherMap free tier for Raleigh, NC.
- **Moodle API Access**: Web Service tokens disabled by NC State. Locked in fallback to Moodle's built-in `.ics` calendar export feed feed parsed via Python `icalendar`.
- **Due date & weight source priority (Phase 4 merge rule)**: Moodle's live calendar is authoritative for a per-assignment due date whenever that item exists there — professors keep it current, syllabus dates drift. Class documents (syllabus + any separate class calendar) are authoritative for grade-category weights (Moodle carries none) and are the fallback due-date source for items Moodle doesn't carry at all (exams especially are often only in the syllabus/class calendar, never posted as a Moodle calendar entry). When the same item appears in both with conflicting dates, Moodle wins.

## Phased Roadmap (each phase has a concrete test gate — don't advance until it passes)
0. ✅ **Foundations** — Collect API credentials (Moodle ICS URL, Google Calendar OAuth, Twilio WhatsApp Sandbox, Google Tasks, OpenWeatherMap, Anthropic).
   *Test: running the six individual hello-world integration scripts successfully validates real keys. — PASSED 2026-08-13.*
1. ✅ **Google Calendar core** — script can create/update/delete events programmatically.
   *Test: round-trip a test event via code.* → see [docs/PHASE1.md](docs/PHASE1.md) — PASSED 2026-08-13.
2. ✅ **Moodle Ingestion (.ics)** — pull and parse the live .ics feed into structured JSON data.
   *Test: dump current semester's Moodle events to JSON, verify weights/dates by hand.* → see [docs/PHASE2.md](docs/PHASE2.md) — PASSED 2026-08-13 against synthetic fixture (real-data check deferred).
3. **Syllabus parser** — Claude API extracts weights/due dates/exam dates from real syllabi using strict JSON schemas.
   *Test: parse 2–3 actual syllabi, manually verify accuracy.* → see [docs/PHASE3.md](docs/PHASE3.md)
4. **Merge engine** — Run the priority scoring algorithm to combine Moodle + syllabus + class schedule + frat calendar into one prioritized event set, resolving due dates and weights per the Due date & weight source priority decision above.
   *Test: one week's unified schedule matches hand-built expectation.*
5. **Calendar sync** — push merged events to Google Calendar with dedupe/update logic.
   *Test: run daily for a week; no dupes, stays accurate.*
6. **WhatsApp bot skeleton** — send/receive messages end-to-end.
   *Test: round-trip a message.*
7. **Daily digest generator** — 4AM message (weather + schedule + to-do + conflicts + frat events).
   *Test: manually trigger and review output for several consecutive days.*
8. **Priority/to-do engine** — Validate auto-escalating urgency math per the dynamic formulas.
   *Test: scenario checks (due tomorrow vs. due in 2 weeks, etc.) give expected ordering.*
9. **Conversational agent** — full 2-way chat, conflict resolution, on-demand Q&A, holds context across the conversation. *Test: multi-day real conversation trial.*
10. **Monday frat RSVP flow.** *Test: run 2–3 real Mondays, verify calendar matches responses.*
11. **Checklist app 2-way sync.** *Test: check an item on phone, confirm calendar updates.*
12. **Moodle real-data validation** — revisit Phase 2's Moodle parsing once a real semester
    is live (built with a synthetic fixture during the between-semesters gap — see
    [docs/PHASE2.md](docs/PHASE2.md) Known limitation). Fetch the real `MOODLE_ICS_URL`
    feed, inspect actual `SUMMARY` formatting, fix the `course`/`type` regex heuristics in
    `src/integrations/moodle.py` if they don't match reality, and fix the `MOODLE_ICS_URL`
    date-range bug (Phase 2 found it returns 0 events — no `timestart`/`timeend` embedded)
    now that there's a real "upcoming" window to export.
    *Test: dump the live feed to JSON, verify every event against the actual Moodle
    calendar in a browser, by hand.*
13. **Hardening** — error handling, retries, monitoring, semester-boundary edge cases.
    *Test: run unattended for 2 weeks with no manual fixes needed.*

## Status Log
- 2026-08-12: Captured problem statement, condensed into living doc. Locked in Phase 0 decisions. Scaffolded repo structure. Wrote basic hello-world boilerplate scripts.
- 2026-08-13: Updated blueprint to replace static hierarchy with dynamic algorithmic calendar scoring. Accounted for NC State's Moodle token restriction by locking in the `.ics` strategy. Accounted for the Twilio 24h sandbox constraint. Ready to finish Phase 0 hello-world integration verification.
- 2026-08-13: **Phase 0 complete.** All six integrations (Twilio WhatsApp sandbox, Google Calendar, Google Tasks, Moodle ICS, OpenWeatherMap, Anthropic) validated with real credentials. Pushed initial codebase to GitHub: https://github.com/sgshimberg/AI-Slop-Assistant.
  - Google OAuth consent already completed locally — `credentials.json` and a cached `token.json` exist in the working tree (both gitignored). Phase 1 (Google Calendar core) can start without redoing the OAuth flow, as long as work continues on this machine; a fresh clone/machine will need `token.json` regenerated via one-time browser consent (see CREDENTIALS.md).
  - Reminder for Phase 6+ (WhatsApp bot): Twilio sandbox requires an inbound message every 24h or outbound sends silently fail — still unresolved, revisit before relying on the 4AM digest (see Decisions above).
  - `.env`, `credentials.json`, `token.json`, `.venv/`, and `data/` confirmed excluded via `.gitignore` — verified no secrets were committed.
- 2026-08-13: Phase 1 design spec written (docs-only, no code yet) — see [docs/PHASE1.md](docs/PHASE1.md).
- 2026-08-13: **Phase 1 complete.** Implemented `create_event`/`get_event`/`update_event`/`delete_event` in `src/integrations/google_calendar.py` per spec. OAuth scope widened from `calendar.readonly` to `calendar` (write) in `google_auth.py`; re-consented after deleting the stale readonly token. Added `tests/test_google_calendar_roundtrip.py`, which passed against the live Calendar API (create → get → update → get → delete → get confirms `cancelled`). Added `pytest` to `requirements.txt`.
- 2026-08-13: Added `scripts/demo_calendar_roundtrip.py` (manual, paused, visual round-trip demo) and `scripts/create_test_calendar.py` (idempotent setup for a dedicated `testing` Google Calendar, ID stored as `GOOGLE_TEST_CALENDAR_ID`). CRUD functions gained an optional `calendar_id` param (defaults to `primary`, unchanged for production use); the test suite and demo script now target `testing` instead of primary. Along the way, fixed a latent bug in the round-trip test's datetime assertion — it string-compared raw `dateTime` values, which only worked by coincidence on primary; now compares actual instants via `zoneinfo`.
- 2026-08-13: **Phase 2 design spec written** (docs/PHASE2.md) — no code yet. While planning, found the live `MOODLE_ICS_URL` from Phase 0 currently returns **zero events total** (not just zero upcoming) — its `preset_time=custom` param has no `timestart`/`timeend` embedded, so it isn't scoped to any range. That's separate from the semester-break problem and blocks live testing either way. User also has no way to access last semester's historical Moodle calendar (no archive access) — so real-data testing isn't possible at all right now, not just inconvenient.
- 2026-08-13: **Phase 2 complete**, tested against a hand-built synthetic fixture instead of real data (`tests/fixtures/moodle_sample.ics`, committed — safe since it's fake data). Refactored `src/integrations/moodle.py` to split `fetch_ics_text` (network) from `parse_ics` (pure) and added `course`/`type`/`due`/`url` extraction. Added `scripts/dump_moodle_events.py` for manual JSON inspection and `tests/test_moodle_parse.py` (6 tests, all passing). **Known limitation**: the `course`/`type` parsing heuristics are based on assumed Moodle ICS formatting, not verified against a real NC State Wolfware export.
- 2026-08-13: Added a new roadmap phase, **12. Moodle real-data validation**, placed near the end (before Hardening, now renumbered 13) specifically to close that Phase 2 gap once a real semester is live — re-check `moodle.py`'s parsing heuristics against the real feed and fix the `MOODLE_ICS_URL` date-range bug, both deferred since there was no real data to test against this week.
- 2026-08-13: **Phase 3 design spec written** (docs/PHASE3.md) — no code yet. Unlike Phase 2, real syllabi (mixed PDF/`.docx`) are available now, so this phase tests against real data from the start instead of a synthetic fixture. Plan: new `src/integrations/syllabus.py` (`extract_text` via `pypdf`/`python-docx`, `parse_syllabus` via Claude tool-use forced to a strict `record_syllabus` schema — course, grade categories, dated graded items, notes), files live in the already-gitignored `data/syllabi/`, and `scripts/parse_syllabus.py` for manual JSON inspection. Test gate is two-tier: an automated mocked-API test for parsing mechanics, plus the real manual gate (compare parser output against 2–3 real syllabi by eye) since there's no ground-truth answer key to assert against automatically.
- 2026-08-13: **Phase 3 spec revised** before any code was written. User clarified real-world syllabus behavior: grade-category weights are reliably present, but due/exam dates are not guaranteed and sometimes live in a **separate class-calendar document** rather than the syllabus. Reworked docs/PHASE3.md accordingly: a course now maps to a `data/courses/<COURSE_CODE>/` directory holding *all* of its documents, and `parse_course_documents(paths, ...)` sends every document for a course to Claude in one combined tool-use call (concatenated with per-file headers) so Claude — not hand-written fuzzy-matching code — reconciles items named in the syllabus with dates that show up in a different file. Renamed the script to `scripts/parse_course.py <course_dir>` and the tool schema to `record_course` to match. `categories`/`graded_items.due` were already nullable in the original schema, so the data model itself didn't need to change — only the file-handling and prompt design did.
- 2026-08-13: Added a new **Decisions** entry: **Due date & weight source priority**. Moodle's live calendar (Phase 2) wins on due date whenever an item exists there — it's kept current by professors, unlike syllabus dates which drift. Class documents (Phase 3) are authoritative for grade weights (Moodle has none) and are the due-date fallback only for items Moodle doesn't carry at all (exams especially). This is a Phase 4 (merge engine) rule, captured now so it isn't rediscovered later; noted a pointer to it in both the Phase 4 roadmap line and docs/PHASE3.md's Out of scope section.
- 2026-08-13: Created `data/courses/` (gitignored, build/test-only dropbox for real course documents). User populated it with real files for ECE 109, 200, 211, 220, 301, 306 — a mix of weights-only, dates-only, and (for 220/301/306) both a syllabus and a separate class-calendar document, which is real coverage of every case Phase 3 was designed to handle.
- 2026-08-13: **Phase 3 spec revised again**: user wants course grouping determined by Claude reading each document's content (course name is always stated somewhere in it), not by filename or manually-sorted subfolders — matches how files are actually being uploaded (flat, no pre-sorting) and sets up naturally for the planned future WhatsApp upload path. Reworked docs/PHASE3.md's pipeline to two stages: `identify_course(text)` (cheap, forced tool-use, per document, returns a normalized "DEPT ###" code) groups every file in flat `data/courses/` via `group_by_course`, then the existing `parse_course_documents` (combined multi-doc tool-use call, unchanged) runs per resulting group. New entry point `parse_all_courses(dir_path) -> {course_code: record}`. Script renamed `scripts/parse_courses.py [dir]` (defaults to `data/courses/`, no per-course arg needed).

