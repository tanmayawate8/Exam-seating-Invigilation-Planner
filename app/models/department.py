"""
Department Model Module.
Represents academic departments in the Teachers College.
"""

from datetime import datetime
from app.extensions import db


class Department(db.Model):
    """Academic Department entity."""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    students = db.relationship("Student", back_populates="department", lazy="dynamic")
    teachers = db.relationship("Teacher", back_populates="department", lazy="dynamic")
    subjects = db.relationship("Subject", back_populates="department", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Department {self.code} - {self.name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
