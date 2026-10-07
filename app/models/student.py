"""
Student Model Module.
Represents student academic records, roll numbers, and department links.
"""

from datetime import datetime
from app.extensions import db


class Student(db.Model):
    """Student profile entity."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=True, index=True)
    enrollment_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)

    # Official Roll-Call & Import Fields
    sr_no = db.Column(db.Integer, nullable=True)
    zprn = db.Column(db.String(50), unique=True, nullable=True, index=True)
    name = db.Column(db.String(150), nullable=True, index=True)
    student_contact = db.Column(db.String(25), nullable=True)
    parent_contact_1 = db.Column(db.String(25), nullable=True)
    parent_contact_2 = db.Column(db.String(25), nullable=True)
    division = db.Column(db.String(10), nullable=True, default="A")
    batch = db.Column(db.String(20), nullable=True)  # e.g., "C1", "C2"
    class_name = db.Column(db.String(50), nullable=True)  # e.g., "TYCO"

    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)  # e.g., "2026-2027"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="student_profile")
    department = db.relationship("Department", back_populates="students")
    registrations = db.relationship("Registration", back_populates="student", cascade="all, delete-orphan", lazy="dynamic")
    seat_allocations = db.relationship("SeatAllocation", back_populates="student", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def enrollment_no(self) -> str:
        return self.enrollment_number

    @enrollment_no.setter
    def enrollment_no(self, value: str) -> None:
        self.enrollment_number = value

    @property
    def full_name(self) -> str:
        if self.name and self.name.strip():
            return self.name.strip()
        full = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full if full else f"Student #{self.id}"

    def __repr__(self) -> str:
        return f"<Student {self.roll_number or self.enrollment_number} - {self.full_name}>"

    def to_dict(self, include_private_contacts: bool = False) -> dict:
        data = {
            "id": self.id,
            "student_id": self.id,
            "user_id": self.user_id,
            "sr_no": self.sr_no,
            "roll_number": self.roll_number,
            "enrollment_number": self.enrollment_number,
            "enrollment_no": self.enrollment_number,
            "zprn": self.zprn,
            "name": self.name or self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "department_code": self.department.code if self.department else None,
            "semester": self.semester,
            "division": self.division,
            "batch": self.batch,
            "class_name": self.class_name,
            "academic_year": self.academic_year,
            "student_contact": self.student_contact,
            "is_active": self.user.is_active if self.user else True,
            "email": self.user.email if self.user else None,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # Parent contacts are protected by privacy policy (Section 18 & 43)
        if include_private_contacts:
            data["parent_contact_1"] = self.parent_contact_1
            data["parent_contact_2"] = self.parent_contact_2
        return data
