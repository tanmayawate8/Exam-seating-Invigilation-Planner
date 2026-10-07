"""
Teacher Portal Routes Module (Member 2 Frontend Integration).
Exposes faculty-facing endpoints for viewing duty rosters,
submitting availability, requesting peer duty swaps, and receiving notifications.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.models.notification import Notification
from app.services.teacher_service import TeacherService
from app.schemas.teacher import validate_availability_payload
from app.utils.decorators import teacher_required
from app.utils.errors import BadRequestError, ForbiddenError
from app.utils.responses import success_response

teacher_portal_bp = Blueprint("teacher_portal", __name__)


@teacher_portal_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for teacher portal routes."""
    return success_response(data={"blueprint": "teacher_portal", "status": "active"}, message="Teacher portal blueprint is active.")


@teacher_portal_bp.route("/profile", methods=["GET"])
@login_required
@teacher_required
def get_my_profile():
    """
    GET /api/teacher/profile
    Retrieves the authenticated teacher's faculty profile.
    """
    profile = current_user.teacher_profile
    if not profile:
        raise ForbiddenError("No faculty profile found for this user account.")

    return success_response(
        data=profile.to_dict(),
        message="Faculty profile retrieved successfully."
    )


@teacher_portal_bp.route("/duties", methods=["GET"])
@login_required
@teacher_required
def get_my_duties():
    """
    GET /api/teacher/duties
    Retrieves invigilation duties assigned to the authenticated teacher.
    Query params: ?status=ASSIGNED|CONFIRMED|COMPLETED
    """
    profile = current_user.teacher_profile
    status = request.args.get("status")
    duties = TeacherService.get_teacher_duties(profile.id, status=status)

    return success_response(
        data=duties,
        message="Assigned invigilation duties retrieved successfully."
    )


@teacher_portal_bp.route("/availability", methods=["POST"])
@login_required
@teacher_required
def submit_my_availability():
    """
    POST /api/teacher/availability
    Submits an unavailability / leave entry for an examination session.
    Payload: {"date": "YYYY-MM-DD", "time_slot": "MORNING|AFTERNOON|ALL_DAY", "is_available": false, "reason": "..."}
    """
    profile = current_user.teacher_profile
    data = request.get_json(silent=True) or {}
    validated_data = validate_availability_payload(data)

    avail = TeacherService.set_teacher_availability(
        teacher_id=profile.id,
        date_val=validated_data["date"],
        time_slot=validated_data["time_slot"],
        is_available=validated_data["is_available"],
        reason=validated_data.get("reason"),
    )

    return success_response(
        data=avail.to_dict(),
        message="Faculty availability recorded successfully.",
        status_code=201,
    )


@teacher_portal_bp.route("/duty-swap", methods=["POST"])
@login_required
@teacher_required
def request_peer_swap():
    """
    POST /api/teacher/duty-swap
    Initiates a peer duty swap request for one of the faculty member's duties.
    Payload: {"duty_id": 1, "target_teacher_id": 2, "reason": "Personal medical emergency"}
    """
    profile = current_user.teacher_profile
    data = request.get_json(silent=True) or {}

    if not data.get("duty_id") or not data.get("target_teacher_id"):
        raise BadRequestError("Fields 'duty_id' and 'target_teacher_id' are required.")

    duty_id = int(data["duty_id"])
    target_id = int(data["target_teacher_id"])
    reason = str(data.get("reason") or "Personal emergency").strip()

    swap = TeacherService.request_duty_swap(
        duty_id=duty_id,
        requester_teacher_id=profile.id,
        target_teacher_id=target_id,
        reason=reason,
    )

    return success_response(
        data=swap.to_dict(),
        message="Duty swap request submitted successfully. Awaiting peer and admin review.",
        status_code=201,
    )


@teacher_portal_bp.route("/duty-swaps", methods=["GET"])
@login_required
@teacher_required
def get_my_swap_requests():
    """
    GET /api/teacher/duty-swaps
    Retrieves all incoming and outgoing duty swap requests for this teacher.
    """
    profile = current_user.teacher_profile
    swaps = TeacherService.get_teacher_swap_requests(profile.id)

    return success_response(
        data=swaps,
        message="Duty swap requests retrieved successfully."
    )


@teacher_portal_bp.route("/colleagues", methods=["GET"])
@login_required
@teacher_required
def get_colleagues():
    """
    GET /api/teacher/colleagues
    Retrieves list of active faculty members available for duty swaps in Member 2's UI dropdown.
    """
    profile = current_user.teacher_profile
    result = TeacherService.get_teachers(page=1, per_page=100, is_active=True)

    # Exclude self
    colleagues = [t for t in result["teachers"] if t["id"] != profile.id]

    return success_response(
        data=colleagues,
        message="Faculty colleagues retrieved successfully."
    )


@teacher_portal_bp.route("/notifications", methods=["GET"])
@login_required
@teacher_required
def get_my_notifications():
    """
    GET /api/teacher/notifications
    Retrieves portal notifications (e.g. duty assignments, swap updates).
    """
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    return success_response(
        data=[n.to_dict() for n in notifications],
        message="Teacher notifications retrieved successfully."
    )
