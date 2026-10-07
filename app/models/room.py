"""
Room Model Module.
Represents physical examination halls, dimensions, capacities, and seat grids.
"""

from datetime import datetime
from app.extensions import db


class Room(db.Model):
    """Examination Room / Hall entity."""

    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    building = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.Integer, default=1, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    rows_count = db.Column(db.Integer, nullable=False)
    columns_count = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    seats = db.relationship("Seat", back_populates="room", cascade="all, delete-orphan", lazy="dynamic")
    invigilation_duties = db.relationship("InvigilationDuty", back_populates="room", lazy="dynamic")
    seat_allocations = db.relationship("SeatAllocation", back_populates="room", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Room {self.room_number} ({self.building}) - Cap: {self.capacity}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "room_number": self.room_number,
            "building": self.building,
            "floor": self.floor,
            "capacity": self.capacity,
            "rows_count": self.rows_count,
            "columns_count": self.columns_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
