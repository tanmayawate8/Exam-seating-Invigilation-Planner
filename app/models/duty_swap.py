"""
Duty Swap Model Module.
Represents peer-to-peer invigilation duty swap requests and administrative approval workflow.
"""

from datetime import datetime
from app.extensions import db


class DutySwap(db.Model):
    """Duty Swap Request entity."""

    __tablename__ = "duty_swaps"

    id = db.Column(db.Integer, primary_key=True)
    duty_id = db.Column(db.Integer, db.ForeignKey("invigilation_duties.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    target_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False, index=True)  # PENDING, ACCEPTED_BY_TEACHER, APPROVED_BY_ADMIN, REJECTED, CANCELLED
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    admin_comment = db.Column(db.String(255), nullable=True)

    # Relationships
    duty = db.relationship("InvigilationDuty", back_populates="swap_requests")
    requester = db.relationship("Teacher", foreign_keys=[requester_id], back_populates="swap_requests_sent")
    target_teacher = db.relationship("Teacher", foreign_keys=[target_teacher_id], back_populates="swap_requests_received")

    def __repr__(self) -> str:
        return f"<DutySwap Duty:{self.duty_id} Requester:{self.requester_id} -> Target:{self.target_teacher_id} [{self.status}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "duty_id": self.duty_id,
            "requester_id": self.requester_id,
            "requester_name": self.requester.full_name if self.requester else None,
            "target_teacher_id": self.target_teacher_id,
            "target_teacher_name": self.target_teacher.full_name if self.target_teacher else None,
            "reason": self.reason,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "admin_comment": self.admin_comment,
        }
