"""
Planning Integration Routes Module (Admin & Execution).
Exposes RESTful endpoints for automated seating plan generation,
invigilation duty assignments, plan publishing with notifications,
and visual 2D seating matrix grids.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.services.planning_service import PlanningService
from app.utils.decorators import admin_required
from app.utils.errors import BadRequestError
from app.utils.responses import success_response

planning_bp = Blueprint("planning", __name__)


@planning_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for planning integration routes."""
    return success_response(data={"blueprint": "planning", "status": "active"}, message="Planning blueprint is active.")


# =============================================================================
# 1. SEATING PLAN GENERATION & PERSISTENCE
# =============================================================================

@planning_bp.route("/seating/generate", methods=["POST"])
@login_required
@admin_required
def generate_seating_plan():
    """
    POST /api/planning/seating/generate
    Triggers Member 4's seating algorithm adapter and persists allocations atomically.
    Payload: {
        "exam_id": 1,
        "room_ids": [1, 2],       (optional, defaults to active venues)
        "options": { ... }         (optional algorithm params)
    }
    """
    data = request.get_json(silent=True) or {}
    if not data.get("exam_id"):
        raise BadRequestError("Field 'exam_id' (integer) is required.")

    exam_id = int(data["exam_id"])
    room_ids = data.get("room_ids")
    if room_ids:
        room_ids = [int(rid) for rid in room_ids]

    options = data.get("options")
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    plan = PlanningService.generate_seating_plan(
        exam_id=exam_id,
        room_ids=room_ids,
        options=options,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=plan.to_dict(),
        message=(
            f"Seating plan '{plan.plan_code}' generated successfully: "
            f"{plan.total_students_allocated} candidates allocated across {plan.total_rooms_used} halls."
        ),
        status_code=201,
    )


@planning_bp.route("/seating/<int:plan_id>", methods=["GET"])
@login_required
def get_seating_plan_by_id(plan_id: int):
    """
    GET /api/planning/seating/<id>
    Fetches master seating plan details by plan ID.
    """
    plan = PlanningService.get_seating_plan_by_id(plan_id)
    return success_response(
        data=plan.to_dict(),
        message="Seating plan retrieved successfully."
    )


@planning_bp.route("/seating/exam/<int:exam_id>", methods=["GET"])
@login_required
def get_seating_plans_for_exam(exam_id: int):
    """
    GET /api/planning/seating/exam/<exam_id>
    Retrieves all generated seating plans for an examination (all versions).
    """
    plans = PlanningService.get_seating_plans_for_exam(exam_id)
    return success_response(
        data=[p.to_dict() for p in plans],
        message="Seating plans retrieved successfully."
    )


@planning_bp.route("/seating/<int:plan_id>/publish", methods=["POST"])
@login_required
@admin_required
def publish_seating_plan(plan_id: int):
    """
    POST /api/planning/seating/<id>/publish
    Publishes the seating plan, making it visible to students, and dispatches portal notifications.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    plan = PlanningService.publish_seating_plan(
        plan_id=plan_id,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=plan.to_dict(),
        message=f"Seating plan '{plan.plan_code}' published successfully. Notifications sent to all candidates."
    )


@planning_bp.route("/seating/<int:plan_id>/cancel", methods=["POST"])
@login_required
@admin_required
def cancel_seating_plan(plan_id: int):
    """
    POST /api/planning/seating/<id>/cancel
    Cancels an existing seating plan.
    """
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    plan = PlanningService.cancel_seating_plan(
        plan_id=plan_id,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=plan.to_dict(),
        message=f"Seating plan '{plan.plan_code}' cancelled successfully."
    )


@planning_bp.route("/seating/<int:plan_id>/matrix/<int:room_id>", methods=["GET"])
@login_required
def get_room_seating_matrix(plan_id: int, room_id: int):
    """
    GET /api/planning/seating/<plan_id>/matrix/<room_id>
    Generates a 2D visual layout matrix of physical seats and allocated students for visual hall rendering.
    """
    matrix = PlanningService.get_room_seating_matrix(plan_id=plan_id, room_id=room_id)
    return success_response(
        data=matrix,
        message="Room seating layout matrix generated successfully."
    )


# =============================================================================
# 2. INVIGILATION DUTY PLANNING
# =============================================================================

@planning_bp.route("/invigilation/generate", methods=["POST"])
@login_required
@admin_required
def generate_invigilation_duties():
    """
    POST /api/planning/invigilation/generate
    Triggers Member 4's invigilator assignment algorithm adapter and persists duties atomically.
    Payload: {
        "exam_id": 1,
        "room_ids": [1, 2],       (optional, defaults to rooms used in seating plan)
        "options": { ... }         (optional algorithm params)
    }
    """
    data = request.get_json(silent=True) or {}
    if not data.get("exam_id"):
        raise BadRequestError("Field 'exam_id' (integer) is required.")

    exam_id = int(data["exam_id"])
    room_ids = data.get("room_ids")
    if room_ids:
        room_ids = [int(rid) for rid in room_ids]

    options = data.get("options")
    operator_user_id = current_user.id if current_user.is_authenticated else None
    ip_addr = request.remote_addr

    duties = PlanningService.generate_invigilation_duties(
        exam_id=exam_id,
        room_ids=room_ids,
        options=options,
        operator_user_id=operator_user_id,
        ip_address=ip_addr,
    )

    return success_response(
        data=[d.to_dict() for d in duties],
        message=f"Assigned {len(duties)} invigilators successfully. Notifications dispatched to assigned faculty.",
        status_code=201,
    )


@planning_bp.route("/invigilation/exam/<int:exam_id>", methods=["GET"])
@login_required
def get_exam_invigilation_duties(exam_id: int):
    """
    GET /api/planning/invigilation/exam/<exam_id>
    Retrieves all invigilation duties scheduled for an exam session.
    """
    duties = PlanningService.get_exam_invigilation_duties(exam_id)
    return success_response(
        data=[d.to_dict() for d in duties],
        message="Exam invigilation duties retrieved successfully."
    )
