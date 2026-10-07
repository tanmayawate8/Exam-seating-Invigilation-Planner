"""
Exam Management & Registration Routes Module (Admin & Academic).
Exposes RESTful endpoints for examination timetabling, schedule conflict checks,
lifecycle state transitions, individual student registrations, and bulk cohort enrollment.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.exam_service import ExamService
from app.services.registration_service import RegistrationService
from app.schemas.exam import (
    validate_exam_create_payload,
    validate_exam_update_payload,
    serialize_exam,
)
from app.utils.decorators import admin_required
from app.utils.errors import BadRequestError
from app.utils.responses import success_response
from app.utils.validators import validate_date

exams_bp = Blueprint("exams", __name__)


@exams_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for exam routes."""
    return success_response(data={"blueprint": "exams", "status": "active"}, message="Exams blueprint is active.")


# =============================================================================
# 1. EXAM TIMETABLE ENDPOINTS
# =============================================================================

@exams_bp.route("", methods=["GET"])
@login_required
def get_exams():
    """
    GET /api/exams
    Retrieves examination schedules with optional filters.
    Query params: ?page=1&per_page=20&status=SCHEDULED&date=2026-11-15&subject_id=1&department_id=1&semester=3
    """
    page_param = request.args.get("page")
    page = int(page_param) if page_param is not None else 1
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    subject_id = request.args.get("subject_id", type=int)
    department_id = request.args.get("department_id", type=int)
    semester = request.args.get("semester", type=int)

    date_str = request.args.get("date") or request.args.get("exam_date")
    date_val = validate_date(date_str, "date") if date_str else None

    result = ExamService.get_exams(
        page=page,
        per_page=per_page,
        status=status,
        date_val=date_val,
        subject_id=subject_id,
        department_id=department_id,
        semester=semester,
    )

    meta = result.get("pagination") if page is not None else {"total": result.get("total")}
    return success_response(
        data=result["exams"],
        meta=meta,
        message="Examination timetable retrieved successfully."
    )


@exams_bp.route("/<int:exam_id>", methods=["GET"])
@login_required
def get_exam_by_id(exam_id: int):
    """
    GET /api/exams/<id>
    Fetches a single scheduled examination by ID.
    """
    exam = ExamService.get_exam_by_id(exam_id)
    return success_response(
        data=serialize_exam(exam),
        message="Exam retrieved successfully."
    )


