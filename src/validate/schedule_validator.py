from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from src.utils.data_utils import ROOT

@dataclass(frozen=True)
class Course:
    course_id: str
    course_name: str
    department: str
    recommended_year: int
    course_type: str
    prerequisites: tuple[str, ...]
    category: str
    credits: int
    difficulty: str
    day: str
    start_time: str
    end_time: str


@dataclass
class ValidationResult:
    valid: bool
    recalculated_total_credits: int | None
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the result in a JSON-serializable format."""
        return asdict(self)


class ScheduleValidator:
    """Validate a proposed schedule against the supplied schema and catalog.

    The JSON Schema handles structural validation. This class handles catalog
    and planning constraints that are not represented in the schema.
    """
    catalog_path: str | Path   
    schema_path: str | Path
    
    def __init__(
        self,
        *,
        require_programming_course: bool = True,
    ) -> None:
        self.catalog_path = ROOT / "data/courses.csv"
        self.schema_path = ROOT / "schemas/schedule_schema.json"
        self.catalog = self._load_catalog(self.catalog_path)

        with self.schema_path.open("r", encoding="utf-8") as file:
            self.schema = json.load(file)

        Draft202012Validator.check_schema(self.schema)
        self.schema_validator = Draft202012Validator(self.schema)
        self.require_programming_course = require_programming_course

    @staticmethod
    def _parse_prerequisites(raw: str | None) -> tuple[str, ...]:
        if not raw or raw.strip().lower() in {"none", "n/a", "null"}:
            return ()
        return tuple(
            item.strip()
            for item in raw.split(";")
            if item.strip()
        )

    @classmethod
    def _load_catalog(cls, path: Path) -> dict[str, Course]:
        catalog: dict[str, Course] = {}

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            required_columns = {
                "course_id", "course_name", "department", "recommended_year",
                "type", "prerequisites", "category", "credits", "difficulty",
                "day", "start_time", "end_time",
            }
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(
                    "Course catalog is missing columns: "
                    + ", ".join(sorted(missing_columns))
                )

            for line_number, row in enumerate(reader, start=2):
                course_id = (row.get("course_id") or "").strip()
                if not course_id:
                    raise ValueError(f"Missing course_id at CSV line {line_number}")
                if course_id in catalog:
                    raise ValueError(f"Duplicate course_id in catalog: {course_id}")

                try:
                    course = Course(
                        course_id=course_id,
                        course_name=(row.get("course_name") or "").strip(),
                        department=(row.get("department") or "").strip(),
                        recommended_year=int(row["recommended_year"]),
                        course_type=(row.get("type") or "").strip().lower(),
                        prerequisites=cls._parse_prerequisites(row.get("prerequisites")),
                        category=(row.get("category") or "").strip().lower(),
                        credits=int(row["credits"]),
                        difficulty=(row.get("difficulty") or "").strip(),
                        day=(row.get("day") or "").strip(),
                        start_time=(row.get("start_time") or "").strip(),
                        end_time=(row.get("end_time") or "").strip(),
                    )
                except (TypeError, ValueError, KeyError) as error:
                    raise ValueError(
                        f"Invalid course data at CSV line {line_number}: {error}"
                    ) from error

                catalog[course_id] = course

        return catalog

    @staticmethod
    def _to_minutes(value: str) -> int:
        try:
            hour_text, minute_text = value.split(":", maxsplit=1)
            hour, minute = int(hour_text), int(minute_text)
        except (ValueError, AttributeError) as error:
            raise ValueError(f"Invalid time value: {value!r}; expected HH:MM") from error

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time value: {value!r}; expected HH:MM")
        return hour * 60 + minute

    @staticmethod
    def _format_schema_error(error: Any) -> str:
        path = ".".join(str(part) for part in error.absolute_path)
        location = f" at '{path}'" if path else ""
        return f"Schema error{location}: {error.message}"

    def validate(
        self,
        raw_schedule: str | dict[str, Any],
        *,
        completed_courses: Iterable[str] | None = None,
        min_credits: int | None = None,
        max_credits: int | None = None,
        required_course_ids: Iterable[str] | None = None,
        unavailable_times: Iterable[dict[str, str]] | None = None,
        require_programming_course: bool | None = None,
    ) -> ValidationResult:
        """Validate one LLM schedule.

        Args:
            raw_schedule: JSON text returned by the LLM, or an already parsed dict.
            completed_courses: Courses the student has already completed. These
                are supplied separately because the required output schema only
                contains department and year in student_profile.
            min_credits/max_credits: Optional allowed credit range from the request
                or StudentProfile. A missing bound is not enforced.
            required_course_ids: Optional explicit required-course list. If omitted,
                the validator requires catalog courses whose type is 'required',
                department matches the student's department, and recommended_year
                equals the student's year. Already completed courses are excluded.
            unavailable_times: Optional time blocks that must remain free, e.g.
                [{"day": "Fri", "start_time": "12:00", "end_time": "18:00",
                  "label": "Friday afternoon must remain free"}].
            require_programming_course: Override the additional constraint. By
                default, at least one selected course must have category 'programming'.
        """
        violations: list[str] = []

        # Parse the model output. A parsing failure makes credit calculation
        # impossible, so return None as required by the assignment.
        if isinstance(raw_schedule, str):
            try:
                schedule = json.loads(raw_schedule)
            except json.JSONDecodeError as error:
                return ValidationResult(
                    valid=False,
                    recalculated_total_credits=None,
                    violations=[
                        f"Invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})"
                    ],
                )
        elif isinstance(raw_schedule, dict):
            schedule = raw_schedule
        else:
            return ValidationResult(
                valid=False,
                recalculated_total_credits=None,
                violations=["The schedule must be a JSON object or JSON string."],
            )

        # 1. Structural validation using the supplied JSON Schema.
        schema_errors = sorted(
            self.schema_validator.iter_errors(schedule),
            key=lambda error: (
                list(str(part) for part in error.absolute_path),
                error.message,
            ),
        )
        violations.extend(self._format_schema_error(error) for error in schema_errors)

        profile = schedule.get("student_profile")
        if not isinstance(profile, dict):
            profile = {}
        department = profile.get("department")
        year = profile.get("year")

        raw_selected = schedule.get("selected_courses")
        if not isinstance(raw_selected, list):
            # Without a usable course list, the total cannot be recalculated.
            return ValidationResult(
                valid=False,
                recalculated_total_credits=None,
                violations=violations + [
                    "Cannot recalculate credits: 'selected_courses' must be an array."
                ],
            )

        # Extract IDs while retaining malformed entries as validation failures.
        selected_ids: list[str] = []
        for index, item in enumerate(raw_selected):
            if not isinstance(item, dict) or not isinstance(item.get("course_id"), str):
                violations.append(
                    f"selected_courses[{index}] must be an object with a string course_id."
                )
                continue
            course_id = item["course_id"].strip()
            if not course_id:
                violations.append(f"selected_courses[{index}].course_id cannot be empty.")
                continue
            selected_ids.append(course_id)

        # Recalculate credits using each known course only once. If any ID is
        # unknown, the complete schedule total cannot be calculated reliably.
        unknown_ids = sorted({course_id for course_id in selected_ids if course_id not in self.catalog})
        if unknown_ids:
            for course_id in unknown_ids:
                violations.append(f"Course '{course_id}' does not exist in the supplied catalog.")
            recalculated_credits: int | None = None
        elif len(selected_ids) != len(raw_selected):
            recalculated_credits = None
            violations.append(
                "Cannot recalculate credits: one or more selected course entries have an invalid course_id."
            )
        else:
            unique_ids = set(selected_ids)
            recalculated_credits = sum(self.catalog[course_id].credits for course_id in unique_ids)

        # 2. Duplicate courses and already-completed courses.
        seen: set[str] = set()
        for course_id in selected_ids:
            if course_id in seen:
                violations.append(f"Course '{course_id}' is selected more than once.")
            seen.add(course_id)

        completed_is_known = completed_courses is not None
        completed = set(completed_courses or [])
        if not completed_is_known:
            violations.append(
                "Cannot fully validate completed-course and prerequisite constraints: "
                "completed_courses was not provided (use [] if the student has completed none)."
            )
        else:
            for course_id in sorted(set(selected_ids) & completed):
                violations.append(f"Course '{course_id}' has already been completed by the student.")

        known_selected = {
            course_id for course_id in selected_ids
            if course_id in self.catalog
        }

        # 3. Prerequisites must have been completed before this schedule.
        # A course selected in the same proposed schedule does not count as
        # a completed prerequisite.
        if completed_is_known:
            for course_id in sorted(known_selected):
                course = self.catalog[course_id]
                missing = [
                    prerequisite for prerequisite in course.prerequisites
                    if prerequisite not in completed
                ]
                if missing:
                    violations.append(
                        f"Course '{course_id}' has unsatisfied prerequisite(s): "
                        + ", ".join(missing)
                        + "."
                    )

        # 4. Compare the model-reported credits with the catalog recalculation.
        reported_credits = schedule.get("total_credits")
        if recalculated_credits is not None and isinstance(reported_credits, int) and not isinstance(reported_credits, bool):
            if reported_credits != recalculated_credits:
                violations.append(
                    f"Reported total_credits is {reported_credits}, but the catalog total is {recalculated_credits}."
                )

        # 5. Check the allowed credit range supplied by the application/user.
        if min_credits is not None and max_credits is not None and min_credits > max_credits:
            violations.append(
                f"Invalid validator configuration: min_credits ({min_credits}) "
                f"is greater than max_credits ({max_credits})."
            )
        elif recalculated_credits is not None:
            if min_credits is not None and recalculated_credits < min_credits:
                violations.append(
                    f"Total credits {recalculated_credits} is below the minimum of {min_credits}."
                )
            if max_credits is not None and recalculated_credits > max_credits:
                violations.append(
                    f"Total credits {recalculated_credits} exceeds the maximum of {max_credits}."
                )

        # 6. Required courses: by default, courses required by this department
        # for this student's current recommended year. Applications can pass an
        # explicit list if their academic policy differs.
        if required_course_ids is None:
            if isinstance(department, str) and isinstance(year, int) and not isinstance(year, bool):
                required_ids = {
                    course.course_id
                    for course in self.catalog.values()
                    if course.course_type == "required"
                    and course.department == department
                    and course.recommended_year == year
                }
            else:
                required_ids = set()
        else:
            required_ids = set(required_course_ids)

        if completed_is_known:
            required_ids -= completed
        missing_required = sorted(required_ids - known_selected)
        if missing_required:
            violations.append(
                "Required course(s) are missing: " + ", ".join(missing_required) + "."
            )

        # 7. Check pairwise timetable conflicts. Adjacent classes are allowed.
        valid_timed_courses: list[Course] = []
        for course_id in sorted(known_selected):
            course = self.catalog[course_id]
            try:
                start = self._to_minutes(course.start_time)
                end = self._to_minutes(course.end_time)
                if start >= end:
                    raise ValueError("start_time must be earlier than end_time")
            except ValueError as error:
                violations.append(f"Invalid timetable data for '{course_id}': {error}.")
                continue
            valid_timed_courses.append(course)

        for index, first in enumerate(valid_timed_courses):
            first_start = self._to_minutes(first.start_time)
            first_end = self._to_minutes(first.end_time)
            for second in valid_timed_courses[index + 1:]:
                if first.day.strip().lower() != second.day.strip().lower():
                    continue
                second_start = self._to_minutes(second.start_time)
                second_end = self._to_minutes(second.end_time)
                if first_start < second_end and second_start < first_end:
                    violations.append(
                        f"Time conflict: '{first.course_id}' ({first.day} "
                        f"{first.start_time}-{first.end_time}) overlaps with "
                        f"'{second.course_id}' ({second.day} "
                        f"{second.start_time}-{second.end_time})."
                    )

        # 8. Additional constraint required by Q2: at least one programming course.
        programming_required = (
            self.require_programming_course
            if require_programming_course is None
            else require_programming_course
        )
        if programming_required and not any(
            self.catalog[course_id].category == "programming"
            for course_id in known_selected
        ):
            violations.append(
                "Additional constraint violated: the schedule must include "
                "at least one programming course."
            )

        # 9. User-defined unavailable time blocks. Q3's Friday-afternoon-free
        # case can be expressed here without hard-coding it into the validator.
        for block in unavailable_times or []:
            try:
                blocked_day = block["day"].strip().lower()
                blocked_start = self._to_minutes(block["start_time"])
                blocked_end = self._to_minutes(block["end_time"])
                label = block.get("label") or (
                    f"{block['day']} {block['start_time']}-{block['end_time']} must remain free"
                )
                if blocked_start >= blocked_end:
                    raise ValueError("blocked start_time must be earlier than end_time")
            except (KeyError, AttributeError, ValueError) as error:
                violations.append(f"Invalid unavailable-time constraint: {error}.")
                continue

            for course in valid_timed_courses:
                if course.day.strip().lower() != blocked_day:
                    continue
                course_start = self._to_minutes(course.start_time)
                course_end = self._to_minutes(course.end_time)
                if course_start < blocked_end and blocked_start < course_end:
                    violations.append(
                        f"Unavailable-time constraint violated: '{course.course_id}' "
                        f"({course.day} {course.start_time}-{course.end_time}) conflicts "
                        f"with '{label}'."
                    )

        return ValidationResult(
            valid=(len(violations) == 0),
            recalculated_total_credits=recalculated_credits,
            violations=violations,
        )
