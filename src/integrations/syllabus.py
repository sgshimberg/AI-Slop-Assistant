"""Course document parsing: grade-category weights and graded items from real syllabi
and class-calendar documents, via the Claude API with forced tool-use.

Run:  python -m src.integrations.syllabus
Requires ANTHROPIC_API_KEY in .env. Two-stage pipeline: `identify_course` cheaply
classifies every document in a flat dropbox by course, then `parse_course_documents`
runs the full extraction on each course's grouped documents in one combined call —
see docs/PHASE3.md. A document `identify_course` can't place (no course code stated
anywhere in it) gets one more chance via `_reconcile_unknowns`, which compares its
content against already-classified courses' documents. If even that comes back
empty, the last resort is asking a human (an `AskHuman` callback) rather than
guessing — `scripts/parse_courses.py` wires that to a terminal prompt today; a later
phase can swap in a WhatsApp round-trip without touching this module.
"""

import re
import warnings
from collections.abc import Callable
from pathlib import Path

from anthropic import Anthropic
from docx import Document
from pypdf import PdfReader

from src import config

_SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
_CODE_RE = re.compile(r"^([A-Z]+)\s*(\d.*)$")

UNKNOWN_COURSE = "UNKNOWN"

# (path, extracted_text, known_course_codes) -> course code the human gave, or None/falsy
# if they don't know either (document stays unresolved under its "UNKNOWN: <filename>" key).
AskHuman = Callable[[Path, str, list[str]], "str | None"]

_COURSE_CODE_TOOL = {
    "name": "record_course_code",
    "description": "Record the normalized course code identified in a document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Department + course number only, e.g. 'ECE 220'. Never a section "
                    f"number, semester, or instructor name. If no course code or department "
                    f"name is explicitly stated anywhere in the text, return exactly "
                    f"'{UNKNOWN_COURSE}' — never guess a code based on topic, content, or "
                    f"filename-like hints."
                ),
            }
        },
        "required": ["code"],
    },
}

_RECORD_COURSE_TOOL = {
    "name": "record_course",
    "description": "Record grade-category weights and graded items extracted from a course's documents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "course": {
                "type": "string",
                "description": "Course code and title, e.g. 'CSC 316: Data Structures'.",
            },
            "categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "weight": {"type": "number", "description": "0-1 fraction."},
                    },
                    "required": ["name", "weight"],
                },
            },
            "graded_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "category": {"type": "string", "description": "Links back to a categories entry name."},
                        "type": {
                            "type": "string",
                            "enum": ["exam", "quiz", "assignment", "project", "other"],
                        },
                        "due": {
                            "type": ["string", "null"],
                            "description": "ISO date string, or null if not stated anywhere.",
                        },
                        "weight_override": {
                            "type": ["number", "null"],
                            "description": "Only set when the syllabus gives this item its own percentage distinct from its category average.",
                        },
                    },
                    "required": ["name", "category", "type", "due"],
                },
            },
            "notes": {
                "type": ["string", "null"],
                "description": "Anything ambiguous or worth a human look.",
            },
        },
        "required": ["course", "categories", "graded_items"],
    },
}

_MATCH_COURSE_TOOL = {
    "name": "record_course_match",
    "description": "Record which candidate course, if any, a document's content matches.",
    "input_schema": {
        "type": "object",
        "properties": {
            "matched_course": {
                "type": ["string", "null"],
                "description": (
                    "The exact course code (copied verbatim from the candidate list) whose "
                    "sample text shares specific, confident content overlap with the "
                    "document — the same chapter/topic sequence, or the same named "
                    "tests/labs/assignments. null if no candidate is a confident match, or "
                    "the overlap is only generic (e.g. both are intro engineering courses)."
                ),
            }
        },
        "required": ["matched_course"],
    },
}

_MATCH_SYSTEM_PROMPT = """\
A document's course could not be identified from its own text — it never states a \
course code or department anywhere. Compare its content against each candidate \
course below (shown via a sample of that course's own already-identified document \
text) and decide whether it's a confident content match: the same chapter/topic \
sequence, the same named tests/labs/assignments, or other specific structural \
overlap. Do not match on generic resemblance alone (e.g. both happen to be intro \
engineering courses with homework and exams) — when in doubt, return null.
"""

_PARSE_SYSTEM_PROMPT = """\
You extract grade-category weights and graded items from a course's syllabus and/or \
class-calendar documents. Treat category weights as the primary, expected output — \
extract them carefully; syllabi reliably state them. Treat due/exam dates as \
opportunistic: use null for anything not explicitly stated anywhere in the provided \
documents, never guess or infer a date.

When multiple documents are provided, cross-reference them: an item named in a \
syllabus (e.g. "Exam 1", no date) and a dated entry in a separate class-calendar \
document (e.g. "Midterm Exam — Oct 3") referring to the same real assessment should \
be merged into one graded_items entry, not two.

Flag ambiguity — including "no dates found anywhere" or "couldn't tell if two items \
across documents are the same one" — in notes rather than silently guessing.
"""


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")

    if len(text.strip()) < 200:
        raise RuntimeError(
            f"Extracted text from {path.name} is suspiciously short ({len(text.strip())} "
            "chars) — likely a scanned/image-only PDF pypdf can't read."
        )
    return text


