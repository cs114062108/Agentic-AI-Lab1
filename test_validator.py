import json

from src.validate import ScheduleValidator

# 1. Prepare a draft course schedule
candidate = {
    "student_profile": {
        "department": "EE",
        "year": 1
    },
    "selected_courses": [
        {
            "course_id": "EE101",
            "reason": "Required course for first-year EE students."
        },
        {
            "course_id": "EE102",
            "reason": "Required course for first-year EE students."
        },
        {
            "course_id": "EE110",
            "reason": "Provides fundamental knowledge."
        },
        {
            "course_id": "EE120",
            "reason": "Provides programming knowledge."
        }
    ],
    "total_credits": 11,
    "explanation": "A balanced first-year schedule."
}

# 2. Create a Validator
validator = ScheduleValidator()

# 3. Submit the candidate course schedule to the Validator
result = validator.validate(
    raw_schedule=json.dumps(candidate),
    completed_courses=[],
    min_credits=9,
    max_credits=18
)

# 4. View Verification Results
print("Valid:", result.valid)
print("Recalculated Credits:", result.recalculated_total_credits)

print("Violations:")
for violation in result.violations:
    print("-", violation)
    