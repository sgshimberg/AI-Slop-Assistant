# WhatsApp Life/Academic Assistant — Living Project Doc

Status: Phase 0 complete. Phase 1 design spec written (docs/PHASE1.md), code not started. Last updated 2026-08-13.
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

## Phased Roadmap (each phase has a concrete test gate — don't advance until it passes)
0. ✅ **Foundations** — Collect API credentials (Moodle ICS URL, Google Calendar OAuth, Twilio WhatsApp Sandbox, Google Tasks, OpenWeatherMap, Anthropic).
   *Test: running the six individual hello-world integration scripts successfully validates real keys. — PASSED 2026-08-13.*
1. **Google Calendar core** — script can create/update/delete events programmatically.
   *Test: round-trip a test event via code.* → see [docs/PHASE1.md](docs/PHASE1.md)
2. **Moodle Ingestion (.ics)** — pull and parse the live .ics feed into structured JSON data.
   *Test: dump current semester's Moodle events to JSON, verify weights/dates by hand.*
3. **Syllabus parser** — Claude API extracts weights/due dates/exam dates from real syllabi using strict JSON schemas.
   *Test: parse 2–3 actual syllabi, manually verify accuracy.*
4. **Merge engine** — Run the priority scoring algorithm to combine Moodle + syllabus + class schedule + frat calendar into one prioritized event set.
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
12. **Hardening** — error handling, retries, monitoring, semester-boundary edge cases.
    *Test: run unattended for 2 weeks with no manual fixes needed.*

## Status Log
- 2026-08-12: Captured problem statement, condensed into living doc. Locked in Phase 0 decisions. Scaffolded repo structure. Wrote basic hello-world boilerplate scripts.
- 2026-08-13: Updated blueprint to replace static hierarchy with dynamic algorithmic calendar scoring. Accounted for NC State's Moodle token restriction by locking in the `.ics` strategy. Accounted for the Twilio 24h sandbox constraint. Ready to finish Phase 0 hello-world integration verification.
- 2026-08-13: **Phase 0 complete.** All six integrations (Twilio WhatsApp sandbox, Google Calendar, Google Tasks, Moodle ICS, OpenWeatherMap, Anthropic) validated with real credentials. Pushed initial codebase to GitHub: https://github.com/sgshimberg/AI-Slop-Assistant.
  - Google OAuth consent already completed locally — `credentials.json` and a cached `token.json` exist in the working tree (both gitignored). Phase 1 (Google Calendar core) can start without redoing the OAuth flow, as long as work continues on this machine; a fresh clone/machine will need `token.json` regenerated via one-time browser consent (see CREDENTIALS.md).
  - Reminder for Phase 6+ (WhatsApp bot): Twilio sandbox requires an inbound message every 24h or outbound sends silently fail — still unresolved, revisit before relying on the 4AM digest (see Decisions above).
  - `.env`, `credentials.json`, `token.json`, `.venv/`, and `data/` confirmed excluded via `.gitignore` — verified no secrets were committed.
- 2026-08-13: Phase 1 design spec written (docs-only, no code yet) — see [docs/PHASE1.md](docs/PHASE1.md).

