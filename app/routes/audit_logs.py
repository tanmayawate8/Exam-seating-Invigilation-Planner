"""
Audit Logs Routes Module.
Exposes read-only administrative endpoints for inspecting immutable system audit trails,
security events, user actions, and forensic timelines.
"""

from flask import Blueprint, request
from flask_login import login_required

from app.services.audit_service import AuditService
from app.utils.decorators import admin_required
from app.utils.responses import success_response

audit_logs_bp = Blueprint("audit_logs", __name__)


@audit_logs_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for audit logs blueprint."""
    return success_response(
        data={"blueprint": "audit_logs", "status": "active"},
        message="Audit logs blueprint is active.",
    )


@audit_logs_bp.route("", methods=["GET"])
@login_required
@admin_required
def get_audit_logs():
    """
    GET /api/audit-logs
    Retrieves filtered and paginated immutable system audit records.
    Query params:
    - action: optional str
    - entity_type: optional str
    - user_id: optional int
    - start_date: optional str (YYYY-MM-DD)
    - end_date: optional str (YYYY-MM-DD)
    - search: optional str
    - page: optional int (default 1)
    - per_page: optional int (default 25)
    """
    action = request.args.get("action")
    entity_type = request.args.get("entity_type")
    user_id = request.args.get("user_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search = request.args.get("search")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    result = AuditService.get_audit_logs(
        page=page,
        per_page=per_page,
        action=action,
        entity_type=entity_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )

    return success_response(
        data=result,
        message="Audit logs retrieved successfully.",
    )


@audit_logs_bp.route("/summary", methods=["GET"])
@login_required
@admin_required
def get_audit_summary():
    """
    GET /api/audit-logs/summary
    Retrieves system activity metrics, top actions, and security alerts.
    """
    summary = AuditService.get_audit_summary()
    return success_response(
        data=summary,
        message="Audit log summary retrieved successfully.",
    )


@audit_logs_bp.route("/<int:log_id>", methods=["GET"])
@login_required
@admin_required
def get_audit_log_detail(log_id: int):
    """
    GET /api/audit-logs/<id>
    Retrieves a single audit log entry by ID.
    """
    log = AuditService.get_audit_log_by_id(log_id)
    return success_response(
        data=log.to_dict(),
        message=f"Audit log #{log_id} retrieved successfully.",
    )
