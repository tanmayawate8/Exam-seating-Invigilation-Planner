"""
User Model Module.
Base identity and authentication entity with Role-Based Access Control (RBAC).
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """User account entity for Admin, Teacher, and Student roles."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="STUDENT", index=True)  # ADMIN, TEACHER, STUDENT
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # One-to-One Relationships with Profiles
    student_profile = db.relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    teacher_profile = db.relationship(
        "Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-Many Relationships
    notifications = db.relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    audit_logs = db.relationship(
        "AuditLog", back_populates="user", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        """Hashes and sets the user password using Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies given password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role.upper() == "ADMIN"

    def is_teacher(self) -> bool:
        return self.role.upper() == "TEACHER"

    def is_student(self) -> bool:
        return self.role.upper() == "STUDENT"

    def __repr__(self) -> str:
        return f"<User {self.username} [{self.role}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login user loader callback."""
    try:
        user = db.session.get(User, int(user_id))
        if user is not None:
            _ = user.is_active
            return user
        return None
    except Exception:
        return None
