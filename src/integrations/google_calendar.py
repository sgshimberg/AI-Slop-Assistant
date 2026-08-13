"""Google Calendar integration: CRUD for events on the primary calendar.

Run:  python -m src.integrations.google_calendar
First run opens a browser for one-time OAuth consent, then caches a token per
GOOGLE_TOKEN_FILE. Requires GOOGLE_CLIENT_SECRET_FILE (downloaded OAuth client JSON).
"""

import datetime

from googleapiclient.discovery import build

from src.integrations.google_auth import get_credentials


def _service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def create_event(
    summary: str,
    start: datetime.datetime,
    end: datetime.datetime,
    description: str = "",
    timezone: str = "America/New_York",
    calendar_id: str = "primary",
) -> dict:
    service = _service()
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": timezone},
    }
    return service.events().insert(calendarId=calendar_id, body=body).execute()


def get_event(event_id: str, calendar_id: str = "primary") -> dict:
    service = _service()
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()


def update_event(event_id: str, calendar_id: str = "primary", **fields) -> dict:
    service = _service()
    event = get_event(event_id, calendar_id=calendar_id)

    if "summary" in fields:
        event["summary"] = fields.pop("summary")
    if "description" in fields:
        event["description"] = fields.pop("description")
    if "start" in fields:
        start = fields.pop("start")
        event["start"] = {
            "dateTime": start.isoformat(),
            "timeZone": event["start"].get("timeZone", "America/New_York"),
        }
    if "end" in fields:
        end = fields.pop("end")
        event["end"] = {
            "dateTime": end.isoformat(),
            "timeZone": event["end"].get("timeZone", "America/New_York"),
        }
    if "timezone" in fields:
        timezone = fields.pop("timezone")
        event["start"]["timeZone"] = timezone
        event["end"]["timeZone"] = timezone
    if fields:
        raise TypeError(f"update_event() got unexpected field(s): {', '.join(fields)}")

    return service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()


def delete_event(event_id: str, calendar_id: str = "primary") -> None:
    service = _service()
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def list_upcoming_events(max_results: int = 5, calendar_id: str = "primary") -> list[dict]:
    service = _service()
    now = datetime.datetime.utcnow().isoformat() + "Z"
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


if __name__ == "__main__":
    events = list_upcoming_events()
    if not events:
        print("No upcoming events found.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"{start} — {event.get('summary', '(no title)')}")
