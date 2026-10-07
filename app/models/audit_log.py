"""
Audit Log Model Module.
Represents immutable system audit trails for administrative, security, and planning events.
"""

from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    """Immutable System Audit Log entity."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # LOGIN, CREATE_STUDENT, GENERATE_SEATING, etc.
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # User, Student, Exam, SeatingPlan, etc.
    entity_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON or descriptive text
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id} at {self.timestamp}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "SYSTEM",
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
