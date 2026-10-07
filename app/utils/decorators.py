"""
Role-Based Access Control (RBAC) Decorators Module.
Enforces server-side authorization policies for Admin, Teacher, and Student roles.
"""

from functools import wraps
from typing import Sequence
from flask import request, jsonify
from flask_login import current_user

from app.utils.audit import log_audit


def role_required(*allowed_roles: str):
    """
    Decorator to restrict route access to users with specified role(s).
    Returns 401 if unauthenticated, 403 if unauthorized.
    Automatically logs forbidden access attempts for security auditing.

    :param allowed_roles: Roles permitted to access the route (e.g., 'ADMIN', 'TEACHER')
    """
    normalized_allowed = [r.upper() for r in allowed_roles]

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 1. Verify Authentication
            if not current_user.is_authenticated:
                return jsonify({
                    "success": False,
                    "message": "Authentication required. Please log in to access this resource."
                }), 401

            # 2. Verify Active Account Status
            if not getattr(current_user, "is_active", True):
                return jsonify({
                    "success": False,
                    "message": "Account has been deactivated. Please contact the administrator."
                }), 403

            # 3. Verify Role Authorization
            user_role = (current_user.role or "").upper()
            if user_role not in normalized_allowed:
                # Log unauthorized access attempt for audit trail
                log_audit(
                    action="FORBIDDEN_ACCESS_ATTEMPT",
                    entity_type="Endpoint",
                    entity_id=request.endpoint,
                    user_id=current_user.id,
                    details=(
                        f"User '{current_user.username}' with role '{user_role}' attempted to "
                        f"access endpoint requiring: {', '.join(normalized_allowed)}."
                    ),
                    ip_address=request.remote_addr,
                )

                return jsonify({
                    "success": False,
                    "message": (
                        f"Access forbidden. Your role '{user_role}' is not authorized "
                        f"for this action. Required role(s): {', '.join(normalized_allowed)}."
                    )
                }), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(fn):
    """Decorator restricting route access strictly to ADMIN users."""
    return role_required("ADMIN")(fn)


def teacher_required(fn):
    """Decorator restricting route access strictly to TEACHER users."""
    return role_required("TEACHER")(fn)


def student_required(fn):
    """Decorator restricting route access strictly to STUDENT users."""
    return role_required("STUDENT")(fn)


def admin_or_teacher_required(fn):
    """Decorator permitting either ADMIN or TEACHER users."""
    return role_required("ADMIN", "TEACHER")(fn)


def admin_or_student_required(fn):
    """Decorator permitting either ADMIN or STUDENT users."""
    return role_required("ADMIN", "STUDENT")(fn)


def verify_teacher_ownership(teacher_id: int) -> bool:
    """
    Validates whether the current user is either an Admin
    or the specific Teacher whose profile/resource is being accessed.

    :param teacher_id: The primary key of the Teacher record
    :return: True if authorized, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin():
        return True
    if current_user.is_teacher() and current_user.teacher_profile:
        return current_user.teacher_profile.id == teacher_id
    return False


def verify_student_ownership(student_id: int) -> bool:
    """
    Validates whether the current user is either an Admin
    or the specific Student whose profile/resource is being accessed.

    :param student_id: The primary key of the Student record
    :return: True if authorized, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin():
        return True
    if current_user.is_student() and current_user.student_profile:
        return current_user.student_profile.id == student_id
    return False
