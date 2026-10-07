"""
Notifications Routes Module.
Exposes endpoints for user notification feeds, unread count tracking,
status toggling, and administrator announcement broadcasts.
"""

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.schemas.notification import validate_broadcast_payload
from app.services.notification_service import NotificationService
from app.utils.decorators import admin_required
from app.utils.errors import BadRequestError
from app.utils.responses import success_response

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/ping", methods=["GET"])
def ping():
    """Health check ping for notifications blueprint."""
    return success_response(
        data={"blueprint": "notifications", "status": "active"},
        message="Notifications blueprint is active.",
    )


@notifications_bp.route("", methods=["GET"])
@login_required
def get_notifications():
    """
    GET /api/notifications
    Retrieves paginated notifications for the authenticated user.
    Query params:
    - is_read: optional bool (true/false)
    - page: optional int (default 1)
    - per_page: optional int (default 20)
    """
    is_read_param = request.args.get("is_read")
    is_read = None
    if is_read_param is not None:
        is_read = is_read_param.strip().lower() in ("true", "1", "yes")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    result = NotificationService.get_user_notifications(
        user_id=current_user.id,
        is_read=is_read,
        page=page,
        per_page=per_page,
    )

    return success_response(
        data=result,
        message="User notifications retrieved successfully.",
    )


@notifications_bp.route("/unread-count", methods=["GET"])
@login_required
def get_unread_count():
    """
    GET /api/notifications/unread-count
    Returns the total count of unread notifications for the badge counter.
    """
    count = NotificationService.get_unread_count(current_user.id)
    return success_response(
        data={"unread_count": count},
        message="Unread notification count retrieved.",
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["PATCH", "PUT"])
@login_required
def mark_notification_read(notification_id: int):
    """
    PATCH/PUT /api/notifications/<id>/read
    Marks an individual notification as read.
    """
    notification = NotificationService.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return success_response(
        data=notification.to_dict(),
        message="Notification marked as read.",
    )


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    """
    POST /api/notifications/mark-all-read
    Marks all notifications for the current user as read.
    """
    updated_count = NotificationService.mark_all_as_read(current_user.id)
    return success_response(
        data={"updated_count": updated_count},
        message=f"{updated_count} notification(s) marked as read.",
    )


@notifications_bp.route("/<int:notification_id>", methods=["DELETE"])
@login_required
def delete_notification(notification_id: int):
    """
    DELETE /api/notifications/<id>
    Dismisses and deletes an individual notification.
    """
    NotificationService.delete_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return success_response(
        data=None,
        message="Notification deleted successfully.",
    )


@notifications_bp.route("/broadcast", methods=["POST"])
@login_required
@admin_required
def broadcast_notification():
    """
    POST /api/notifications/broadcast
    Admin action to dispatch announcements to cohorts (ALL, STUDENT, TEACHER, ADMIN).
    Payload: {"title": "...", "message": "...", "target_role": "STUDENT|TEACHER|ALL"}
    """
    payload = request.get_json(silent=True) or {}
    validated_data = validate_broadcast_payload(payload)

    result = NotificationService.broadcast_notification(
        validated_data=validated_data,
        sender_user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return success_response(
        data=result,
        message=f"Broadcast successfully sent to {result['recipients_count']} recipient(s).",
        status_code=201,
    )
