"""
Services package initialization.
Exports all domain services for application routes and background workflows.
"""

from app.services.auth_service import AuthService
from app.services.academic_service import AcademicService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.room_service import RoomService
from app.services.exam_service import ExamService
from app.services.registration_service import RegistrationService
from app.services.planning_service import PlanningService
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService
from app.services.report_service import ReportService

__all__ = [
    "AuthService",
    "AcademicService",
    "StudentService",
    "TeacherService",
    "RoomService",
    "ExamService",
    "RegistrationService",
    "PlanningService",
    "NotificationService",
    "AuditService",
    "ReportService",
]
