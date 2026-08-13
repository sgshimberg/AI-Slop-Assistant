"""Moodle calendar ingestion: fetch the .ics feed and parse it into structured events.

Run:  python -m src.integrations.moodle
Tries the Moodle web service API first (MOODLE_TOKEN); falls back to the personal
calendar ICS export feed (MOODLE_ICS_URL) if no token is available — see CREDENTIALS.md.

`fetch_ics_text` (network) and `parse_ics` (pure) are split so `parse_ics` can run
against a static fixture file with no network/`.env` dependency — see docs/PHASE2.md.
"""

import datetime
import re

import requests
from icalendar import Calendar

from src import config

_TYPE_KEYWORDS = [
    ("exam", "exam"),
    ("quiz", "quiz"),
    ("is due", "assignment"),
    ("homework", "assignment"),
    ("assignment", "assignment"),
    ("project", "assignment"),
]

_COURSE_PREFIX_RE = re.compile(r"^([A-Z]{2,5}\s?\d{3}[A-Z]?):\s*(.+)$")
_DUE_SUFFIX_RE = re.compile(r"\s+is due$", re.IGNORECASE)


def _via_api() -> list[dict]:
    url = f"{config.MOODLE_BASE_URL}/webservice/rest/server.php"
    params = {
        "wstoken": config.MOODLE_TOKEN,
        "wsfunction": "core_calendar_get_calendar_upcoming_view",
        "moodlewsrestformat": "json",
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    if "exception" in data:
        raise RuntimeError(f"Moodle API error: {data.get('message', data)}")
    return [
        {"name": event["name"], "when": datetime.datetime.fromtimestamp(event["timestart"])}
        for event in data.get("events", [])
    ]


def fetch_ics_text(url: str) -> str:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.text


def _classify_type(raw_summary: str) -> str:
    lowered = raw_summary.lower()
    for keyword, event_type in _TYPE_KEYWORDS:
        if keyword in lowered:
            return event_type
    return "other"


def _split_course_and_name(raw_summary: str) -> tuple[str | None, str]:
    match = _COURSE_PREFIX_RE.match(raw_summary)
    if not match:
        return None, raw_summary
    course, rest = match.group(1), match.group(2)
    name = _DUE_SUFFIX_RE.sub("", rest)
    return course, name


def parse_ics(ics_text: str) -> list[dict]:
    """Parse ICS text into structured events. Pure — no network, no date filtering."""
    cal = Calendar.from_ical(ics_text)
    events = []
    for component in cal.walk("VEVENT"):
        start = component.get("dtstart").dt
        if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)

        raw_summary = str(component.get("summary"))
        course, name = _split_course_and_name(raw_summary)
        url_prop = component.get("url")

        events.append({
            "name": name,
            "raw_summary": raw_summary,
            "course": course,
            "type": _classify_type(raw_summary),
            "due": start.isoformat(),
            "url": str(url_prop) if url_prop else None,
        })
    return sorted(events, key=lambda e: e["due"])


def _via_ics() -> list[dict]:
    ics_text = fetch_ics_text(config.MOODLE_ICS_URL)
    now = datetime.datetime.now(datetime.timezone.utc)
    events = parse_ics(ics_text)
    upcoming = [e for e in events if datetime.datetime.fromisoformat(e["due"]) >= now]
    return [{"name": e["name"], "when": datetime.datetime.fromisoformat(e["due"])} for e in upcoming]


def list_upcoming_events() -> list[dict]:
    if config.MOODLE_TOKEN:
        return _via_api()
    if config.MOODLE_ICS_URL:
        return _via_ics()
    raise RuntimeError("Set either MOODLE_TOKEN or MOODLE_ICS_URL in .env — see CREDENTIALS.md")


if __name__ == "__main__":
    for event in list_upcoming_events()[:10]:
        print(f"{event['when']} — {event['name']}")
