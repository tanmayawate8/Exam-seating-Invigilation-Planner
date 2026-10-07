"""
Room and Seat Schemas and Validation Module.
Handles validation for exam room layout, row/column dimensions, and capacity calculations.
"""

from typing import Any, Dict
from app.models.room import Room
from app.utils.validators import (
    validate_required_fields,
    validate_positive_int,
    validate_unique_field,
)


def validate_room_create_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates payload for examination room creation.
    Required: room_number, building, floor, rows_count, columns_count
    Calculated: capacity = rows_count * columns_count
    """
    validate_required_fields(data, [
        "room_number", "building", "rows_count", "columns_count"
    ])

    room_num = str(data["room_number"]).strip().upper()
    validate_unique_field(Room, "room_number", room_num)

    rows = validate_positive_int(data["rows_count"], "rows_count", min_val=1, max_val=50)
    cols = validate_positive_int(data["columns_count"], "columns_count", min_val=1, max_val=50)
    floor = validate_positive_int(data.get("floor", 1), "floor", min_val=-2, max_val=20)

    # Calculate or override capacity
    default_capacity = rows * cols
    capacity = validate_positive_int(data.get("capacity", default_capacity), "capacity", min_val=1, max_val=default_capacity)

    return {
        "room_number": room_num,
        "building": str(data["building"]).strip(),
        "floor": floor,
        "rows_count": rows,
        "columns_count": cols,
        "capacity": capacity,
        "is_active": bool(data.get("is_active", True)),
    }


def validate_room_update_payload(room_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates payload for updating an existing room record."""
    if not isinstance(data, dict):
        from app.utils.errors import ValidationError
        raise ValidationError("Request body must be a valid JSON object.")

    cleaned = {}

    if "building" in data and str(data["building"]).strip():
        cleaned["building"] = str(data["building"]).strip()

    if "floor" in data:
        cleaned["floor"] = validate_positive_int(data["floor"], "floor", min_val=-2, max_val=20)

    if "capacity" in data:
        cleaned["capacity"] = validate_positive_int(data["capacity"], "capacity", min_val=1, max_val=2500)

    if "is_active" in data:
        cleaned["is_active"] = bool(data["is_active"])

    if "room_number" in data:
        r_num = str(data["room_number"]).strip().upper()
        validate_unique_field(Room, "room_number", r_num, exclude_id=room_id)
        cleaned["room_number"] = r_num

    return cleaned


def serialize_room(room: Room, include_seats: bool = False) -> Dict[str, Any]:
    """Serializes room model into standardized JSON dictionary."""
    if not room:
        return {}
    res = room.to_dict()
    if include_seats:
        res["seats"] = [seat.to_dict() for seat in room.seats.order_by("row_num", "col_num").all()]
    return res
