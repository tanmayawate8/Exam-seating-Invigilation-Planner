"""
Routes Package Initialization.
Imports all route blueprints and registers them with their respective URL prefixes.
"""

from flask import Flask

from app.routes.auth import auth_bp
from app.routes.students import students_bp
from app.routes.teachers import teachers_bp
from app.routes.departments import departments_bp
from app.routes.subjects import subjects_bp
from app.routes.rooms import rooms_bp
from app.routes.exams import exams_bp
from app.routes.planning import planning_bp
from app.routes.student_portal import student_portal_bp
from app.routes.teacher_portal import teacher_portal_bp
from app.routes.notifications import notifications_bp
from app.routes.audit_logs import audit_logs_bp
from app.routes.reports import reports_bp
from app.routes.root import root_bp


def register_blueprints(app: Flask) -> None:
    """
    Registers all application blueprints onto the Flask app instance
    with standardized /api URL prefixes.
    """
    app.register_blueprint(root_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(students_bp, url_prefix="/api/students")
    app.register_blueprint(teachers_bp, url_prefix="/api/teachers")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(subjects_bp, url_prefix="/api/subjects")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(exams_bp, url_prefix="/api/exams")
    app.register_blueprint(planning_bp, url_prefix="/api/planning")
    app.register_blueprint(student_portal_bp, url_prefix="/api/student")
    app.register_blueprint(teacher_portal_bp, url_prefix="/api/teacher")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(audit_logs_bp, url_prefix="/api/audit-logs")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")


__all__ = [
    "register_blueprints",
    "auth_bp",
    "students_bp",
    "teachers_bp",
    "departments_bp",
    "subjects_bp",
    "rooms_bp",
    "exams_bp",
    "planning_bp",
    "student_portal_bp",
    "teacher_portal_bp",
    "notifications_bp",
    "audit_logs_bp",
    "reports_bp",
    "root_bp",
]
