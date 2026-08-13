# Phase 3 — Syllabus Parser

Status: **implemented and passed** — see `src/integrations/syllabus.py`,
`scripts/parse_courses.py`, `tests/test_syllabus_parse.py`. Test gate (PROJECT.md):
parse 2–3 actual syllabi, manually verify accuracy — ran against all 6 real ECE
courses in `data/courses/`; weights, dates, and cross-referencing all checked out,
with zero documents left unclassified. One limitation was found and fixed along the
way — see below.

## Scope
Parse a course's real documents (PDF and/or `.docx`) into one structured JSON record
per course: course identity, grade-category weights, and whatever graded-item due
dates happen to be stated. Uses the Claude API with a strict tool-use schema — no
prose-JSON parsing. No merging across courses or with Moodle events (that's Phase 4).
No calendar writes (Phase 5).

**Reliability assumption, from you:** grade-category weights are reliably present in
the syllabus itself. Due dates and exam dates are *not* guaranteed — some syllabi omit
them entirely, and some courses publish them in a **separate class-calendar document**
instead of the syllabus. So a course may hand this phase 1 file or several (syllabus +
calendar + whatever else), and the parser has to work from whichever subset it gets:
weights only, weights + dates, or dates arriving in a different file than the weights.

Unlike Phase 2, this phase tests against **real data from day one** — `data/courses/`
already holds real documents for 6 courses (ECE 109, 200, 211, 220, 301, 306), mixed
PDF/`.docx`, so no synthetic-fixture workaround is needed here. Coverage happens to
span every case this phase handles: weights-only (109, 200), dates-only (211), and
weights + a separate class-calendar document needing cross-reference (220, 301, 306).

**Grouping, from you:** documents don't need to be manually sorted into per-course
folders. Every professor formats their syllabus/calendar differently, but the course
name is always stated somewhere in the document itself — so Claude reads each
document and determines which course it belongs to, rather than us relying on
filename or folder conventions. This also matches how you're actually uploading:
everything dropped flat into one place.

## File storage
`data/courses/` — a single flat dropbox for every document, any course, no
subfolders required. `data/` is already fully gitignored (confirmed via
`git check-ignore`), so nothing extra is needed in `.gitignore`. No download
automation — you drop files in manually (for now — see Vision in PROJECT.md for the
planned future WhatsApp upload path, which will land files in the same place).
Mirrors why the Moodle fixture was safe to commit and real Moodle data isn't: these
are real personal academic documents.

## New module: `src/integrations/syllabus.py`
Two-stage pipeline: cheaply classify every document by course first, *then* run the
existing multi-document extraction (unchanged in spirit from the prior revision) on
each course's grouped documents.

```python
def extract_text(path: Path) -> str: ...
    # Dispatches on extension: .pdf -> pypdf, .docx -> python-docx.
    # Raises ValueError on unsupported extensions, and RuntimeError if extracted
    # text is suspiciously short (<200 chars) -- likely a scanned/image-only PDF
    # pypdf can't read. No OCR fallback (out of scope).

def identify_course(text: str, model: str = "claude-sonnet-5") -> str: ...
    # Single small forced tool-use call per document: reads the extracted text
    # and returns a normalized course code, e.g. "ECE 220" (department + number,
    # section/semester/instructor stripped). Deliberately separate from full
    # extraction below -- classification shouldn't fail just because a document
    # is messy in some other way, and it's cheap/fast to run per-file.

def group_by_course(dir_path: Path, ask_human: AskHuman | None = None) -> dict[str, list[Path]]: ...
    # Globs every supported file directly under dir_path (flat, no subfolders),
    # runs identify_course on each, and groups paths by the returned code.
    # The dict key is additionally whitespace/case-normalized as a safety net
    # against minor formatting drift between documents for the same course
    # (e.g. "ECE220" vs "ECE 220" collapse to the same group).
    #
    # A document identify_course can't place gets two more chances rather than a
    # guess: content-based reconciliation against already-classified courses first
    # (_reconcile_unknowns), then — only if that also comes back empty — the
    # optional ask_human(path, text, known_course_codes) callback, so a genuinely
    # unresolvable document surfaces as a direct question instead of a silent
    # misfile. Default None preserves the old (library-only, non-interactive)
    # behavior; scripts/parse_courses.py wires it to a terminal prompt.

def parse_course_documents(paths: list[Path], model: str = "claude-sonnet-5") -> dict: ...
    # Extracts text from every path, concatenates with a
    # "=== <filename> ===" header per document, and sends the whole bundle to
    # Claude in a SINGLE tool-use call (see below) -- not one call per file.
    # Letting Claude read the syllabus and the class calendar side by side in
    # one call is what lets it reconcile "Exam 1" (syllabus, no date) with
    # "Midterm Exam: Oct 3" (calendar doc) into one graded_items entry, which
    # a per-file-then-programmatic-merge approach would need brittle fuzzy
    # name-matching code to do instead.

def parse_all_courses(dir_path: Path) -> dict[str, dict]: ...
    # group_by_course(dir_path), then parse_course_documents per group.
    # Returns {course_code: record}. This is the actual entry point --
    # nothing in this phase requires you to pre-sort files by course.
```

## Structured extraction: tool-use, not prose JSON
Both Claude calls use forced tool-use, not prose JSON, for the same reason: the API
guarantees schema-shaped output instead of markdown-fence/prose-JSON parsing that can
drift or break.

- `identify_course`: a small `record_course_code` tool, `tool_choice` forced,
  input schema is just `{code: str}`. Prompt instructs Claude to return only
  department + number (e.g. "ECE 220"), never a section number, semester, or
  instructor name, so the same real course normalizes to the same string across
  differently-formatted documents.
- `parse_course_documents`: a `record_course` tool whose `input_schema` matches the
  data model below, `tool_choice` forced. System prompt instructs Claude to:
  - Treat category weights as the primary, expected output — extract them carefully.
  - Treat due/exam dates as opportunistic: use `null` for anything not explicitly
    stated anywhere in the provided documents, never guess or infer a date.
  - When multiple documents are provided, cross-reference them — an item named in
    the syllabus (e.g. "Exam 1", no date) and a dated entry in a separate
    class-calendar document (e.g. "Midterm Exam — Oct 3") referring to the same
    real assessment should be merged into one `graded_items` entry, not two.
  - Flag ambiguity (including "no dates found anywhere" or "couldn't tell if two
    items across documents are the same one") in `notes` rather than silently
    guessing.

## Data model
| field | type | notes |
|---|---|---|
| course | str | code + title, e.g. `"CSC 316: Data Structures"` |
| categories | list[{name: str, weight: float}] | grade breakdown; weights are 0–1 fractions and should sum to ~1.0 (validated with a warning, not an error — some syllabi round oddly or leave a category like "extra credit" uncapped) |
| graded_items | list[{name, category, type, due, weight_override}] | explicitly named/dated items — `type` is one of `exam`, `quiz`, `assignment`, `project`, `other`; `due` is an ISO date string or `null` if the syllabus doesn't give one; `category` links back to a `categories` entry name; `weight_override` is set only when the syllabus gives that specific item its own percentage distinct from its category average (e.g. "Final counts double the other exams") |
| notes | str \| None | freeform — anything Claude flags as ambiguous or worth a human look |

`type`'s vocabulary intentionally mirrors `moodle.py`'s `_classify_type` values
(`assignment`/`quiz`/`exam`/`other`), plus `project` since syllabi usually break
that out explicitly where Moodle summaries don't. Reconciling the two vocabularies
(does a syllabus `project` merge with a Moodle-parsed `assignment`?) is a Phase 4
merge-engine concern, not solved here — flagged so Phase 4 doesn't rediscover it.

## New script: `scripts/parse_courses.py [dir]`
Defaults to `data/courses/`, runs `parse_all_courses`, and prints
`{course_code: record}` as JSON to stdout for manual inspection — same pattern as
`scripts/dump_moodle_events.py`.

## Test gate
Two tiers, because this phase's real test gate is inherently manual:

1. **Automated** (`tests/test_syllabus_parse.py`, CI-safe, no network): covers
   `extract_text`'s extension dispatch and short-text error, `identify_course` and
   `parse_course_documents`'s handling of **mocked** Anthropic tool-use responses,
   and `group_by_course`'s grouping/normalization logic given a mocked classifier —
   catches code bugs (wrong routing, malformed tool input handling, grouping drift)
   without hitting the live API or depending on real syllabus content.
2. **Manual** (the actual Phase 3 gate per PROJECT.md): run
   `scripts/parse_courses.py` against the real, flat `data/courses/` dropbox,
   compare the JSON to the real documents by eye — including checking that every
   document landed in the right course group, and that dates from a separate
   class-calendar file landed on the right `graded_items` entry.

## New dependencies
`pypdf` (PDF text extraction), `python-docx` (`.docx` text extraction) — added to
`requirements.txt`.

## Out of scope
Merging with Moodle events / class schedule (Phase 4). Calendar event creation
(Phase 5). OCR for scanned/image-only PDFs — if `pypdf` can't extract real text, the
function raises rather than silently returning garbage. Automated document
discovery/download — manual file drop into `data/courses/` only (a WhatsApp upload
path is planned later, per PROJECT.md's Vision, but not part of this phase).

Note for Phase 4: this phase's `graded_items.due` is *not* the final due date — per
PROJECT.md's Due date & weight source priority decision, Moodle's live calendar wins
over a class-document date when the same item exists in both. This phase's `due` is
a fallback the merge engine uses only for items Moodle doesn't carry (e.g. exams
often aren't Moodle calendar entries). This phase's `categories`/weights, by
contrast, have no Moodle equivalent and are authoritative as-is.

## Known limitation (found during the manual test gate — since resolved)
The "course name is always stated somewhere in the document" assumption doesn't
universally hold: `ECE220-Fall25 - Course Schedule - DY Eun (2).pdf` is a bare weekly
grid (topics/HW/lab columns) that never states "ECE 220" or "Analytical Foundations"
anywhere in its extracted text — confirmed by inspecting the raw extracted text
directly. `identify_course` has no grounding to work from on a document like this,
and without an explicit escape hatch it **hallucinated** a course code — two
different runs produced two different wrong answers (`"&LT;UNKNOWN&GT;"`, then
`"ENGR 260"`) instead of reliably admitting it couldn't tell. That's a correctness
risk beyond just "one document lands in the wrong group" — a hallucinated real course
code could have silently merged this document's content into an unrelated course's
grade record.

First fix, in `identify_course`'s prompt/schema: it must return the literal string
`"UNKNOWN"` (`syllabus.UNKNOWN_COURSE`) when no course code or department is
explicitly stated, rather than inferring one from topic/content. `group_by_course`
also treats any code containing the substring `UNKNOWN` (case/wrapper-noise-tolerant,
to survive odd model formatting like the `&LT;...&GT;` case above) as unclassifiable,
and — important — does **not** lump multiple unclassifiable documents into one shared
bucket, since two different real courses' orphan documents could land there and get
cross-referenced as if they were the same course. Each gets its own
`"UNKNOWN: <filename>"` key so it's visible for manual reconciliation instead of
silently mis-filed.

That alone still left the document stranded as its own one-off group needing manual
merging by hand — not wrong, but not what the phase is supposed to deliver
automatically. **Second fix — content-based reconciliation**, added as a step after
initial grouping: `_reconcile_unknowns` takes every `"UNKNOWN: <filename>"` document
and asks Claude (`_match_unknown_to_candidate`, forced tool-use) to compare its
content against a sample of each *already content-classified* course's documents —
specific overlap only (same chapter/topic sequence, same named tests/labs), never a
generic "both are intro engineering courses" match, and `null` when not confident.
Candidates are always real, already-identified courses — never another unclassifiable
document, for the same reason the shared-bucket fallback above was rejected: two
orphans matching each other on nothing would just relocate the corruption risk rather
than remove it. Confirmed against the real `data/courses/` dropbox: the schedule PDF
now correctly reconciles into `"ECE 220"` — its topic sequence (Ch 2 Signals, Ch 4
Complex Numbers, Ch 8 Laplace Transform, Ch 9 Fourier Series...) matches the ECE 220
syllabus already grouped from `ECE220-Fall25 - Syllabus -DY Eun (1).pdf` — and the
merged `ECE 220` record correctly carries homework/midterm/final due dates pulled
from the schedule alongside the category weights from the syllabus, exactly the
weights+dates cross-referencing this phase was designed to do. All 6 real courses in
`data/courses/` now group with zero leftover `UNKNOWN` keys.

Also added while re-verifying against real output: `parse_course_documents` now
defaults a missing `notes` key to `None` (the tool schema allows omitting it, and one
real response did) so the field is reliably present for downstream code, and warns
(via `warnings.warn`, not a hard error, per the Data model table's original intent)
when a course's category weights don't sum to ~1.0 — not triggered by any of the 6
real courses, but exercised in `tests/test_syllabus_parse.py` against a mocked
lopsided response.

**Third fix, per your explicit instruction: ask, don't guess.** Content-based
reconciliation resolves the common case (a companion document for a course that's
already been identified elsewhere), but there's still a real scenario it can't cover:
the *first* document dropped for a brand-new course, with no identifying information
in its own text and no sibling document yet to content-match against — nothing in
`data/courses/` exercises this today, but it will happen once you're uploading a
single syllabus at a time rather than a whole semester's batch. For that case,
`group_by_course`/`parse_all_courses` now take an optional `ask_human` callback
(`AskHuman = Callable[[Path, str, list[str]], str | None]`, see
src/integrations/syllabus.py) — invoked only after both `identify_course` and
`_reconcile_unknowns` have already come back empty, with the document's path, text,
and the courses identified so far. `scripts/parse_courses.py` wires this to a
terminal prompt (prints the filename, known courses, and a text excerpt, then
`input()`s your answer) — blank/unsure answers leave the document under its
`"UNKNOWN: <filename>"` key rather than forcing a choice. This is the same
`(document, context) -> answer` shape a future WhatsApp round-trip (Phase 6+) would
need, so upgrading the interaction later is a matter of swapping the callback, not
rewriting the classification pipeline. Default is `None` (no prompting), so calling
`group_by_course`/`parse_all_courses` without it behaves exactly as before —
`tests/test_syllabus_parse.py` covers being asked on failure, not being asked when
content-matching already succeeded, and staying unresolved when the human doesn't
know either.
