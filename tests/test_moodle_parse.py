"""Phase 2 test gate: parse a static .ics fixture into structured events.

Uses tests/fixtures/moodle_sample.ics — a hand-written, synthetic fixture (not real
Moodle data; see docs/PHASE2.md for why). Pure/offline: no network, no .env needed.
"""

from pathlib import Path

from src.integrations.moodle import parse_ics

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "moodle_sample.ics"


def _parsed():
    return parse_ics(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_parses_all_events():
    events = _parsed()
    assert len(events) == 6


def test_assignment_with_course_prefix_and_due_suffix():
    events = _parsed()
    event = next(e for e in events if e["raw_summary"] == "CSC 316: Homework 3 is due")
    assert event["course"] == "CSC 316"
    assert event["name"] == "Homework 3"
    assert event["type"] == "assignment"
    assert event["due"] == "2026-02-10T04:59:00+00:00"
    assert event["url"] == "https://moodle-courses2527.wolfware.ncsu.edu/mod/assign/view.php?id=10001"


def test_quiz_classified_correctly():
    events = _parsed()
    event = next(e for e in events if e["raw_summary"] == "ENGR 101: Quiz 4 is due")
    assert event["course"] == "ENGR 101"
    assert event["type"] == "quiz"


def test_exam_classified_correctly():
    events = _parsed()
    event = next(e for e in events if e["raw_summary"] == "MA 242: Final Exam")
    assert event["course"] == "MA 242"
    assert event["name"] == "Final Exam"
    assert event["type"] == "exam"


def test_event_without_course_prefix_or_url():
    events = _parsed()
    event = next(e for e in events if e["raw_summary"] == "ENGR 101: Team Design Review")
    # "ENGR 101:" matches the course-prefix pattern even without a due-date suffix.
    assert event["course"] == "ENGR 101"
    assert event["name"] == "Team Design Review"
    assert event["type"] == "other"
    assert event["url"] is None


def test_events_sorted_by_due_date():
    events = _parsed()
    dues = [e["due"] for e in events]
    assert dues == sorted(dues)
