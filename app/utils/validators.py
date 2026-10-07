"""
Centralized Backend Validation Utility Module.
Provides reusable validators for data types, dates, constraints,
entity existence, unique checks, and state transitions.
"""

import re
from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Type
from flask_sqlalchemy.model import Model

from app.utils.errors import (
    ValidationError,
    NotFoundError,
    ConflictError,
    BadRequestError,
)

# Email regex pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Permitted Examination Sessions
ALLOWED_SESSIONS = {"MORNING", "AFTERNOON", "EVENING"}


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validates that all specified keys are present in data and non-empty.
    Raises ValidationError with a list of missing fields.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a valid JSON object.")

    missing = []
    for field in required_fields:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    if missing:
        raise ValidationError(
            f"Missing required field(s): {', '.join(missing)}.",
            errors={"missing_fields": missing},
        )


def validate_email(email_str: str) -> str:
    """Validates and returns normalized lowercase email address."""
    if not email_str or not isinstance(email_str, str):
        raise ValidationError("Email must be a non-empty string.")
    cleaned = email_str.strip().lower()
    if not EMAIL_REGEX.match(cleaned):
        raise ValidationError(f"Invalid email address format: '{email_str}'.")
    return cleaned


def validate_date(date_str: Any, field_name: str = "date") -> date:
    """Parses and validates an ISO formatted date string (YYYY-MM-DD)."""
    if isinstance(date_str, date) and not isinstance(date_str, datetime):
        return date_str
    if not isinstance(date_str, str) or not date_str.strip():
        raise ValidationError(f"'{field_name}' must be an ISO date string (YYYY-MM-DD).")
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(
            f"Invalid date format for '{field_name}'. Expected YYYY-MM-DD, received: '{date_str}'."
        )


def validate_time(time_str: Any, field_name: str = "time") -> time:
    """Parses and validates an ISO formatted time string (HH:MM or HH:MM:SS)."""
    if isinstance(time_str, time):
        return time_str
    if not isinstance(time_str, str) or not time_str.strip():
        raise ValidationError(f"'{field_name}' must be a time string (HH:MM).")

    cleaned = time_str.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            pass

    raise ValidationError(
        f"Invalid time format for '{field_name}'. Expected HH:MM or HH:MM:SS, received: '{time_str}'."
    )


def validate_session_name(session_name: str) -> str:
    """Validates that session is one of MORNING, AFTERNOON, EVENING."""
    if not session_name or not isinstance(session_name, str):
        raise ValidationError("Session name is required.")
    normalized = session_name.strip().upper()
    if normalized not in ALLOWED_SESSIONS:
        raise ValidationError(
            f"Invalid session '{session_name}'. Permitted sessions: {', '.join(sorted(ALLOWED_SESSIONS))}."
        )
    return normalized


def validate_positive_int(
    val: Any,
    field_name: str,
    min_val: int = 1,
    max_val: Optional[int] = None,
) -> int:
    """Validates integer within specified numeric boundaries."""
    try:
        int_val = int(val)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field_name}' must be a valid integer.")

    if int_val < min_val:
        raise ValidationError(f"'{field_name}' must be at least {min_val}.")
    if max_val is not None and int_val > max_val:
        raise ValidationError(f"'{field_name}' cannot exceed {max_val}.")

    return int_val


def validate_entity_exists(model: Type[Model], entity_id: int, entity_name: str) -> Any:
    """
    Queries database for entity by primary key.
    Raises NotFoundError if record does not exist.
    """
    entity = model.query.get(entity_id)
    if not entity:
        raise NotFoundError(f"{entity_name} with ID {entity_id} was not found.")
    return entity


def validate_unique_field(
    model: Type[Model],
    field_name: str,
    value: Any,
    exclude_id: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Checks that value for field_name is not already taken by another record.
    Raises ConflictError on collision.
    """
    column = getattr(model, field_name, None)
    if column is None:
        return

    query = model.query.filter(column == value)
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)

    if query.first():
        msg = error_message or f"{model.__name__} with {field_name} '{value}' already exists."
        raise ConflictError(msg)


def validate_state_transition(
    current_state: str,
    next_state: str,
    allowed_transitions: Dict[str, List[str]],
    entity_name: str = "Resource",
) -> None:
    """
    Validates lifecycle status transitions.
    Raises BadRequestError on invalid transition attempt.
    """
    curr = current_state.upper()
    target = next_state.upper()
    valid_next = [s.upper() for s in allowed_transitions.get(curr, [])]

    if target not in valid_next:
        raise BadRequestError(
            f"Invalid status transition for {entity_name}: cannot change from '{curr}' to '{target}'. "
            f"Allowed next states from '{curr}': {', '.join(valid_next) if valid_next else 'None (Terminal state)'}."
        )
