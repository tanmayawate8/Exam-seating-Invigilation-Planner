"""
Room and Seat Service Module.
Encapsulates business logic for examination room management,
seat layout generation, physical capacity tracking, and status controls.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.extensions import db
from app.models.room import Room
from app.models.seat import Seat
from app.models.seat_allocation import SeatAllocation
from app.models.invigilation_duty import InvigilationDuty
from app.utils.errors import NotFoundError, ConflictError, ValidationError, BadRequestError
from app.utils.audit import log_audit


class RoomService:
    """Service layer managing examination rooms, halls, and seating grids."""

    @staticmethod
    def get_rooms(
        page: Optional[int] = None,
        per_page: Optional[int] = 20,
        building: Optional[str] = None,
        floor: Optional[int] = None,
        is_active: Optional[bool] = None,
        min_capacity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves examination rooms with optional filtering and pagination.
        If page is None, returns all matching rooms.
        """
        query = Room.query

        if building:
            query = query.filter(Room.building.ilike(f"%{building}%"))

        if floor is not None:
            query = query.filter(Room.floor == floor)

        if is_active is not None:
            query = query.filter(Room.is_active.is_(is_active))

        if min_capacity is not None:
            query = query.filter(Room.capacity >= min_capacity)

        query = query.order_by(Room.building.asc(), Room.floor.asc(), Room.room_number.asc())

        if page is not None:
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "rooms": [room.to_dict() for room in paginated.items],
                "pagination": {
                    "total": paginated.total,
                    "page": paginated.page,
                    "pages": paginated.pages,
                    "per_page": paginated.per_page,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }

        rooms = query.all()
        return {
            "rooms": [room.to_dict() for room in rooms],
            "total": len(rooms),
        }

    @staticmethod
    def get_room_by_id(room_id: int) -> Room:
        """Fetches a single room by its ID or raises NotFoundError."""
        room = Room.query.get(room_id)
        if not room:
            raise NotFoundError(f"Room with ID {room_id} was not found.")
        return room

    @staticmethod
    def get_room_by_number(room_number: str) -> Optional[Room]:
        """Fetches a room by unique room_number."""
        return Room.query.filter_by(room_number=room_number.strip().upper()).first()

    @staticmethod
    def create_room(
        validated_data: Dict[str, Any],
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Room:
        """
        Creates an examination room and automatically generates its physical seat grid.
        
        Grid seats are numbered in standard 'R{row}-C{col}' coordinate format:
        Row 1 to rows_count, Column 1 to columns_count.
        """
        room_num = validated_data["room_number"].strip().upper()
        existing = RoomService.get_room_by_number(room_num)
        if existing:
            raise ConflictError(f"Room '{room_num}' already exists in the system.")

        rows = validated_data["rows_count"]
        cols = validated_data["columns_count"]
        max_possible = rows * cols
        capacity = validated_data.get("capacity", max_possible)

        if capacity > max_possible:
            raise ValidationError(
                f"Room capacity ({capacity}) cannot exceed grid dimension ({rows} x {cols} = {max_possible})."
            )

        try:
            room = Room(
                room_number=room_num,
                building=validated_data["building"].strip(),
                floor=validated_data.get("floor", 1),
                capacity=capacity,
                rows_count=rows,
                columns_count=cols,
                is_active=validated_data.get("is_active", True),
                created_at=datetime.utcnow(),
            )
            db.session.add(room)
            db.session.flush()  # Generate room.id

            # Automatically populate physical Seat records for the room grid
            seat_count = 0
            for r in range(1, rows + 1):
                for c in range(1, cols + 1):
                    if seat_count >= capacity:
                        break
                    seat = Seat(
                        room_id=room.id,
                        seat_number=f"R{r}-C{c}",
                        row_num=r,
                        col_num=c,
                        is_active=True,
                    )
                    db.session.add(seat)
                    seat_count += 1

            db.session.commit()

            log_audit(
                action="ROOM_CREATED",
                entity_type="Room",
                entity_id=str(room.id),
                user_id=creator_user_id,
                details=f"Room {room.room_number} created with {seat_count} generated seats.",
                ip_address=ip_address,
            )

            return room

        except Exception as exc:
            db.session.rollback()
            raise ValidationError(f"Failed to create room and seats: {exc}")

    @staticmethod
    def update_room(
        room_id: int,
        validated_data: Dict[str, Any],
        modifier_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Room:
        """
        Updates examination room attributes.
        If row/column dimensions are changed, ensures no active seat allocations exist
        before regenerating seat grid coordinates.
        """
        room = RoomService.get_room_by_id(room_id)

        # Room number uniqueness check
        if "room_number" in validated_data:
            new_num = validated_data["room_number"].strip().upper()
            if new_num != room.room_number:
                existing = RoomService.get_room_by_number(new_num)
                if existing:
                    raise ConflictError(f"Room number '{new_num}' is already in use.")
                room.room_number = new_num

        if "building" in validated_data:
            room.building = validated_data["building"].strip()

        if "floor" in validated_data:
            room.floor = validated_data["floor"]

        if "is_active" in validated_data:
            room.is_active = bool(validated_data["is_active"])

        # Grid dimension updates
        new_rows = validated_data.get("rows_count", room.rows_count)
        new_cols = validated_data.get("columns_count", room.columns_count)
        new_capacity = validated_data.get("capacity", room.capacity)

        dims_changed = (
            new_rows != room.rows_count or
            new_cols != room.columns_count or
            new_capacity != room.capacity
        )

        if dims_changed:
            # Check for existing seat allocations
            has_allocations = SeatAllocation.query.filter_by(room_id=room.id).first()
            if has_allocations:
                raise ConflictError(
                    "Cannot modify room grid dimensions or capacity because active exam seat allocations "
                    "reference existing seats in this room."
                )

            max_possible = new_rows * new_cols
            if new_capacity > max_possible:
                raise ValidationError(
                    f"Room capacity ({new_capacity}) cannot exceed grid dimension ({new_rows} x {new_cols} = {max_possible})."
                )

            room.rows_count = new_rows
            room.columns_count = new_cols
            room.capacity = new_capacity

            # Delete old seats and recreate
            Seat.query.filter_by(room_id=room.id).delete()
            db.session.flush()

            seat_count = 0
            for r in range(1, new_rows + 1):
                for c in range(1, new_cols + 1):
                    if seat_count >= new_capacity:
                        break
                    seat = Seat(
                        room_id=room.id,
                        seat_number=f"R{r}-C{c}",
                        row_num=r,
                        col_num=c,
                        is_active=True,
                    )
                    db.session.add(seat)
                    seat_count += 1

        db.session.commit()

        log_audit(
            action="ROOM_UPDATED",
            entity_type="Room",
            entity_id=str(room.id),
            user_id=modifier_user_id,
            details=f"Room {room.room_number} attributes updated.",
            ip_address=ip_address,
        )

        return room

    @staticmethod
    def toggle_room_status(
        room_id: int,
        is_active: bool,
        operator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Room:
        """Enables or disables an examination room."""
        room = RoomService.get_room_by_id(room_id)
        room.is_active = is_active
        db.session.commit()

        action = "ROOM_ACTIVATED" if is_active else "ROOM_DEACTIVATED"
        log_audit(
            action=action,
            entity_type="Room",
            entity_id=str(room.id),
            user_id=operator_user_id,
            details=f"Room {room.room_number} status set to {'active' if is_active else 'inactive'}.",
            ip_address=ip_address,
        )

        return room

    @staticmethod
    def delete_room(
        room_id: int,
        deleter_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Deletes a room if no active seat allocations or invigilation duties exist.
        """
        room = RoomService.get_room_by_id(room_id)

        has_allocations = SeatAllocation.query.filter_by(room_id=room.id).first()
        if has_allocations:
            raise ConflictError(
                "Cannot delete room: examination seat allocations reference this room. "
                "Deactivate the room instead."
            )

        has_duties = InvigilationDuty.query.filter_by(room_id=room.id).first()
        if has_duties:
            raise ConflictError(
                "Cannot delete room: invigilation duties are assigned to this room. "
                "Deactivate the room instead."
            )

        room_num = room.room_number
        db.session.delete(room)
        db.session.commit()

        log_audit(
            action="ROOM_DELETED",
            entity_type="Room",
            entity_id=str(room_id),
            user_id=deleter_user_id,
            details=f"Room {room_num} deleted from system.",
            ip_address=ip_address,
        )

        return True

    @staticmethod
    def get_room_seats(room_id: int, is_active_only: bool = True) -> List[Seat]:
        """Returns all physical seats configured for a given room."""
        room = RoomService.get_room_by_id(room_id)
        query = room.seats
        if is_active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Seat.row_num.asc(), Seat.col_num.asc()).all()

    @staticmethod
    def toggle_seat_status(
        seat_id: int,
        is_active: bool,
        operator_user_id: Optional[int] = None,
    ) -> Seat:
        """Marks an individual seat as functional or damaged/unavailable."""
        seat = Seat.query.get(seat_id)
        if not seat:
            raise NotFoundError(f"Seat with ID {seat_id} not found.")

        seat.is_active = is_active
        db.session.commit()

        log_audit(
            action="SEAT_STATUS_UPDATED",
            entity_type="Seat",
            entity_id=str(seat.id),
            user_id=operator_user_id,
            details=f"Seat {seat.seat_number} in Room {seat.room_id} set to {'active' if is_active else 'inactive'}.",
        )

        return seat

    @staticmethod
    def get_available_capacity(room_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Calculates aggregate examination capacity across active rooms and seats.
        """
        query = Room.query.filter_by(is_active=True)
        if room_ids:
            query = query.filter(Room.id.in_(room_ids))

        active_rooms = query.all()
        total_rooms = len(active_rooms)
        nominal_capacity = sum(r.capacity for r in active_rooms)

        # Count active functional seats
        active_room_ids = [r.id for r in active_rooms]
        active_seats_count = Seat.query.filter(
            Seat.room_id.in_(active_room_ids),
            Seat.is_active.is_(True)
        ).count() if active_room_ids else 0

        return {
            "total_rooms": total_rooms,
            "nominal_capacity": nominal_capacity,
            "functional_seats": active_seats_count,
            "rooms": [
                {
                    "id": r.id,
                    "room_number": r.room_number,
                    "building": r.building,
                    "floor": r.floor,
                    "capacity": r.capacity,
                    "rows": r.rows_count,
                    "columns": r.columns_count,
                }
                for r in active_rooms
            ],
        }
