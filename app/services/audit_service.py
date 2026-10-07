"""
Audit Service Module.
Provides administrative compliance queries, filtering, and metric aggregations
over immutable system audit logs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.errors import NotFoundError, ValidationError


class AuditService:
    """Service layer managing access to immutable system audit trails."""

    @staticmethod
    def get_audit_logs(
        page: int = 1,
        per_page: int = 25,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves paginated audit log entries with multi-attribute filtering:
        - action (exact or prefix match)
        - entity_type
        - user_id
        - start_date / end_date (YYYY-MM-DD)
        - search (matches action, entity_type, or details text)
        """
        query = AuditLog.query

        if action:
            query = query.filter(AuditLog.action == action.strip().upper())

        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type.strip())

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if start_date:
            try:
                start_dt = datetime.strptime(start_date.strip()[:10], "%Y-%m-%d")
                query = query.filter(AuditLog.timestamp >= start_dt)
            except ValueError:
                raise ValidationError("Invalid start_date format. Expected YYYY-MM-DD.")

        if end_date:
            try:
                # Include whole day up to 23:59:59
                end_dt = datetime.strptime(end_date.strip()[:10], "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                query = query.filter(AuditLog.timestamp <= end_dt)
            except ValueError:
                raise ValidationError("Invalid end_date format. Expected YYYY-MM-DD.")

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    AuditLog.action.ilike(search_pattern),
                    AuditLog.entity_type.ilike(search_pattern),
                    AuditLog.details.ilike(search_pattern),
                    AuditLog.ip_address.ilike(search_pattern),
                )
            )

        query = query.order_by(AuditLog.timestamp.desc())

        if page is not None and per_page is not None:
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "audit_logs": [log.to_dict() for log in paginated.items],
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
            "audit_logs": [log.to_dict() for log in all_items],
            "total": len(all_items),
        }

    @staticmethod
    def get_audit_log_by_id(log_id: int) -> AuditLog:
        """Retrieves a single audit log entry by its primary key ID."""
        log = AuditLog.query.get(log_id)
        if not log:
            raise NotFoundError(f"Audit log entry with ID {log_id} not found.")
        return log

    @staticmethod
    def get_audit_summary() -> Dict[str, Any]:
        """
        Calculates audit trail statistical summary for Admin dashboards:
        - Total audit events
        - Breakdown by action
        - Breakdown by entity type
        - Count of security alert events (e.g., failed logins, forbidden attempts)
        """
        total_count = db.session.query(func.count(AuditLog.id)).scalar() or 0

        # Action breakdown (top 10)
        action_counts = (
            db.session.query(AuditLog.action, func.count(AuditLog.id).label("count"))
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
            .all()
        )

        # Entity type breakdown
        entity_counts = (
            db.session.query(AuditLog.entity_type, func.count(AuditLog.id).label("count"))
            .group_by(AuditLog.entity_type)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
            .all()
        )

        # Security-sensitive events
        security_actions = ["LOGIN_FAILED", "FORBIDDEN_ACCESS_ATTEMPT", "UNAUTHORIZED_ACCESS"]
        security_alerts = (
            AuditLog.query.filter(AuditLog.action.in_(security_actions))
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
            .all()
        )

        return {
            "total_logs": total_count,
            "top_actions": [{"action": act, "count": cnt} for act, cnt in action_counts],
            "top_entity_types": [{"entity_type": ent, "count": cnt} for ent, cnt in entity_counts],
            "security_alerts_count": (
                AuditLog.query.filter(AuditLog.action.in_(security_actions)).count()
            ),
            "recent_security_alerts": [log.to_dict() for log in security_alerts],
        }
