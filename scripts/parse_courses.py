"""Phase 3 manual verification: parse every course document in a flat dropbox and
print the structured result as JSON for eyeballing against the real syllabi/calendars.

Run:  python -m scripts.parse_courses           # defaults to data/courses/
      python -m scripts.parse_courses path/to/dir

Hits the live Anthropic API (ANTHROPIC_API_KEY) — see docs/PHASE3.md test gate.
Documents that can't be classified by content, even after cross-referencing against
already-identified courses, trigger a terminal prompt instead of a silent guess (see
`_ask_human` below and `AskHuman` in src/integrations/syllabus.py).
"""

import json
import sys
from pathlib import Path

from src.integrations.syllabus import parse_all_courses

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "courses"


def _ask_human(path: Path, text: str, known_courses: list[str]) -> str | None:
    print(f"\nCouldn't determine the course for: {path.name}", file=sys.stderr)
    if known_courses:
        print(f"Known courses so far: {', '.join(known_courses)}", file=sys.stderr)
    print(f"--- first 500 chars of {path.name} ---\n{text[:500]}\n---", file=sys.stderr)
    answer = input("Which course does this belong to? (blank if you're not sure either): ").strip()
    return answer or None


def main() -> None:
    dir_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    if not dir_path.is_dir():
        print(f"Not a directory: {dir_path}", file=sys.stderr)
        sys.exit(1)

    records = parse_all_courses(dir_path, ask_human=_ask_human)
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
