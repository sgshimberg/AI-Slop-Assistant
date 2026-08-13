"""Phase 0 hello-world: list the next 5 upcoming Google Calendar events.

Run:  python -m src.integrations.google_calendar
First run opens a browser for one-time OAuth consent, then caches a token per
GOOGLE_TOKEN_FILE. Requires GOOGLE_CLIENT_SECRET_FILE (downloaded OAuth client JSON).
"""

import datetime

from googleapiclient.discovery import build

from src.integrations.google_auth import get_credentials


def list_upcoming_events(max_results: int = 5) -> list[dict]:
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.datetime.utcnow().isoformat() + "Z"
    result = (
        service.events()
        .list(
            calendarId="primary",
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
