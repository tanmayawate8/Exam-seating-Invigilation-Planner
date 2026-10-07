"""
Teacher Management Routes Module (Admin & Faculty).
Exposes RESTful endpoints for faculty profiles, availability declarations,
peer duty swap workflows, and administrative reviews.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.teacher_service import TeacherService
from app.schemas.teacher import (
    validate_teacher_create_payload,
    validate_teacher_update_payload,
    validate_availability_payload,
)
from app.utils.decorators import admin_required, role_required
from app.utils.errors import ForbiddenError, BadRequestError
from app.utils.responses import success_response

teachers_bp = Blueprint("teachers", __name__)


@teachers_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for teacher routes."""
    return success_response(data={"blueprint": "teachers", "status": "active"}, message="Teachers blueprint is active.")


@teachers_bp.route("", methods=["GET"])
@login_required
def get_teachers():
    """
    GET /api/teachers
    Retrieves paginated faculty directory with department, designation, and search filters.
    Query params: ?page=1&per_page=20&department_id=1&designation=Lecturer&is_active=true&search=smith
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    dept_id = request.args.get("department_id", type=int)
    designation = request.args.get("designation", type=str)
    search = request.args.get("search", type=str)

    is_active_param = request.args.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() in ("true", "1", "yes")

    result = TeacherService.get_teachers(
        page=page,
        per_page=per_page,
        department_id=dept_id,
        designation=designation,
        is_active=is_active,
        search=search,
    )

    return success_response(
        data=result["teachers"],
        meta={"pagination": result["pagination"]},
        message="Teachers retrieved successfully."
    )


@teachers_bp.route("/<int:teacher_id>", methods=["GET"])
@login_required
def get_teacher_by_id(teacher_id: int):
    """
    GET /api/teachers/<id>
    Fetches a single teacher record.
    """
    teacher = TeacherService.get_teacher_by_id(teacher_id)
    return success_response(
        data=teacher.to_dict(),
        message="Teacher retrieved successfully."
    )


@teachers_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_teacher():
    """
    POST /api/teachers
    Enrolls a new faculty member and provisions their linked user account.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_teacher_create_payload(data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    teacher = TeacherService.create_teacher(
        validated_data=validated_data,
        creator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=teacher.to_dict(),
        message=f"Faculty member '{teacher.full_name}' ({teacher.employee_id}) created successfully.",
        status_code=201,
    )


@teachers_bp.route("/<int:teacher_id>", methods=["PUT"])
@login_required
@admin_required
def update_teacher(teacher_id: int):
    """
    PUT /api/teachers/<id>
    Updates attributes of an existing faculty member.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_teacher_update_payload(teacher_id, data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    teacher = TeacherService.update_teacher(
        teacher_id=teacher_id,
        validated_data=validated_data,
        modifier_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=teacher.to_dict(),
        message=f"Faculty member {teacher.employee_id} updated successfully."
    )


@teachers_bp.route("/<int:teacher_id>/status", methods=["PATCH"])
@login_required
@admin_required
def toggle_teacher_status(teacher_id: int):
    """
    PATCH /api/teachers/<id>/status
    Enables or disables a teacher's active status.
    Payload: {"is_active": bool}
    """
    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise BadRequestError("Field 'is_active' (boolean) is required.")

    is_active = bool(data["is_active"])
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    teacher = TeacherService.toggle_teacher_status(
        teacher_id=teacher_id,
        is_active=is_active,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    status_str = "activated" if is_active else "deactivated"
    return success_response(
        data=teacher.to_dict(),
        message=f"Teacher {teacher.employee_id} has been {status_str}."
    )


@teachers_bp.route("/<int:teacher_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_teacher(teacher_id: int):
    """
    DELETE /api/teachers/<id>
    Removes faculty record and linked user credentials.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    TeacherService.delete_teacher(
        teacher_id=teacher_id,
        deleter_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Teacher deleted successfully."
    )


@teachers_bp.route("/<int:teacher_id>/availability", methods=["POST"])
@login_required
def set_availability(teacher_id: int):
    """
    POST /api/teachers/<id>/availability
    Records teacher availability or leave window.
    Allowed for Admins or the Teacher themselves.
    Payload: {"date": "YYYY-MM-DD", "time_slot": "MORNING|AFTERNOON|ALL_DAY", "is_available": bool, "reason": "..."}
    """
    if current_user.role == "TEACHER":
        if not current_user.teacher_profile or current_user.teacher_profile.id != teacher_id:
            raise ForbiddenError("You can only submit your own availability.")

    data = request.get_json(silent=True) or {}
    validated_data = validate_availability_payload(data)

    avail = TeacherService.set_teacher_availability(
        teacher_id=teacher_id,
        date_val=validated_data["date"],
        time_slot=validated_data["time_slot"],
        is_available=validated_data["is_available"],
        reason=validated_data.get("reason"),
    )

    return success_response(
        data=avail.to_dict(),
        message="Teacher availability recorded successfully.",
        status_code=201,
    )


@teachers_bp.route("/<int:teacher_id>/duties", methods=["GET"])
@login_required
def get_teacher_duties(teacher_id: int):
    """
    GET /api/teachers/<id>/duties
    Retrieves invigilation duties assigned to a faculty member.
    Allowed for Admins or the Teacher themselves.
    """
    if current_user.role == "TEACHER":
        if not current_user.teacher_profile or current_user.teacher_profile.id != teacher_id:
            raise ForbiddenError("You can only view your own assigned duties.")

    status = request.args.get("status")
    duties = TeacherService.get_teacher_duties(teacher_id=teacher_id, status=status)

    return success_response(
        data=duties,
        message="Invigilation duties retrieved successfully."
    )


@teachers_bp.route("/duty-swap", methods=["POST"])
@login_required
@role_required("TEACHER")
def request_duty_swap():
    """
    POST /api/teachers/duty-swap
    Initiates a peer-to-peer duty swap request.
    Payload: {"duty_id": 1, "target_teacher_id": 2, "reason": "Medical emergency"}
    """
    if not current_user.teacher_profile:
        raise ForbiddenError("Only registered faculty members can initiate duty swaps.")

    data = request.get_json(silent=True) or {}
    if not data.get("duty_id") or not data.get("target_teacher_id"):
        raise BadRequestError("Fields 'duty_id' and 'target_teacher_id' are required.")

    duty_id = int(data["duty_id"])
    target_id = int(data["target_teacher_id"])
    reason = str(data.get("reason") or "Personal emergency").strip()

    swap = TeacherService.request_duty_swap(
        duty_id=duty_id,
        requester_teacher_id=current_user.teacher_profile.id,
        target_teacher_id=target_id,
        reason=reason,
    )

    return success_response(
        data=swap.to_dict(),
        message="Duty swap requested successfully. Awaiting peer and admin approval.",
        status_code=201,
    )


@teachers_bp.route("/duty-swap/<int:swap_id>/review", methods=["PATCH"])
@login_required
@admin_required
def review_duty_swap(swap_id: int):
    """
    PATCH /api/teachers/duty-swap/<id>/review
    Admin endpoint to approve or reject a duty swap request.
    Payload: {"approve": true|false, "admin_comment": "..."}
    """
    data = request.get_json(silent=True) or {}
    if "approve" not in data:
        raise BadRequestError("Field 'approve' (boolean) is required.")

    approve = bool(data["approve"])
    admin_comment = str(data.get("admin_comment") or "").strip() or None

    swap = TeacherService.admin_review_duty_swap(
        swap_id=swap_id,
        admin_user_id=current_user.id,
        approve=approve,
        admin_comment=admin_comment,
    )

    action_word = "approved" if approve else "rejected"
    return success_response(
        data=swap.to_dict(),
        message=f"Duty swap {swap.id} has been {action_word}."
    )
