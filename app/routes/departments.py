"""
Department Management Routes Module (Admin & Academic).
Exposes RESTful endpoints for Polytechnic engineering branches/departments.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.academic_service import AcademicService
from app.utils.decorators import admin_required
from app.utils.responses import success_response

departments_bp = Blueprint("departments", __name__)


@departments_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for department routes."""
    return success_response(data={"blueprint": "departments", "status": "active"}, message="Departments blueprint is active.")


@departments_bp.route("", methods=["GET"])
@login_required
def get_departments():
    """
    GET /api/departments
    Retrieves all Polytechnic engineering branches with optional keyword search.
    """
    search = request.args.get("search", type=str)
    departments = AcademicService.get_departments(search=search)
    return success_response(
        data=departments,
        message="Departments retrieved successfully."
    )


@departments_bp.route("/semesters", methods=["GET"])
@login_required
def get_polytechnic_semesters():
    """
    GET /api/departments/semesters
    Retrieves the standard 3-Year Diploma semester structure (Semesters 1 to 6).
    """
    semesters = AcademicService.get_polytechnic_semesters()
    return success_response(
        data=semesters,
        message="Polytechnic semesters retrieved successfully."
    )


@departments_bp.route("/<int:department_id>", methods=["GET"])
@login_required
def get_department_by_id(department_id: int):
    """
    GET /api/departments/<id>
    Fetches a single department by its ID.
    """
    department = AcademicService.get_department_by_id(department_id)
    return success_response(
        data=department.to_dict(),
        message="Department retrieved successfully."
    )


@departments_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_department():
    """
    POST /api/departments
    Creates a new Polytechnic branch (e.g., Computer Engineering).
    Payload: {"code": "CO", "name": "Computer Engineering", "description": "..."}
    """
    data = request.get_json(silent=True) or {}
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    dept = AcademicService.create_department(
        code=data,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=dept.to_dict(),
        message=f"Department '{dept.name}' ({dept.code}) created successfully.",
        status_code=201,
    )


@departments_bp.route("/<int:department_id>", methods=["PUT"])
@login_required
@admin_required
def update_department(department_id: int):
    """
    PUT /api/departments/<id>
    Updates attributes of an existing branch.
    Payload: {"code": "...", "name": "...", "description": "..."}
    """
    data = request.get_json(silent=True) or {}
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    dept = AcademicService.update_department(
        department_id=department_id,
        code=data.get("code"),
        name=data.get("name"),
        description=data.get("description"),
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=dept.to_dict(),
        message=f"Department '{dept.name}' ({dept.code}) updated successfully."
    )


@departments_bp.route("/<int:department_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_department(department_id: int):
    """
    DELETE /api/departments/<id>
    Removes a branch if no students or subjects are associated with it.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    AcademicService.delete_department(
        department_id=department_id,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        message="Department deleted successfully."
    )
