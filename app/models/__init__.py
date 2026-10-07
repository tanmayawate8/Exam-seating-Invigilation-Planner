"""
Database Models Package Initialization.
Imports and exposes all 16 SQLAlchemy models to ensure discovery by Alembic/Flask-Migrate.
"""

from app.models.department import Department
from app.models.subject import Subject
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.room import Room
from app.models.seat import Seat
from app.models.exam import Exam
from app.models.registration import Registration
from app.models.seating_plan import SeatingPlan
from app.models.seat_allocation import SeatAllocation
from app.models.teacher_availability import TeacherAvailability
from app.models.invigilation_duty import InvigilationDuty
from app.models.duty_swap import DutySwap
from app.models.notification import Notification
from app.models.audit_log import AuditLog

__all__ = [
    "Department",
    "Subject",
    "User",
    "Student",
    "Teacher",
    "Room",
    "Seat",
    "Exam",
    "Registration",
    "SeatingPlan",
    "SeatAllocation",
    "TeacherAvailability",
    "InvigilationDuty",
    "DutySwap",
    "Notification",
    "AuditLog",
]
