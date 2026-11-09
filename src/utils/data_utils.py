from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from src.utils import Logger

PARENT = Path(__file__).resolve().parents[1]
ROOT = Path(os.path.abspath(".")).resolve()
DATA_DIR = ROOT / "data"

RESULTS_DIR = ROOT / "results"

# [MAKEDIR] Try make results dir if not exist
if not os.path.exists(RESULTS_DIR):
    Logger.info("The directory 'results' does not exist")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(RESULTS_DIR):
        Logger.error("The directory 'results' does not exist")
    else:
        Logger.info("Successfully maked the directory")

def load_courses() -> list[dict[str, Any]]:
    """Load the course catalog and convert credits to integers."""
    with (DATA_DIR / "courses.csv").open(encoding="utf-8", newline="") as file:
        courses = list(csv.DictReader(file))
    for course in courses:
        course["credits"] = int(course["credits"])
        course["recommended_year"] = int(course["recommended_year"])
    return courses


def load_profiles() -> dict[str, dict[str, Any]]:
    """Load the example student profiles."""
    with (DATA_DIR / "profiles.json").open(encoding="utf-8") as file:
        return json.load(file)


def courses_as_text(courses: list[dict[str, Any]]) -> str:
    """Convert the course catalog into text suitable for an LLM prompt."""
    lines = [
        "course_id | name | department | year | type | prerequisites | category | credits | difficulty | day | time"
    ]
    for course in courses:
        lines.append(
            f'{course["course_id"]} | {course["course_name"]} | '
            f'{course["department"]} | {course["recommended_year"]} | '
            f'{course["type"]} | {course["prerequisites"]} | '
            f'{course["category"]} | {course["credits"]} | '
            f'{course["difficulty"]} | {course["day"]} | '
            f'{course["start_time"]}-{course["end_time"]}'
        )
    return "\n".join(lines)
