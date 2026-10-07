"""
Seat Model Module.
Represents individual physical seats located within an examination room.
"""

from app.extensions import db


class Seat(db.Model):
    """Individual Seat entity within a Room."""

    __tablename__ = "seats"
    __table_args__ = (
        db.UniqueConstraint("room_id", "seat_number", name="uq_room_seat_number"),
        db.UniqueConstraint("room_id", "row_num", "col_num", name="uq_room_row_col"),
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_number = db.Column(db.String(30), nullable=False)  # e.g., "R1-C1", "A-01"
    row_num = db.Column(db.Integer, nullable=False)
    col_num = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    room = db.relationship("Room", back_populates="seats")
    allocations = db.relationship("SeatAllocation", back_populates="seat", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Seat {self.seat_number} in Room {self.room_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "seat_number": self.seat_number,
            "row_num": self.row_num,
            "col_num": self.col_num,
            "is_active": self.is_active,
        }
