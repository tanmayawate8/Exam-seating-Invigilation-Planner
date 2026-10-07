"""
Notification Model Module.
Represents user notifications for exam scheduling, duty allocations, and status updates.
"""

from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    """User Notification entity."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default="GENERAL", nullable=False)  # DUTY_ASSIGNED, DUTY_SWAP, SEATING_PUBLISHED, EXAM_UPDATE
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification User:{self.user_id} - {self.title}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
