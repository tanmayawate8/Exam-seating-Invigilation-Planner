"""
Teacher Model Module.
Represents faculty members, designations, workload ceilings, and department links.
"""

from datetime import datetime
from app.extensions import db


class Teacher(db.Model):
    """Faculty / Invigilator profile entity."""

    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    designation = db.Column(db.String(100), nullable=False)  # e.g., "Assistant Professor", "Associate Professor"
    phone_number = db.Column(db.String(20), nullable=True)
    max_duties_per_week = db.Column(db.Integer, default=5, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="teacher_profile")
    department = db.relationship("Department", back_populates="teachers")
    availabilities = db.relationship("TeacherAvailability", back_populates="teacher", cascade="all, delete-orphan", lazy="dynamic")
    invigilation_duties = db.relationship("InvigilationDuty", back_populates="teacher", cascade="all, delete-orphan", lazy="dynamic")

    # Duty swap relationships
    swap_requests_sent = db.relationship(
        "DutySwap", foreign_keys="DutySwap.requester_id", back_populates="requester", lazy="dynamic"
    )
    swap_requests_received = db.relationship(
        "DutySwap", foreign_keys="DutySwap.target_teacher_id", back_populates="target_teacher", lazy="dynamic"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Teacher {self.employee_id} - {self.full_name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "designation": self.designation,
            "phone_number": self.phone_number,
            "max_duties_per_week": self.max_duties_per_week,
            "is_active": self.user.is_active if self.user else True,
            "email": self.user.email if self.user else None,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
