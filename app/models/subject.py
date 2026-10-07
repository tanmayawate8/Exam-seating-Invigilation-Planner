"""
Subject Model Module.
Represents academic courses/subjects linked to departments and exam schedules.
"""

from datetime import datetime
from app.extensions import db


class Subject(db.Model):
    """Academic Subject entity."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, default=3, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    department = db.relationship("Department", back_populates="subjects")
    exams = db.relationship("Exam", back_populates="subject", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Subject {self.code} - {self.name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "semester": self.semester,
            "credits": self.credits,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
