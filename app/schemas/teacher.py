"""
Teacher Schemas and Validation Module.
Handles validation for faculty creation, modification, availability submission, and serialization.
"""

from typing import Any, Dict
from app.models.teacher import Teacher
from app.models.department import Department
from app.utils.validators import (
    validate_required_fields,
    validate_positive_int,
    validate_date,
    validate_session_name,
    validate_entity_exists,
    validate_unique_field,
)


def validate_teacher_create_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload for teacher creation.
    Required: username, email, password, employee_id, first_name, last_name,
              department_id, designation
    """
    validate_required_fields(data, [
        "username", "email", "password",
        "employee_id", "first_name", "last_name",
        "department_id", "designation"
    ])

    dept_id = validate_positive_int(data["department_id"], "department_id")
    validate_entity_exists(Department, dept_id, "Department")

    emp_id = str(data["employee_id"]).strip().upper()
    validate_unique_field(Teacher, "employee_id", emp_id)

    max_duties = validate_positive_int(data.get("max_duties_per_week", 5), "max_duties_per_week", min_val=1, max_val=20)

    return {
        "username": str(data["username"]).strip(),
        "email": str(data["email"]).strip().lower(),
        "password": str(data["password"]),
        "employee_id": emp_id,
        "first_name": str(data["first_name"]).strip(),
        "last_name": str(data["last_name"]).strip(),
        "department_id": dept_id,
        "designation": str(data["designation"]).strip(),
        "phone_number": str(data.get("phone_number") or "").strip() or None,
        "max_duties_per_week": max_duties,
    }


def validate_teacher_update_payload(teacher_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates payload for updating an existing teacher record."""
    if not isinstance(data, dict):
        from app.utils.errors import ValidationError
        raise ValidationError("Request body must be a valid JSON object.")

    cleaned = {}

    if "first_name" in data and str(data["first_name"]).strip():
        cleaned["first_name"] = str(data["first_name"]).strip()

    if "last_name" in data and str(data["last_name"]).strip():
        cleaned["last_name"] = str(data["last_name"]).strip()

    if "designation" in data and str(data["designation"]).strip():
        cleaned["designation"] = str(data["designation"]).strip()

    if "department_id" in data:
        dept_id = validate_positive_int(data["department_id"], "department_id")
        validate_entity_exists(Department, dept_id, "Department")
        cleaned["department_id"] = dept_id

    if "phone_number" in data:
        cleaned["phone_number"] = str(data["phone_number"]).strip() or None

    if "max_duties_per_week" in data:
        cleaned["max_duties_per_week"] = validate_positive_int(
            data["max_duties_per_week"], "max_duties_per_week", min_val=1, max_val=20
        )

    if "employee_id" in data:
        emp_id = str(data["employee_id"]).strip().upper()
        validate_unique_field(Teacher, "employee_id", emp_id, exclude_id=teacher_id)
        cleaned["employee_id"] = emp_id

    return cleaned


def validate_availability_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload for teacher availability / leave entry.
    Required: date, time_slot, is_available
    """
    validate_required_fields(data, ["date", "time_slot"])
    avail_date = validate_date(data["date"], "date")
    slot = validate_session_name(data["time_slot"])

    return {
        "date": avail_date,
        "time_slot": slot,
        "is_available": bool(data.get("is_available", True)),
        "reason": str(data.get("reason") or "").strip() or None,
    }


def serialize_teacher(teacher: Teacher) -> Dict[str, Any]:
    """Serializes teacher model into standardized JSON dictionary."""
    return teacher.to_dict() if teacher else {}
