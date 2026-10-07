"""
Teacher Availability Model Module.
Represents teacher availability, time windows, and leave constraints for invigilation.
"""

from datetime import datetime
from app.extensions import db


class TeacherAvailability(db.Model):
    """Teacher Availability / Leave entity."""

    __tablename__ = "teacher_availabilities"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time_slot = db.Column(db.String(30), nullable=False)  # MORNING, AFTERNOON, ALL_DAY
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    reason = db.Column(db.String(255), nullable=True)  # e.g., "Medical leave", "Academic conference"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    teacher = db.relationship("Teacher", back_populates="availabilities")
    exam = db.relationship("Exam", back_populates="teacher_availabilities")

    def __repr__(self) -> str:
        status = "Available" if self.is_available else "Unavailable"
        return f"<TeacherAvailability Teacher:{self.teacher_id} Date:{self.date} Slot:{self.time_slot} [{status}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.full_name if self.teacher else None,
            "exam_id": self.exam_id,
            "date": self.date.isoformat() if self.date else None,
            "time_slot": self.time_slot,
            "is_available": self.is_available,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