@exams_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_exam():
    """
    POST /api/exams
    Schedules an examination session with subject and cohort conflict checks.
    Payload: {
        "subject_id": 1,
        "exam_code": "EXAM-CO301-W26",
        "title": "Data Structures Winter 2026",
        "exam_date": "2026-11-15",
        "start_time": "10:00:00",
        "end_time": "13:00:00",
        "session_name": "MORNING",
        "status": "SCHEDULED"
    }
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_exam_create_payload(data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    exam = ExamService.create_exam(
        validated_data=validated_data,
        creator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=serialize_exam(exam),
        message=f"Exam '{exam.exam_code}' ({exam.title}) scheduled successfully.",
        status_code=201,
    )


@exams_bp.route("/<int:exam_id>", methods=["PUT"])
@login_required
@admin_required
def update_exam(exam_id: int):
    """
    PUT /api/exams/<id>
    Updates examination schedule, times, or metadata.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_exam_update_payload(exam_id, data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    exam = ExamService.update_exam(
        exam_id=exam_id,
        validated_data=validated_data,
        modifier_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=serialize_exam(exam),
        message=f"Exam {exam.exam_code} updated successfully."
    )


@exams_bp.route("/<int:exam_id>/status", methods=["PATCH"])
@login_required
@admin_required
def change_exam_status(exam_id: int):
    """
    PATCH /api/exams/<id>/status
    Transitions exam lifecycle status (e.g. SCHEDULED -> PLANNED -> COMPLETED).
    Payload: {"status": "PLANNED"}
    """
    data = request.get_json(silent=True) or {}
    if "status" not in data:
        raise BadRequestError("Field 'status' is required.")

    new_status = str(data["status"]).strip().upper()
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    exam = ExamService.change_exam_status(
        exam_id=exam_id,
        new_status=new_status,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=serialize_exam(exam),
        message=f"Exam {exam.exam_code} transitioned to status '{new_status}'."
    )


@exams_bp.route("/<int:exam_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_exam(exam_id: int):
    """
    DELETE /api/exams/<id>
    Removes scheduled exam if no published seating plan exists.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    ExamService.delete_exam(
        exam_id=exam_id,
        deleter_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Exam deleted successfully."
    )


# =============================================================================
# 2. CANDIDATE REGISTRATION ENDPOINTS
# =============================================================================

@exams_bp.route("/<int:exam_id>/registrations", methods=["GET"])
@login_required
def get_exam_registrations(exam_id: int):
    """
    GET /api/exams/<id>/registrations
    Retrieves paginated registered candidates for an examination.
    Query params: ?page=1&per_page=20&is_eligible=true&attendance_status=PENDING&search=EE01
    """
    page_param = request.args.get("page")
    page = int(page_param) if page_param is not None else 1
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", type=str)
    attendance = request.args.get("attendance_status", type=str)

    is_eligible_param = request.args.get("is_eligible")
    is_eligible = None
    if is_eligible_param is not None:
        is_eligible = is_eligible_param.lower() in ("true", "1", "yes")

    result = RegistrationService.get_exam_registrations(
        exam_id=exam_id,
        page=page,
        per_page=per_page,
        is_eligible=is_eligible,
        attendance_status=attendance,
        search=search,
    )

    meta = result.get("pagination") if page is not None else {"total": result.get("total")}
    return success_response(
        data=result["registrations"],
        meta=meta,
        message="Exam registrations retrieved successfully."
    )


@exams_bp.route("/<int:exam_id>/registrations", methods=["POST"])
@login_required
@admin_required
def register_student(exam_id: int):
    """
    POST /api/exams/<id>/registrations
    Registers an individual candidate for an examination.
    Payload: {"student_id": 1, "is_eligible": true}
    """
    data = request.get_json(silent=True) or {}
    if not data.get("student_id"):
        raise BadRequestError("Field 'student_id' (integer) is required.")

    student_id = int(data["student_id"])
    is_eligible = bool(data.get("is_eligible", True))
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    reg = RegistrationService.register_student(
        student_id=student_id,
        exam_id=exam_id,
        is_eligible=is_eligible,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=reg.to_dict(),
        message=f"Student {reg.student.roll_number} registered for Exam {reg.exam.exam_code} successfully.",
        status_code=201,
    )


@exams_bp.route("/<int:exam_id>/bulk-enroll", methods=["POST"])
@login_required
@admin_required
def bulk_enroll_students(exam_id: int):
    """
    POST /api/exams/<id>/bulk-enroll
    Enrolls all active students from the subject's branch/semester in batch.
    Payload: {"semester": 3} (optional)
    """
    data = request.get_json(silent=True) or {}
    semester = data.get("semester")
    if semester is not None:
        semester = int(semester)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    result = RegistrationService.bulk_enroll_department_students(
        exam_id=exam_id,
        semester=semester,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=result,
        message=(
            f"Bulk enrollment completed: {result['enrolled']} newly enrolled, "
            f"{result['skipped']} already registered. Total candidates: {result['total']}."
        )
    )


@exams_bp.route("/<int:exam_id>/registrations/<int:student_id>", methods=["DELETE"])
@login_required
@admin_required
def deregister_student(exam_id: int, student_id: int):
    """
    DELETE /api/exams/<id>/registrations/<student_id>
    Removes student's registration (prevented if allocated in published plan).
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    RegistrationService.deregister_student(
        student_id=student_id,
        exam_id=exam_id,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Student deregistered from examination successfully."
    )


@exams_bp.route("/registrations/<int:registration_id>", methods=["PATCH"])
@login_required
@admin_required
def update_registration_status(registration_id: int):
    """
    PATCH /api/exams/registrations/<id>
    Updates eligibility or attendance status of an enrolled candidate.
    Payload: {"is_eligible": true, "attendance_status": "PRESENT|ABSENT|PENDING"}
    """
    data = request.get_json(silent=True) or {}
    is_eligible = data.get("is_eligible")
    attendance = data.get("attendance_status")

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    reg = RegistrationService.update_registration_status(
        registration_id=registration_id,
        is_eligible=is_eligible,
        attendance_status=attendance,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=reg.to_dict(),
        message="Registration status updated successfully."
    )
