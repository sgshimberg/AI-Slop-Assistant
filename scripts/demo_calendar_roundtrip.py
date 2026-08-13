"""Manual demo: watch a Phase 1 CRUD round-trip happen live in Google Calendar.

Not a test — pauses between each step so you can switch to the Calendar UI
(web or app) and see the event appear / change / disappear in real time.
Runs against the dedicated 'testing' calendar (GOOGLE_TEST_CALENDAR_ID) — see
scripts/create_test_calendar.py to set one up. Make sure 'testing' is checked
in your calendar list sidebar so its events are visible.

Run:  python -m scripts.demo_calendar_roundtrip [delay_seconds]
Default delay is 8 seconds per step.
"""

import datetime
import sys
import time

from src import config
from src.integrations.google_calendar import create_event, delete_event, get_event, update_event

TZ = "America/New_York"
CALENDAR_ID = config.GOOGLE_TEST_CALENDAR_ID or "primary"


def pause(seconds: float, message: str) -> None:
    print(f"\n{message}")
    print(f"Waiting {seconds:.0f}s — check Google Calendar now...")
    time.sleep(seconds)


def main() -> None:
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0

    start = datetime.datetime.now() + datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)

    print("Step 1: creating event...")
    created = create_event(
        summary="Phase 1 demo event",
        start=start,
        end=end,
        description="Created by scripts/demo_calendar_roundtrip.py",
        timezone=TZ,
        calendar_id=CALENDAR_ID,
    )
    event_id = created["id"]
    print(f"Created: {created['summary']} (id={event_id})")
    pause(delay, "Event should now appear on your calendar tomorrow.")

    print("Step 2: fetching event...")
    fetched = get_event(event_id, calendar_id=CALENDAR_ID)
    print(f"Fetched: {fetched['summary']} @ {fetched['start']['dateTime']}")
    pause(delay, "Fetched the same event back (no visible change).")

    print("Step 3: updating event...")
    updated = update_event(event_id, calendar_id=CALENDAR_ID, summary="Phase 1 demo event (updated)")
    print(f"Updated: {updated['summary']}")
    pause(delay, "Event title should now show '(updated)' on your calendar.")

    print("Step 4: deleting event...")
    delete_event(event_id, calendar_id=CALENDAR_ID)
    print("Deleted.")
    pause(delay, "Event should now be gone from your calendar.")

    print("Step 5: confirming deletion...")
    confirmed = get_event(event_id, calendar_id=CALENDAR_ID)
    print(f"Final status: {confirmed['status']}")


if __name__ == "__main__":
    main()
