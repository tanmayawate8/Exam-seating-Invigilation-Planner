"""
Seat Allocation Model Module.
Represents individual student-to-seat mappings within a specific seating plan.
"""

from datetime import datetime
from app.extensions import db


class SeatAllocation(db.Model):
    """Specific Student Seat Allocation entity."""

    __tablename__ = "seat_allocations"
    __table_args__ = (
        db.UniqueConstraint("seating_plan_id", "seat_id", name="uq_plan_seat_allocation"),
        db.UniqueConstraint("seating_plan_id", "student_id", name="uq_plan_student_allocation"),
    )

    id = db.Column(db.Integer, primary_key=True)
    seating_plan_id = db.Column(db.Integer, db.ForeignKey("seating_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False, index=True)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    seating_plan = db.relationship("SeatingPlan", back_populates="allocations")
    student = db.relationship("Student", back_populates="seat_allocations")
    room = db.relationship("Room", back_populates="seat_allocations")
    seat = db.relationship("Seat", back_populates="allocations")

    def __repr__(self) -> str:
        return f"<SeatAllocation Plan:{self.seating_plan_id} Student:{self.student_id} Seat:{self.seat_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seating_plan_id": self.seating_plan_id,
            "student_id": self.student_id,
            "student_roll": self.student.roll_number if self.student else None,
            "student_name": self.student.full_name if self.student else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "building": self.room.building if self.room else None,
            "seat_id": self.seat_id,
            "seat_number": self.seat.seat_number if self.seat else None,
            "row_num": self.seat.row_num if self.seat else None,
            "col_num": self.seat.col_num if self.seat else None,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
        }
