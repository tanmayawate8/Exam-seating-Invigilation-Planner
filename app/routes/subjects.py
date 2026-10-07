"""
Subject Management Routes Module (Admin & Curriculum).
Exposes RESTful endpoints for Polytechnic courses, subject codes, and semester curricula.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.academic_service import AcademicService
from app.utils.decorators import admin_required
from app.utils.responses import success_response

subjects_bp = Blueprint("subjects", __name__)


@subjects_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for subject routes."""
    return success_response(data={"blueprint": "subjects", "status": "active"}, message="Subjects blueprint is active.")


@subjects_bp.route("", methods=["GET"])
@login_required
def get_subjects():
    """
    GET /api/subjects
    Retrieves subjects with optional filtering by department, semester, and keyword search.
    Query params: ?department_id=1&semester=3&search=data
    """
    dept_id = request.args.get("department_id", type=int)
    semester = request.args.get("semester", type=int)
    search = request.args.get("search", type=str)

    subjects = AcademicService.get_subjects(
        department_id=dept_id,
        semester=semester,
        search=search,
    )

    return success_response(
        data=subjects,
        message="Subjects retrieved successfully."
    )


@subjects_bp.route("/<int:subject_id>", methods=["GET"])
@login_required
def get_subject_by_id(subject_id: int):
    """
    GET /api/subjects/<id>
    Fetches a single subject by ID.
    """
    subject = AcademicService.get_subject_by_id(subject_id)
    return success_response(
        data=subject.to_dict(),
        message="Subject retrieved successfully."
    )


@subjects_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_subject():
    """
    POST /api/subjects
    Creates an academic subject within a Polytechnic branch curriculum.
    Payload: {
        "code": "CO301",
        "name": "Data Structures",
        "department_id": 1,
        "semester": 3,
        "credits": 4
    }
    """
    data = request.get_json(silent=True) or {}
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    subject = AcademicService.create_subject(
        code=data,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=subject.to_dict(),
        message=f"Subject '{subject.name}' ({subject.code}) created successfully.",
        status_code=201,
    )


@subjects_bp.route("/<int:subject_id>", methods=["PUT"])
@login_required
@admin_required
def update_subject(subject_id: int):
    """
    PUT /api/subjects/<id>
    Updates attributes of an existing curriculum subject.
    Payload: {"code": "...", "name": "...", "semester": 3, "credits": 4}
    """
    data = request.get_json(silent=True) or {}
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    subject = AcademicService.update_subject(
        subject_id=subject_id,
        code=data.get("code"),
        name=data.get("name"),
        semester=data.get("semester"),
        credits=data.get("credits"),
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=subject.to_dict(),
        message=f"Subject '{subject.name}' ({subject.code}) updated successfully."
    )


@subjects_bp.route("/<int:subject_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_subject(subject_id: int):
    """
    DELETE /api/subjects/<id>
    Removes a subject if not referenced by active examinations.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    AcademicService.delete_subject(
        subject_id=subject_id,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Subject deleted successfully."
    )
