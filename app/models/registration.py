"""
Registration Model Module.
Represents student registration and eligibility for scheduled examinations.
"""

from datetime import datetime
from app.extensions import db


class Registration(db.Model):
    """Student Exam Registration entity."""

    __tablename__ = "registrations"
    __table_args__ = (
        db.UniqueConstraint("student_id", "exam_id", name="uq_student_exam_registration"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_eligible = db.Column(db.Boolean, default=True, nullable=False)
    attendance_status = db.Column(db.String(20), default="PENDING", nullable=False)  # PENDING, PRESENT, ABSENT

    # Relationships
    student = db.relationship("Student", back_populates="registrations")
    exam = db.relationship("Exam", back_populates="registrations")

    def __repr__(self) -> str:
        return f"<Registration Student:{self.student_id} Exam:{self.exam_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_roll": self.student.roll_number if self.student else None,
            "student_name": self.student.full_name if self.student else None,
            "exam_id": self.exam_id,
            "exam_code": self.exam.exam_code if self.exam else None,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "is_eligible": self.is_eligible,
            "attendance_status": self.attendance_status,
        }
