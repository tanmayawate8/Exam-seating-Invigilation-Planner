"""
Authentication Schemas and Validation Module.
Handles validation for authentication payloads and safe serialization of user identities.
"""

from typing import Tuple, Dict, Any
from app.models.user import User


def validate_login_input(data: Any) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Validates credentials payload for POST /api/auth/login.
    Accepts 'username', 'email', 'name', or 'enrollment_no', plus 'password'.
    """
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    username_or_email = (
        data.get("username")
        or data.get("email")
        or data.get("name")
        or data.get("enrollment_no")
        or data.get("enrollment_number")
        or data.get("identifier")
        or ""
    ).strip()
    password = (
        data.get("password")
        or data.get("enrollment_no")
        or data.get("enrollment_number")
        or data.get("zprn")
        or ""
    )
    remember = bool(data.get("remember", False))

    if not username_or_email:
        return False, "Username, email, student name, or enrollment number is required."

    if not password:
        return False, "Password or enrollment number is required."

    return True, {
        "identifier": username_or_email,
        "password": password,
        "remember": remember,
    }


def validate_password_change_input(data: Any) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Validates payload for POST /api/auth/change-password.
    """
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not current_password:
        return False, "Current password is required."

    if not new_password:
        return False, "New password is required."

    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    if confirm_password and new_password != confirm_password:
        return False, "New password and confirmation do not match."

    return True, {
        "current_password": current_password,
        "new_password": new_password,
    }


def serialize_user(user: User, include_profile: bool = True) -> Dict[str, Any]:
    """
    Serializes a User model into a sanitized dictionary suitable for API responses.
    Guarantees that password hashes are NEVER exposed.
    """
    if not user:
        return {}

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    if include_profile:
        if user.is_student() and user.student_profile:
            user_data["student_profile"] = {
                "id": user.student_profile.id,
                "roll_number": user.student_profile.roll_number,
                "enrollment_number": user.student_profile.enrollment_number,
                "full_name": user.student_profile.full_name,
                "department_id": user.student_profile.department_id,
                "department_name": (
                    user.student_profile.department.name
                    if user.student_profile.department
                    else None
                ),
                "semester": user.student_profile.semester,
                "academic_year": user.student_profile.academic_year,
            }
        elif user.is_teacher() and user.teacher_profile:
            user_data["teacher_profile"] = {
                "id": user.teacher_profile.id,
                "employee_id": user.teacher_profile.employee_id,
                "full_name": user.teacher_profile.full_name,
                "designation": user.teacher_profile.designation,
                "department_id": user.teacher_profile.department_id,
                "department_name": (
                    user.teacher_profile.department.name
                    if user.teacher_profile.department
                    else None
                ),
                "phone_number": user.teacher_profile.phone_number,
                "max_duties_per_week": user.teacher_profile.max_duties_per_week,
            }

    return user_data
