"""
Notification Schema Validation Module.
Validates input payloads for announcements and broadcast notifications.
"""

from typing import Any, Dict
from app.utils.errors import ValidationError

VALID_NOTIFICATION_TYPES = {
    "GENERAL",
    "BROADCAST",
    "DUTY_ASSIGNED",
    "DUTY_SWAP",
    "SEATING_PUBLISHED",
    "EXAM_UPDATE",
}

VALID_TARGET_ROLES = {"ALL", "STUDENT", "TEACHER", "ADMIN"}


def validate_broadcast_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates admin notification broadcast payload.
    Expected fields:
    - title: str (3 to 150 chars)
    - message: str (3 to 2000 chars)
    - target_role: str (ALL, STUDENT, TEACHER, ADMIN)
    - notification_type: optional str (default BROADCAST)
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a valid JSON object.")

    title = data.get("title")
    if not title or not isinstance(title, str) or not (3 <= len(title.strip()) <= 150):
        raise ValidationError("Field 'title' is required and must be between 3 and 150 characters.")

    message = data.get("message")
    if not message or not isinstance(message, str) or not (3 <= len(message.strip()) <= 2000):
        raise ValidationError("Field 'message' is required and must be between 3 and 2000 characters.")

    target_role = (data.get("target_role") or "ALL").strip().upper()
    if target_role not in VALID_TARGET_ROLES:
        raise ValidationError(
            f"Invalid target_role '{target_role}'. Allowed values: {', '.join(sorted(VALID_TARGET_ROLES))}."
        )

    notification_type = (data.get("notification_type") or "BROADCAST").strip().upper()
    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise ValidationError(
            f"Invalid notification_type '{notification_type}'. Allowed values: {', '.join(sorted(VALID_NOTIFICATION_TYPES))}."
        )

    return {
        "title": title.strip(),
        "message": message.strip(),
        "target_role": target_role,
        "notification_type": notification_type,
    }
