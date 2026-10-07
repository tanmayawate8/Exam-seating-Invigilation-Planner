"""
Reports Routes Module (Member 4 Integration Gateway).
Exposes REST delivery endpoints serving official PDF and Excel examination documents:
- Master Seating Arrangement Charts
- Examination Room Door Notices
- Candidate Hall Attendance & Signature Sheets
- Faculty Invigilation Duty Rosters
- Diagnostic Data Contract Specifications
"""

from flask import Blueprint, request, send_file
from flask_login import current_user, login_required
from app.services.report_service import ReportService
from app.utils.decorators import admin_required, admin_or_teacher_required
from app.utils.responses import success_response

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for reports blueprint."""
    return success_response(
        data={"blueprint": "reports", "status": "active"},
        message="Reports gateway blueprint is active.",
    )


@reports_bp.route("/contracts", methods=["GET"])
def get_contracts():
    """
    GET /api/reports/contracts
    Retrieves formal JSON schema metadata for Member 3 <-> Member 4 data contracts.
    """
    contracts = ReportService.get_contracts_meta()
    return success_response(
        data=contracts,
        message="Member 4 data contract specifications retrieved successfully.",
    )


@reports_bp.route("/seating-chart/<int:plan_id>", methods=["GET"])
@login_required
@admin_required
def get_seating_chart(plan_id: int):
    """
    GET /api/reports/seating-chart/<plan_id>?format=pdf|excel
    Exports Master Seating Arrangement Chart for a generated seating plan.
    """
    format_type = request.args.get("format", "pdf")
    buf, filename, mime_type = ReportService.generate_seating_chart(
        plan_id=plan_id,
        format_type=format_type,
        operator_user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return send_file(
        buf,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
    )


@reports_bp.route("/room-notice/<int:plan_id>/<int:room_id>", methods=["GET"])
@admin_or_teacher_required
def get_room_notice(plan_id: int, room_id: int):
    """
    GET /api/reports/room-notice/<plan_id>/<room_id>?format=pdf
    Exports Hall Door Notice / Noticeboard Seating Chart.
    """
    format_type = request.args.get("format", "pdf")
    buf, filename, mime_type = ReportService.generate_room_notice(
        plan_id=plan_id,
        room_id=room_id,
        format_type=format_type,
        operator_user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return send_file(
        buf,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
    )


@reports_bp.route("/attendance-sheet/<int:plan_id>/<int:room_id>", methods=["GET"])
@admin_or_teacher_required
def get_attendance_sheet(plan_id: int, room_id: int):
    """
    GET /api/reports/attendance-sheet/<plan_id>/<room_id>?format=pdf|excel
    Exports Examination Hall Attendance & Signature Sheet for invigilators.
    """
    format_type = request.args.get("format", "pdf")
    buf, filename, mime_type = ReportService.generate_attendance_sheet(
        plan_id=plan_id,
        room_id=room_id,
        format_type=format_type,
        operator_user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return send_file(
        buf,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
    )


@reports_bp.route("/duty-roster/<int:exam_id>", methods=["GET"])
@admin_or_teacher_required
def get_duty_roster(exam_id: int):
    """
    GET /api/reports/duty-roster/<exam_id>?format=pdf|excel
    Exports Faculty Invigilation Duty Roster.
    """
    format_type = request.args.get("format", "pdf")
    buf, filename, mime_type = ReportService.generate_duty_roster(
        exam_id=exam_id,
        format_type=format_type,
        operator_user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return send_file(
        buf,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
    )
