"""
Exam Model Module.
Represents scheduled examinations, dates, sessions, subjects, and lifecycle status.
"""

from datetime import datetime
from app.extensions import db


class Exam(db.Model):
    """Scheduled Examination entity."""

    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    exam_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    exam_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    session_name = db.Column(db.String(20), nullable=False, default="MORNING")  # MORNING, AFTERNOON, EVENING
    status = db.Column(db.String(20), nullable=False, default="DRAFT", index=True)  # DRAFT, SCHEDULED, PLANNED, COMPLETED, CANCELLED
    total_registered = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    subject = db.relationship("Subject", back_populates="exams")
    registrations = db.relationship("Registration", back_populates="exam", cascade="all, delete-orphan", lazy="dynamic")
    seating_plans = db.relationship("SeatingPlan", back_populates="exam", cascade="all, delete-orphan", lazy="dynamic")
    invigilation_duties = db.relationship("InvigilationDuty", back_populates="exam", cascade="all, delete-orphan", lazy="dynamic")
    teacher_availabilities = db.relationship("TeacherAvailability", back_populates="exam", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Exam {self.exam_code} - {self.title} on {self.exam_date}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "subject_code": self.subject.code if self.subject else None,
            "subject_name": self.subject.name if self.subject else None,
            "exam_code": self.exam_code,
            "title": self.title,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "session_name": self.session_name,
            "status": self.status,
            "total_registered": self.total_registered,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
