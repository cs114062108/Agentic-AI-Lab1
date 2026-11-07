from __future__ import annotations

import json
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.path.abspath(".")).resolve()
sys.path.insert(0, str(ROOT / "starter"))

from src.utils.data_utils import load_courses, load_profiles, courses_as_text


def main() -> None:
    courses = load_courses()
    profiles = load_profiles()
    schema = json.loads((ROOT / "schemas" / "schedule_schema.json").read_text(encoding="utf-8"))
    print(f"Loaded {len(courses)} courses and {len(profiles)} profiles.")
    print("Profile IDs:", ", ".join(profiles))
    print("Course fields:", ", ".join(courses[0]))
    print("Profile fields:", ", ".join(next(iter(profiles.values()))))
    print("Output schema:", schema["title"])
    print("First two catalog rows as prompt text:")
    print(courses_as_text(courses[:2]))


if __name__ == "__main__":
    main()
