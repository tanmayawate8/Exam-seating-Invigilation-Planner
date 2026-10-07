"""
Audit Logging Utility Module.
Provides helper functions to record immutable audit trail records for security and compliance.
"""

from app.extensions import db
from app.models.audit_log import AuditLog


def log_audit(
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    user_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Creates and commits an immutable audit log entry.

    :param action: Action performed (e.g., 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGOUT')
    :param entity_type: Category of entity affected (e.g., 'User', 'Session', 'Exam')
    :param entity_id: ID of the affected entity
    :param user_id: ID of the user performing the action (None for system actions)
    :param details: Descriptive context or JSON string
    :param ip_address: Remote client IP address
    :return: The committed AuditLog instance
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
    except Exception as exc:
        db.session.rollback()
        # Fallback logging without crashing the main application flow
        import logging
        logging.getLogger("exam_planner.audit").error(f"Failed to record audit log: {exc}")
        return None
