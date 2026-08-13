"""Phase 0 hello-world: list upcoming Moodle calendar events.

Run:  python -m src.integrations.moodle
Tries the Moodle web service API first (MOODLE_TOKEN); falls back to the personal
calendar ICS export feed (MOODLE_ICS_URL) if no token is available — see CREDENTIALS.md.
"""

import datetime

import requests
from icalendar import Calendar

from src import config


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


def _via_ics() -> list[dict]:
    response = requests.get(config.MOODLE_ICS_URL, timeout=15)
    response.raise_for_status()
    cal = Calendar.from_ical(response.text)
    now = datetime.datetime.now(datetime.timezone.utc)
    events = []
    for component in cal.walk("VEVENT"):
        start = component.get("dtstart").dt
        if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        if start >= now:
            events.append({"name": str(component.get("summary")), "when": start})
    return sorted(events, key=lambda e: e["when"])


def list_upcoming_events() -> list[dict]:
    if config.MOODLE_TOKEN:
        return _via_api()
    if config.MOODLE_ICS_URL:
        return _via_ics()
    raise RuntimeError("Set either MOODLE_TOKEN or MOODLE_ICS_URL in .env — see CREDENTIALS.md")


if __name__ == "__main__":
    for event in list_upcoming_events()[:10]:
        print(f"{event['when']} — {event['name']}")
