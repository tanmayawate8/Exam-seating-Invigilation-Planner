"""
Student Portal Routes Module (Member 2 Frontend Integration).
Exposes student-facing endpoints for viewing student profile,
examination timetable, hall assignments, and public seat search kiosks.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.models.notification import Notification
from app.services.student_service import StudentService
from app.utils.decorators import student_required
from app.utils.errors import BadRequestError, ForbiddenError
from app.utils.responses import success_response

student_portal_bp = Blueprint("student_portal", __name__)


@student_portal_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for student portal routes."""
    return success_response(data={"blueprint": "student_portal", "status": "active"}, message="Student portal blueprint is active.")


@student_portal_bp.route("/profile", methods=["GET"])
@login_required
@student_required
def get_my_profile():
    """
    GET /api/student/profile
    Retrieves the authenticated student's academic profile.
    """
    profile = current_user.student_profile
    if not profile:
        raise ForbiddenError("No student profile found for this user account.")

    return success_response(
        data=profile.to_dict(),
        message="Student profile retrieved successfully."
    )


@student_portal_bp.route("/timetable", methods=["GET"])
@login_required
@student_required
def get_my_timetable():
    """
    GET /api/student/timetable
    Retrieves the examination timetable for courses where the student is registered.
    """
    profile = current_user.student_profile
    timetable = StudentService.get_student_timetable(profile.id)

    return success_response(
        data=timetable,
        message="Examination timetable retrieved successfully."
    )


@student_portal_bp.route("/my-seat", methods=["GET"])
@student_portal_bp.route("/seating", methods=["GET"])
@login_required
@student_required
def get_my_seating():
    """
    GET /api/student/my-seat (or /api/student/seating)
    Retrieves published hall and seat allocations for the authenticated student.
    """
    profile = current_user.student_profile
    seating_info = StudentService.get_student_seating_info(profile.id)

    return success_response(
        data=seating_info,
        message="Seating allocations retrieved successfully."
    )


@student_portal_bp.route("/seat-search", methods=["GET"])
def search_seat():
    """
    GET /api/student/seat-search
    Public / Kiosk lookup for students to search allocated seats by roll number.
    Query params: ?roll_number=CO01&exam_id=1
    """
    roll_number = request.args.get("roll_number")
    if not roll_number:
        raise BadRequestError("Query parameter 'roll_number' is required.")

    exam_id_param = request.args.get("exam_id")
    exam_id = int(exam_id_param) if exam_id_param else None

    results = StudentService.search_student_seating(
        roll_number=roll_number,
        exam_id=exam_id,
    )

    return success_response(
        data=results,
        message=f"Seating search for student '{roll_number}' completed."
    )


@student_portal_bp.route("/notifications", methods=["GET"])
@login_required
@student_required
def get_my_notifications():
    """
    GET /api/student/notifications
    Retrieves portal notifications (e.g. published seating, hall announcements).
    """
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    return success_response(
        data=[n.to_dict() for n in notifications],
        message="Student notifications retrieved successfully."
    )
