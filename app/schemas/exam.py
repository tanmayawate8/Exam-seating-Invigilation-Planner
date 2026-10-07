"""
Exam Schemas and Validation Module.
Handles validation for exam timetable creation, updates, and student registrations.
"""

from typing import Any, Dict
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.student import Student
from app.models.registration import Registration
from app.utils.validators import (
    validate_required_fields,
    validate_date,
    validate_time,
    validate_session_name,
    validate_positive_int,
    validate_entity_exists,
    validate_unique_field,
)
from app.utils.errors import ConflictError


def validate_exam_create_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload for exam timetable creation.
    Required: subject_id, exam_code, title, exam_date, start_time, end_time, session_name
    """
    validate_required_fields(data, [
        "subject_id", "exam_code", "title",
        "exam_date", "start_time", "end_time", "session_name"
    ])

    subj_id = validate_positive_int(data["subject_id"], "subject_id")
    validate_entity_exists(Subject, subj_id, "Subject")

    code = str(data["exam_code"]).strip().upper()
    validate_unique_field(Exam, "exam_code", code)

    ex_date = validate_date(data["exam_date"], "exam_date")
    start = validate_time(data["start_time"], "start_time")
    end = validate_time(data["end_time"], "end_time")

    if end <= start:
        from app.utils.errors import ValidationError
        raise ValidationError("Exam end_time must be later than start_time.")

    session = validate_session_name(data["session_name"])

    return {
        "subject_id": subj_id,
        "exam_code": code,
        "title": str(data["title"]).strip(),
        "exam_date": ex_date,
        "start_time": start,
        "end_time": end,
        "session_name": session,
        "status": str(data.get("status", "SCHEDULED")).strip().upper(),
    }


def validate_exam_update_payload(exam_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates payload for updating an existing exam record."""
    if not isinstance(data, dict):
        from app.utils.errors import ValidationError
        raise ValidationError("Request body must be a valid JSON object.")

    cleaned = {}

    if "title" in data and str(data["title"]).strip():
        cleaned["title"] = str(data["title"]).strip()

    if "exam_date" in data:
        cleaned["exam_date"] = validate_date(data["exam_date"], "exam_date")

    if "start_time" in data:
        cleaned["start_time"] = validate_time(data["start_time"], "start_time")

    if "end_time" in data:
        cleaned["end_time"] = validate_time(data["end_time"], "end_time")

    if "session_name" in data:
        cleaned["session_name"] = validate_session_name(data["session_name"])

    if "status" in data:
        cleaned["status"] = str(data["status"]).strip().upper()

    if "exam_code" in data:
        code = str(data["exam_code"]).strip().upper()
        validate_unique_field(Exam, "exam_code", code, exclude_id=exam_id)
        cleaned["exam_code"] = code

    return cleaned


def validate_registration_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates student enrollment/registration into an examination.
    Ensures student and exam exist, and checks for duplicate registrations.
    """
    validate_required_fields(data, ["student_id", "exam_id"])

    s_id = validate_positive_int(data["student_id"], "student_id")
    e_id = validate_positive_int(data["exam_id"], "exam_id")

    validate_entity_exists(Student, s_id, "Student")
    validate_entity_exists(Exam, e_id, "Exam")

    # Check for duplicate registration
    existing = Registration.query.filter_by(student_id=s_id, exam_id=e_id).first()
    if existing:
        raise ConflictError("Student is already registered for this examination.")

    return {
        "student_id": s_id,
        "exam_id": e_id,
        "is_eligible": bool(data.get("is_eligible", True)),
    }


def serialize_exam(exam: Exam) -> Dict[str, Any]:
    """Serializes exam model into standardized JSON dictionary."""
    return exam.to_dict() if exam else {}
