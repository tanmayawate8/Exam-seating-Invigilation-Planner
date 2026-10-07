"""
Student Schemas and Validation Module.
Handles validation for student creation, modification, and response serialization.
"""

from typing import Any, Dict
from app.models.student import Student
from app.models.department import Department
from app.utils.validators import (
    validate_required_fields,
    validate_positive_int,
    validate_entity_exists,
    validate_unique_field,
)


def validate_student_create_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload for student registration.
    Required: username, email, password, roll_number, enrollment_number,
              first_name, last_name, department_id, semester, academic_year
    """
    validate_required_fields(data, [
        "username", "email", "password",
        "roll_number", "enrollment_number",
        "first_name", "last_name",
        "department_id", "semester", "academic_year"
    ])

    # Validate department exists
    dept_id = validate_positive_int(data["department_id"], "department_id")
    validate_entity_exists(Department, dept_id, "Department")

    # Validate semester
    semester = validate_positive_int(data["semester"], "semester", min_val=1, max_val=12)

    # Validate uniqueness of roll number and enrollment number
    roll_number = str(data["roll_number"]).strip().upper()
    enrollment_number = str(data["enrollment_number"]).strip().upper()
    validate_unique_field(Student, "roll_number", roll_number)
    validate_unique_field(Student, "enrollment_number", enrollment_number)

    return {
        "username": str(data["username"]).strip(),
        "email": str(data["email"]).strip().lower(),
        "password": str(data["password"]),
        "roll_number": roll_number,
        "enrollment_number": enrollment_number,
        "first_name": str(data["first_name"]).strip(),
        "last_name": str(data["last_name"]).strip(),
        "department_id": dept_id,
        "semester": semester,
        "academic_year": str(data["academic_year"]).strip(),
    }


def validate_student_update_payload(student_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates payload for updating an existing student record."""
    if not isinstance(data, dict):
        from app.utils.errors import ValidationError
        raise ValidationError("Request body must be a valid JSON object.")

    cleaned = {}

    if "first_name" in data and str(data["first_name"]).strip():
        cleaned["first_name"] = str(data["first_name"]).strip()

    if "last_name" in data and str(data["last_name"]).strip():
        cleaned["last_name"] = str(data["last_name"]).strip()

    if "department_id" in data:
        dept_id = validate_positive_int(data["department_id"], "department_id")
        validate_entity_exists(Department, dept_id, "Department")
        cleaned["department_id"] = dept_id

    if "semester" in data:
        cleaned["semester"] = validate_positive_int(data["semester"], "semester", min_val=1, max_val=12)

    if "academic_year" in data and str(data["academic_year"]).strip():
        cleaned["academic_year"] = str(data["academic_year"]).strip()

    if "roll_number" in data:
        roll = str(data["roll_number"]).strip().upper()
        validate_unique_field(Student, "roll_number", roll, exclude_id=student_id)
        cleaned["roll_number"] = roll

    if "enrollment_number" in data:
        enrollment = str(data["enrollment_number"]).strip().upper()
        validate_unique_field(Student, "enrollment_number", enrollment, exclude_id=student_id)
        cleaned["enrollment_number"] = enrollment

    return cleaned


def serialize_student(student: Student) -> Dict[str, Any]:
    """Serializes student model into standardized JSON dictionary."""
    return student.to_dict() if student else {}
