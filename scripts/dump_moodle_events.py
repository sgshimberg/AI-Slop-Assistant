"""Phase 2 manual verification: dump a parsed .ics file's events as JSON.

Run:  python -m scripts.dump_moodle_events tests/fixtures/moodle_sample.ics
      python -m scripts.dump_moodle_events path/to/real_export.ics

Reads a local .ics file (no network) and prints structured JSON to stdout for
eyeballing against known assignments/exams — see docs/PHASE2.md test gate.
"""

import json
import sys
from pathlib import Path

from src.integrations.moodle import parse_ics


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.dump_moodle_events <path-to-ics>", file=sys.stderr)
        sys.exit(1)

    ics_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    events = parse_ics(ics_text)
    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
