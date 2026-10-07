"""
Room and Seat Management Routes Module (Admin & Logistics).
Exposes RESTful endpoints for examination rooms, seat grids,
physical capacity calculations, and individual seat condition toggling.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.room_service import RoomService
from app.schemas.room import (
    validate_room_create_payload,
    validate_room_update_payload,
    serialize_room,
)
from app.utils.decorators import admin_required
from app.utils.errors import BadRequestError
from app.utils.responses import success_response

rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for room routes."""
    return success_response(data={"blueprint": "rooms", "status": "active"}, message="Rooms blueprint is active.")


@rooms_bp.route("", methods=["GET"])
@login_required
def get_rooms():
    """
    GET /api/rooms
    Retrieves examination venues with optional filtering and pagination.
    Query params: ?page=1&per_page=20&building=Main&floor=1&is_active=true&min_capacity=30
    """
    page_param = request.args.get("page")
    page = int(page_param) if page_param is not None else None
    per_page = request.args.get("per_page", 20, type=int)
    building = request.args.get("building", type=str)
    floor = request.args.get("floor", type=int)
    min_capacity = request.args.get("min_capacity", type=int)

    is_active_param = request.args.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() in ("true", "1", "yes")

    result = RoomService.get_rooms(
        page=page,
        per_page=per_page,
        building=building,
        floor=floor,
        is_active=is_active,
        min_capacity=min_capacity,
    )

    meta = result.get("pagination") if page is not None else {"total": result.get("total")}
    return success_response(
        data=result["rooms"],
        meta=meta,
        message="Rooms retrieved successfully."
    )


@rooms_bp.route("/capacity-summary", methods=["GET"])
@login_required
def get_capacity_summary():
    """
    GET /api/rooms/capacity-summary
    Calculates total aggregate exam seating capacity across active venues.
    Query params: ?room_ids=1,2,3 (optional comma-separated list)
    """
    room_ids_str = request.args.get("room_ids")
    room_ids = None
    if room_ids_str:
        try:
            room_ids = [int(rid.strip()) for rid in room_ids_str.split(",") if rid.strip()]
        except ValueError:
            raise BadRequestError("Invalid format for 'room_ids'. Expected comma-separated integers.")

    summary = RoomService.get_available_capacity(room_ids=room_ids)
    return success_response(
        data=summary,
        message="Seating capacity summary calculated successfully."
    )


@rooms_bp.route("/<int:room_id>", methods=["GET"])
@login_required
def get_room_by_id(room_id: int):
    """
    GET /api/rooms/<id>
    Fetches a single room record with optional full seat grid list.
    Query params: ?include_seats=true
    """
    include_seats = request.args.get("include_seats", "").lower() in ("true", "1", "yes")
    room = RoomService.get_room_by_id(room_id)
    serialized = serialize_room(room, include_seats=include_seats)

    return success_response(
        data=serialized,
        message="Room retrieved successfully."
    )


@rooms_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_room():
    """
    POST /api/rooms
    Creates an examination venue and automatically generates its physical seat grid.
    Payload: {
        "room_number": "LH-101",
        "building": "Main Block",
        "floor": 1,
        "rows_count": 5,
        "columns_count": 6,
        "capacity": 30
    }
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_room_create_payload(data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    room = RoomService.create_room(
        validated_data=validated_data,
        creator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=room.to_dict(),
        message=f"Room '{room.room_number}' created with {room.capacity} generated seats.",
        status_code=201,
    )


@rooms_bp.route("/<int:room_id>", methods=["PUT"])
@login_required
@admin_required
def update_room(room_id: int):
    """
    PUT /api/rooms/<id>
    Updates examination room dimensions or metadata.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_room_update_payload(room_id, data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    room = RoomService.update_room(
        room_id=room_id,
        validated_data=validated_data,
        modifier_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=room.to_dict(),
        message=f"Room {room.room_number} updated successfully."
    )


@rooms_bp.route("/<int:room_id>/status", methods=["PATCH"])
@login_required
@admin_required
def toggle_room_status(room_id: int):
    """
    PATCH /api/rooms/<id>/status
    Enables or disables an examination room.
    Payload: {"is_active": bool}
    """
    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise BadRequestError("Field 'is_active' (boolean) is required.")

    is_active = bool(data["is_active"])
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    room = RoomService.toggle_room_status(
        room_id=room_id,
        is_active=is_active,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    status_str = "activated" if is_active else "deactivated"
    return success_response(
        data=room.to_dict(),
        message=f"Room {room.room_number} has been {status_str}."
    )


@rooms_bp.route("/<int:room_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_room(room_id: int):
    """
    DELETE /api/rooms/<id>
    Removes an examination venue if no seating plans or invigilation duties reference it.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    RoomService.delete_room(
        room_id=room_id,
        deleter_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Room deleted successfully."
    )


@rooms_bp.route("/<int:room_id>/seats", methods=["GET"])
@login_required
def get_room_seats(room_id: int):
    """
    GET /api/rooms/<id>/seats
    Retrieves all individual physical seats within a room.
    Query params: ?is_active_only=true
    """
    is_active_only = request.args.get("is_active_only", "true").lower() in ("true", "1", "yes")
    seats = RoomService.get_room_seats(room_id=room_id, is_active_only=is_active_only)

    return success_response(
        data=[seat.to_dict() for seat in seats],
        message="Room seats retrieved successfully."
    )


@rooms_bp.route("/seats/<int:seat_id>/status", methods=["PATCH"])
@login_required
@admin_required
def toggle_seat_status(seat_id: int):
    """
    PATCH /api/rooms/seats/<id>/status
    Marks an individual seat as functional or damaged/unavailable.
    Payload: {"is_active": bool}
    """
    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise BadRequestError("Field 'is_active' (boolean) is required.")

    is_active = bool(data["is_active"])
    operator_user_id = current_user.id if current_user.is_authenticated else None

    seat = RoomService.toggle_seat_status(
        seat_id=seat_id,
        is_active=is_active,
        operator_user_id=operator_user_id,
    )

    status_str = "functional" if is_active else "damaged/disabled"
    return success_response(
        data=seat.to_dict(),
        message=f"Seat {seat.seat_number} in Room {seat.room_id} marked as {status_str}."
    )
