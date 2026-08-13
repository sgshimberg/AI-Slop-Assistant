"""Phase 1 test gate: round-trip a real event through Google Calendar.

Hits the live Calendar API using the cached OAuth token (see CREDENTIALS.md).
Requires the `calendar` (write) scope — delete token.json and re-consent if
you still have an old readonly-scope token cached.

Runs against the dedicated 'testing' calendar (GOOGLE_TEST_CALENDAR_ID) rather
than primary — see scripts/create_test_calendar.py to set one up.
"""

import datetime
from zoneinfo import ZoneInfo

from src import config
from src.integrations.google_calendar import create_event, delete_event, get_event, update_event

TZ = "America/New_York"
CALENDAR_ID = config.GOOGLE_TEST_CALENDAR_ID or "primary"


def test_create_get_update_delete_roundtrip():
    start = datetime.datetime.now() + datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)

    created = create_event(
        summary="Phase 1 roundtrip test",
        start=start,
        end=end,
        description="Created by test_google_calendar_roundtrip.py",
        timezone=TZ,
        calendar_id=CALENDAR_ID,
    )
    event_id = created["id"]

    try:
        fetched = get_event(event_id, calendar_id=CALENDAR_ID)
        assert fetched["summary"] == "Phase 1 roundtrip test"
        fetched_start = datetime.datetime.fromisoformat(fetched["start"]["dateTime"].replace("Z", "+00:00"))
        expected_start = start.replace(microsecond=0, tzinfo=ZoneInfo(TZ))
        assert fetched_start == expected_start

        updated = update_event(event_id, calendar_id=CALENDAR_ID, summary="Phase 1 roundtrip test (updated)")
        assert updated["summary"] == "Phase 1 roundtrip test (updated)"

        refetched = get_event(event_id, calendar_id=CALENDAR_ID)
        assert refetched["summary"] == "Phase 1 roundtrip test (updated)"
    finally:
        delete_event(event_id, calendar_id=CALENDAR_ID)

    deleted = get_event(event_id, calendar_id=CALENDAR_ID)
    assert deleted["status"] == "cancelled"
