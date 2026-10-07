"""
Notification Service Module.
Handles notification delivery, status tracking, broadcast announcements,
and read state management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.utils.audit import log_audit
from app.utils.errors import NotFoundError, ForbiddenError, ValidationError


class NotificationService:
    """Service layer managing user notifications and system announcements."""

    @staticmethod
    def get_user_notifications(
        user_id: int,
        is_read: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Retrieves paginated notifications for a specific user.
        Supports filtering by read/unread status.
        """
        query = Notification.query.filter_by(user_id=user_id)

        if is_read is not None:
            query = query.filter(Notification.is_read.is_(is_read))

        query = query.order_by(Notification.created_at.desc())

        if page is not None and per_page is not None:
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "notifications": [n.to_dict() for n in paginated.items],
                "pagination": {
                    "total": paginated.total,
                    "page": paginated.page,
                    "pages": paginated.pages,
                    "per_page": paginated.per_page,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }

        all_items = query.all()
        return {
            "notifications": [n.to_dict() for n in all_items],
            "total": len(all_items),
        }

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Returns the total number of unread notifications for a user."""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> Notification:
        """Marks an individual notification as read. Validates user ownership."""
        notification = Notification.query.get(notification_id)
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found.")

        if notification.user_id != user_id:
            raise ForbiddenError("You cannot modify notifications belonging to another user.")

        if not notification.is_read:
            notification.is_read = True
            db.session.commit()

        return notification

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """Marks all unread notifications as read for a user. Returns count updated."""
        updated = (
            Notification.query.filter_by(user_id=user_id, is_read=False)
            .update({"is_read": True}, synchronize_session="fetch")
        )
        db.session.commit()
        return updated

    @staticmethod
    def create_notification(
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "GENERAL",
    ) -> Notification:
        """Creates a targeted notification for a single user."""
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(f"Target user with ID {user_id} not found.")

        notif = Notification(
            user_id=user.id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def broadcast_notification(
        validated_data: Dict[str, Any],
        sender_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Broadcasts an announcement notification to a targeted cohort of users
        (ALL, STUDENT, TEACHER, or ADMIN).
        """
        target_role = validated_data.get("target_role", "ALL")
        title = validated_data["title"]
        message = validated_data["message"]
        notif_type = validated_data.get("notification_type", "BROADCAST")

        query = User.query.filter_by(is_active=True)
        if target_role != "ALL":
            query = query.filter_by(role=target_role)

        recipients = query.all()
        if not recipients:
            raise ValidationError(f"No active users found with target role '{target_role}'.")

        notifications_to_add = []
        for user in recipients:
            notifications_to_add.append(
                Notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type=notif_type,
                    is_read=False,
                    created_at=datetime.utcnow(),
                )
            )

        db.session.add_all(notifications_to_add)
        db.session.commit()

        log_audit(
            action="NOTIFICATION_BROADCAST",
            entity_type="Notification",
            entity_id=f"Target:{target_role}",
            user_id=sender_user_id,
            details=f"Broadcast '{title}' sent to {len(recipients)} recipients with role '{target_role}'.",
            ip_address=ip_address,
        )

        return {
            "title": title,
            "target_role": target_role,
            "recipients_count": len(recipients),
            "notification_type": notif_type,
        }

    @staticmethod
    def delete_notification(notification_id: int, user_id: int) -> bool:
        """Deletes/dismisses an individual notification. Enforces ownership."""
        notification = Notification.query.get(notification_id)
        if not notification:
            raise NotFoundError(f"Notification with ID {notification_id} not found.")

        if notification.user_id != user_id:
            raise ForbiddenError("You cannot delete notifications belonging to another user.")

        db.session.delete(notification)
        db.session.commit()
        return True
