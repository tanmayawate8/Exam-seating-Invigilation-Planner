"""
Seating Plan Model Module.
Represents master seating plan generations for examination sessions.
"""

from datetime import datetime
from app.extensions import db


class SeatingPlan(db.Model):
    """Master Seating Plan entity."""

    __tablename__ = "seating_plans"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_code = db.Column(db.String(60), unique=True, nullable=False, index=True)
    version = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="GENERATED", nullable=False, index=True)  # DRAFT, GENERATED, PUBLISHED, ARCHIVED
    total_students_allocated = db.Column(db.Integer, default=0, nullable=False)
    total_rooms_used = db.Column(db.Integer, default=0, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    exam = db.relationship("Exam", back_populates="seating_plans")
    allocations = db.relationship("SeatAllocation", back_populates="seating_plan", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<SeatingPlan {self.plan_code} - Version {self.version} [{self.status}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "exam_code": self.exam.exam_code if self.exam else None,
            "plan_code": self.plan_code,
            "version": self.version,
            "status": self.status,
            "total_students_allocated": self.total_students_allocated,
            "total_rooms_used": self.total_rooms_used,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
