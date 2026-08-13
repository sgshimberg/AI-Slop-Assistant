"""One-time setup: create (or find) a dedicated 'testing' Google Calendar.

Keeps Phase 1 test/demo runs off your primary calendar. Idempotent — if a
calendar named 'testing' already exists, reuses it instead of duplicating.

Run:  python -m scripts.create_test_calendar
Prints the calendar ID to add to .env as GOOGLE_TEST_CALENDAR_ID.
"""

from googleapiclient.discovery import build

from src.integrations.google_auth import get_credentials

CALENDAR_NAME = "testing"


def get_or_create_test_calendar() -> str:
    service = build("calendar", "v3", credentials=get_credentials())

    page_token = None
    while True:
        result = service.calendarList().list(pageToken=page_token).execute()
        for entry in result.get("items", []):
            if entry.get("summary") == CALENDAR_NAME:
                return entry["id"]
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    created = service.calendars().insert(body={"summary": CALENDAR_NAME}).execute()
    return created["id"]


if __name__ == "__main__":
    calendar_id = get_or_create_test_calendar()
    print(f"'{CALENDAR_NAME}' calendar ID: {calendar_id}")
    print("Add this to .env as GOOGLE_TEST_CALENDAR_ID.")
