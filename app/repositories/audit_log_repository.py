"""
AuditLog repository for Leviia Schedule.

Data access layer for the AuditLog model - no business logic, no Flask
request/response handling, just queries. See app/services/audit_service.py
for the single write path (routes/services never call create() directly).
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import AuditLog


class AuditLogRepository:
    """Data access for the AuditLog model."""

    @staticmethod
    def create(
        actor_id: int | None,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        details: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(entry)
        return entry

    @staticmethod
    def list_paginated(
        page: int,
        per_page: int,
        actor_id: int | None = None,
        action_prefix: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        query = AuditLog.query.order_by(AuditLog.created_at.desc())

        if actor_id is not None:
            query = query.filter(AuditLog.actor_id == actor_id)
        if action_prefix:
            query = query.filter(AuditLog.action.like(f"{action_prefix}%"))
        if date_from is not None:
            query = query.filter(
                AuditLog.created_at >= datetime.combine(date_from, datetime.min.time())
            )
        if date_to is not None:
            # Inclusive of the whole end day.
            query = query.filter(
                AuditLog.created_at
                < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)
            )

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def delete_older_than(cutoff: datetime) -> int:
        """Delete entries created strictly before cutoff. Returns the
        number deleted."""
        return AuditLog.query.filter(AuditLog.created_at < cutoff).delete(
            synchronize_session=False
        )
