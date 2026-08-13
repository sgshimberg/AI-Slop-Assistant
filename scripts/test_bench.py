"""Interactive test bench: run any check or demo from Phases 0-3 in one place.

Run:  python -m scripts.test_bench          # interactive menu, loops until you quit
      python -m scripts.test_bench 3        # run item 3 once, then exit (for scripting)

Doesn't duplicate any logic — every item just shells out to the real
module/script/pytest target that already exists (see each file's own
docstring), inheriting your terminal so interactive bits still work: input()
prompts (Phase 3's ask_human), sleeps (Phase 1's demo pauses), etc.

Items marked (live) hit a real external API. Items marked with a warning
prompt for confirmation first because they cost money, send a real message,
or may block on terminal input.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Item:
    def __init__(self, key: str, label: str, args: list[str], warn: str | None = None):
        self.key = key
        self.label = label
        self.args = args
        self.warn = warn


ITEMS = [
    Item(
        "1",
        "Automated test suite — everything (pytest)  [includes a live Calendar\n"
        "     round-trip against your 'testing' calendar, not primary]",
        ["-m", "pytest", "-v"],
    ),
    Item(
        "2",
        "  Phase 1 only — Google Calendar CRUD round-trip (live 'testing' calendar)",
        ["-m", "pytest", "-v", "tests/test_google_calendar_roundtrip.py"],
    ),
    Item(
        "3",
        "  Phase 2 only — Moodle .ics parsing, synthetic fixture (offline)",
        ["-m", "pytest", "-v", "tests/test_moodle_parse.py"],
    ),
    Item(
        "4",
        "  Phase 3 only — syllabus/course parser, mocked Anthropic calls (offline)",
        ["-m", "pytest", "-v", "tests/test_syllabus_parse.py"],
    ),
    Item("5", "Phase 0 — weather (live: OpenWeatherMap)", ["-m", "src.integrations.weather"]),
    Item("6", "Phase 0 — Google Tasks: list task lists (live)", ["-m", "src.integrations.google_tasks"]),
    Item(
        "7",
        "Phase 0 — Moodle: list upcoming events (live token/ICS — ICS is known to\n"
        "     return 0 events between semesters, see PROJECT.md Phase 12)",
        ["-m", "src.integrations.moodle"],
    ),
    Item("8", "Phase 0 — Anthropic: ask Claude a one-liner (live)", ["-m", "src.integrations.llm"]),
    Item(
        "9",
        "Phase 0 — WhatsApp: send yourself a real message via Twilio",
        ["-m", "src.integrations.whatsapp"],
        warn="Sends a real WhatsApp message and counts against your Twilio sandbox/session window.",
    ),
    Item(
        "10",
        "Phase 1 — live visual demo: create/get/update/delete, paused ~8s/step\n"
        "     (switch to Google Calendar to watch it happen)",
        ["-m", "scripts.demo_calendar_roundtrip"],
    ),
    Item(
        "11",
        "Phase 2 — dump the bundled synthetic fixture to JSON (offline)",
        ["-m", "scripts.dump_moodle_events", "tests/fixtures/moodle_sample.ics"],
    ),
    Item(
        "12",
        "Phase 3 — parse everything in data/courses/ to JSON (live Anthropic API)",
        ["-m", "scripts.parse_courses"],
        warn="Hits the live Anthropic API (real cost) and may prompt you in the "
        "terminal if a document's course can't be determined.",
    ),
]


def confirm(message: str) -> bool:
    answer = input(f"  {message}\n  Continue? [y/N]: ").strip().lower()
    return answer == "y"


def run_item(item: Item) -> None:
    if item.warn and not confirm(item.warn):
        print("  Skipped.")
        return
    cmd = [sys.executable, *item.args]
    print(f"\n$ {' '.join(item.args)}\n" + "-" * 70)
    result = subprocess.run(cmd, cwd=ROOT)
    print("-" * 70)
    print(f"[exit code {result.returncode}]")


def print_menu() -> None:
    print("\n=== WhatsApp Assistant — Test Bench (Phases 0-3) ===\n")
    for item in ITEMS:
        print(f" {item.key:>2}) {item.label}")
    print("  q) Quit")


def main() -> None:
    if len(sys.argv) > 1:
        key = sys.argv[1]
        item = next((i for i in ITEMS if i.key == key), None)
        if item is None:
            print(f"No such item: {key}", file=sys.stderr)
            sys.exit(1)
        run_item(item)
        return

    while True:
        print_menu()
        choice = input("\nSelect an option: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            break
        item = next((i for i in ITEMS if i.key == choice), None)
        if item is None:
            print("Not a valid option.")
            continue
        run_item(item)


if __name__ == "__main__":
    main()