def _normalize_course_code(code: str) -> str:
    cleaned = " ".join(code.strip().upper().split())
    # Guard against odd model output (e.g. "&LT;UNKNOWN&GT;") for the "can't tell" case —
    # a real department+number code never contains the word UNKNOWN, so substring
    # containment is enough to catch encoding/wrapper noise around the placeholder.
    if UNKNOWN_COURSE in cleaned:
        return UNKNOWN_COURSE
    match = _CODE_RE.match(cleaned)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return cleaned


def _tool_input(message, tool_name: str) -> dict:
    tool_use = next(block for block in message.content if block.type == "tool_use" and block.name == tool_name)
    return tool_use.input


def identify_course(text: str, model: str = "claude-sonnet-5") -> str:
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=50,
        system=(
            "You identify which course a document belongs to. Read the document text "
            "and return only the department + course number (e.g. 'ECE 220') — never "
            f"a section number, semester, or instructor name. If the text never states "
            f"a course code or department anywhere (e.g. a bare weekly schedule grid "
            f"with no header), return exactly '{UNKNOWN_COURSE}' rather than inferring "
            f"one from topic or content."
        ),
        # Course identity is almost always stated near the top of a syllabus or
        # calendar; capping input keeps this classification pass cheap.
        messages=[{"role": "user", "content": text[:4000]}],
        tools=[_COURSE_CODE_TOOL],
        tool_choice={"type": "tool", "name": "record_course_code"},
    )
    return _tool_input(message, "record_course_code")["code"]


def _match_unknown_to_candidate(text: str, candidates: dict[str, str], model: str = "claude-sonnet-5") -> str | None:
    """Try to place a course-less document by comparing its content against documents
    already classified into real courses — never against another unclassified document,
    since two unrelated orphans could otherwise be matched to each other on nothing."""
    if not candidates:
        return None
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    candidate_block = "\n\n".join(
        f"--- Candidate course: {code} ---\n{sample[:3000]}" for code, sample in candidates.items()
    )
    message = client.messages.create(
        model=model,
        max_tokens=50,
        system=_MATCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"=== Unidentified document ===\n{text[:4000]}\n\n{candidate_block}"}],
        tools=[_MATCH_COURSE_TOOL],
        tool_choice={"type": "tool", "name": "record_course_match"},
    )
    return _tool_input(message, "record_course_match")["matched_course"]


def _reconcile_unknowns(
    groups: dict[str, list[Path]], texts: dict[Path, str], ask_human: AskHuman | None = None
) -> dict[str, list[Path]]:
    unknown_keys = [key for key in groups if key.startswith(f"{UNKNOWN_COURSE}: ")]
    for key in unknown_keys:
        # Recomputed each iteration: an earlier ask_human answer in this same loop may
        # have introduced a course code that a later document should also match.
        candidates = {code: texts[paths[0]] for code, paths in groups.items() if code not in unknown_keys}
        unknown_path = groups[key][0]
        match = _match_unknown_to_candidate(texts[unknown_path], candidates)
        if match in candidates:
            groups[match].append(unknown_path)
            del groups[key]
        elif ask_human is not None:
            answer = ask_human(unknown_path, texts[unknown_path], sorted(candidates))
            resolved = _normalize_course_code(answer) if answer else None
            if resolved and resolved != UNKNOWN_COURSE:
                groups.setdefault(resolved, []).append(unknown_path)
                del groups[key]
            # else: human doesn't know either — leave it under its "UNKNOWN: <filename>"
            # key, still visible in the output rather than silently dropped or guessed.
    return groups


def group_by_course(dir_path: Path, ask_human: AskHuman | None = None) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    texts: dict[Path, str] = {}
    for path in sorted(dir_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            continue
        text = extract_text(path)
        texts[path] = text
        code = _normalize_course_code(identify_course(text))
        if code == UNKNOWN_COURSE:
            # Don't lump unrelated unclassifiable documents into one shared bucket —
            # each gets its own filename-tagged key so it surfaces for manual
            # reconciliation instead of silently merging into (or corrupting) a real
            # course's group.
            code = f"{UNKNOWN_COURSE}: {path.name}"
        groups.setdefault(code, []).append(path)
    return _reconcile_unknowns(groups, texts, ask_human)


def _warn_if_weights_dont_sum_to_one(record: dict) -> None:
    weights = [c["weight"] for c in record.get("categories", []) if c.get("weight") is not None]
    total = sum(weights)
    if weights and abs(total - 1.0) > 0.05:
        warnings.warn(
            f"{record.get('course', 'course')}: category weights sum to {total:.2f}, not ~1.0",
            stacklevel=2,
        )


def parse_course_documents(paths: list[Path], model: str = "claude-sonnet-5") -> dict:
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    bundle = "\n\n".join(f"=== {path.name} ===\n{extract_text(path)}" for path in paths)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_PARSE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": bundle}],
        tools=[_RECORD_COURSE_TOOL],
        tool_choice={"type": "tool", "name": "record_course"},
    )
    record = _tool_input(message, "record_course")
    record.setdefault("notes", None)
    _warn_if_weights_dont_sum_to_one(record)
    return record


def parse_all_courses(dir_path: Path, ask_human: AskHuman | None = None) -> dict[str, dict]:
    return {code: parse_course_documents(paths) for code, paths in group_by_course(dir_path, ask_human).items()}


if __name__ == "__main__":
    import json

    default_dir = Path(__file__).resolve().parent.parent.parent / "data" / "courses"
    print(json.dumps(parse_all_courses(default_dir), indent=2))
