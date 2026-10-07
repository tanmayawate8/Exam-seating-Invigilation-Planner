"""
Invigilation Duty Model Module.
Represents assigned teacher invigilation slots per examination and room.
"""

from datetime import datetime
from app.extensions import db


class InvigilationDuty(db.Model):
    """Teacher Invigilation Duty Assignment entity."""

    __tablename__ = "invigilation_duties"
    __table_args__ = (
        db.UniqueConstraint("exam_id", "teacher_id", name="uq_teacher_exam_duty"),
    )

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    duty_role = db.Column(db.String(30), default="CHIEF_INVIGILATOR", nullable=False)  # CHIEF_INVIGILATOR, ASSISTANT, RELIEVER
    status = db.Column(db.String(20), default="ASSIGNED", nullable=False, index=True)  # ASSIGNED, CONFIRMED, SWAPPED, COMPLETED, ABSENT
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    exam = db.relationship("Exam", back_populates="invigilation_duties")
    teacher = db.relationship("Teacher", back_populates="invigilation_duties")
    room = db.relationship("Room", back_populates="invigilation_duties")
    swap_requests = db.relationship("DutySwap", back_populates="duty", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<InvigilationDuty Exam:{self.exam_id} Teacher:{self.teacher_id} Room:{self.room_id} [{self.status}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "exam_code": self.exam.exam_code if self.exam else None,
            "exam_title": self.exam.title if self.exam else None,
            "exam_date": self.exam.exam_date.isoformat() if self.exam and self.exam.exam_date else None,
            "start_time": self.exam.start_time.isoformat() if self.exam and self.exam.start_time else None,
            "end_time": self.exam.end_time.isoformat() if self.exam and self.exam.end_time else None,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.full_name if self.teacher else None,
            "room_id": self.room_id,
            "room_number": self.room.room_number if self.room else None,
            "building": self.room.building if self.room else None,
            "duty_role": self.duty_role,
            "status": self.status,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }
