"""
Student Management Routes Module (Admin & Faculty).
Exposes RESTful endpoints for Polytechnic student records, status toggles, search, and pagination.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.student_service import StudentService
from app.schemas.student import (
    validate_student_create_payload,
    validate_student_update_payload,
)
from app.utils.decorators import admin_required, role_required
from app.utils.errors import ForbiddenError, BadRequestError
from app.utils.responses import success_response

students_bp = Blueprint("students", __name__)


@students_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for student routes."""
    return success_response(data={"blueprint": "students", "status": "active"}, message="Students blueprint is active.")


@students_bp.route("", methods=["GET"])
@login_required
@role_required("ADMIN", "TEACHER")
def get_students():
    """
    GET /api/students
    Retrieves paginated Polytechnic student directory with filters.
    Query params: ?page=1&per_page=20&department_id=1&semester=3&is_active=true&search=tanmay
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    dept_id = request.args.get("department_id", type=int)
    semester = request.args.get("semester", type=int)
    search = request.args.get("search", type=str)

    is_active_param = request.args.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() in ("true", "1", "yes")

    result = StudentService.get_students(
        page=page,
        per_page=per_page,
        department_id=dept_id,
        semester=semester,
        is_active=is_active,
        search=search,
    )

    return success_response(
        data=result["students"],
        meta={"pagination": result["pagination"]},
        message="Students retrieved successfully."
    )


@students_bp.route("/<int:student_id>", methods=["GET"])
@login_required
def get_student_by_id(student_id: int):
    """
    GET /api/students/<id>
    Fetches a single student record.
    Accessible to Admins, Teachers, or the Student themselves.
    """
    if current_user.role == "STUDENT":
        if not current_user.student_profile or current_user.student_profile.id != student_id:
            raise ForbiddenError("You are not authorized to view another student's record.")

    student = StudentService.get_student_by_id(student_id)
    return success_response(
        data=student.to_dict(),
        message="Student retrieved successfully."
    )


@students_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_student():
    """
    POST /api/students
    Enrolls a new Polytechnic student and provisions their linked user account.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_student_create_payload(data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    student = StudentService.create_student(
        validated_data=validated_data,
        creator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=student.to_dict(),
        message=f"Student '{student.full_name}' ({student.roll_number}) enrolled successfully.",
        status_code=201,
    )


@students_bp.route("/<int:student_id>", methods=["PUT"])
@login_required
@admin_required
def update_student(student_id: int):
    """
    PUT /api/students/<id>
    Updates attributes of an existing student.
    """
    data = request.get_json(silent=True) or {}
    validated_data = validate_student_update_payload(student_id, data)

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    student = StudentService.update_student(
        student_id=student_id,
        validated_data=validated_data,
        modifier_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=student.to_dict(),
        message=f"Student {student.roll_number} updated successfully."
    )


@students_bp.route("/<int:student_id>/status", methods=["PATCH"])
@login_required
@admin_required
def toggle_student_status(student_id: int):
    """
    PATCH /api/students/<id>/status
    Enables or disables a student's active enrollment status.
    Payload: {"is_active": bool}
    """
    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        raise BadRequestError("Field 'is_active' (boolean) is required.")

    is_active = bool(data["is_active"])
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    student = StudentService.toggle_student_status(
        student_id=student_id,
        is_active=is_active,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    status_str = "activated" if is_active else "deactivated"
    return success_response(
        data=student.to_dict(),
        message=f"Student {student.roll_number} has been {status_str}."
    )


@students_bp.route("/<int:student_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_student(student_id: int):
    """
    DELETE /api/students/<id>
    Removes student record and linked user credentials.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    StudentService.delete_student(
        student_id=student_id,
        deleter_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Student deleted successfully."
    )


# =============================================================================
# STUDENT EXCEL / CSV IMPORT WORKFLOW (OFFICIAL TYCO ROLL-CALL STRUCTURE)
# =============================================================================

@students_bp.route("/import/template", methods=["GET"])
@login_required
@admin_required
def download_import_template():
    """
    GET /api/students/import/template?format=excel|csv
    Generates and serves the official student import template.
    """
    from flask import send_file
    from app.services.import_service import ImportService

    format_type = request.args.get("format", "excel")
    buf, filename, mimetype = ImportService.generate_template(format_type=format_type)

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype,
    )


@students_bp.route("/import/preview", methods=["POST"])
@login_required
@admin_required
def preview_student_import():
    """
    POST /api/students/import/preview
    Validates uploaded Excel/CSV file or JSON rows against academic rules and duplicates.
    Returns preview report without modifying the database.
    """
    from app.services.import_service import ImportService

    if "file" in request.files and request.files["file"].filename:
        uploaded_file = request.files["file"]
        result = ImportService.preview_student_import(
            file_stream=uploaded_file.stream,
            filename=uploaded_file.filename,
        )
    elif request.is_json and "rows" in (request.get_json(silent=True) or {}):
        rows = request.get_json()["rows"]
        result = ImportService.validate_student_rows(rows)
    else:
        raise BadRequestError("Please upload an Excel (.xlsx) or CSV file, or provide 'rows' in JSON payload.")

    return success_response(
        data=result,
        message=(
            f"File validation complete: {result['valid_count']} valid, "
            f"{result['invalid_count']} invalid/flagged, {result['duplicate_count']} duplicates."
        ),
    )


@students_bp.route("/import/commit", methods=["POST"])
@login_required
@admin_required
def commit_student_import():
    """
    POST /api/students/import/commit
    Persists validated student records and provisions user accounts inside an atomic transaction.
    Initial password for each student is their Enrollment Number from the official roll call (hashed securely).
    """
    from app.services.import_service import ImportService

    data = request.get_json(silent=True) or {}
    rows = data.get("rows")

    if not rows and "file" in request.files and request.files["file"].filename:
        uploaded_file = request.files["file"]
        preview = ImportService.preview_student_import(
            file_stream=uploaded_file.stream,
            filename=uploaded_file.filename,
        )
        rows = [r["data"] for r in preview["rows"] if r["status"] == "VALID"]

    if not rows:
        raise BadRequestError("No valid student rows provided for import commitment.")

    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    result = ImportService.commit_student_import(
        valid_student_data=rows,
        creator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=result,
        message=result["message"],
        status_code=201,
    )

