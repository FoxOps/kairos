"""
AuditService for Kairos.

Single write path for the audit trail (app/models/audit_log.py) - every
business-relevant mutation and auth event goes through
AuditService.log(), which writes to both the AuditLog table (consultable
at /admin/audit-log) and logs/audit.log (defense in depth: a bug here
must never break the business action it's recording, so failures are
caught and logged, never raised). `action` values are namespaced
"<domain>.<verb>" strings, e.g. shift.create, swap.approve,
auth.login_failure.
"""

import logging

from flask import has_request_context
from flask import request as flask_request
from flask_login import current_user

from app import db
from app.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.utils.logging import log_audit_action

logger = logging.getLogger(__name__)


class AuditService:
    """Writes audit trail entries. Called from the service layer as a
    cross-cutting effect (same placement as AppNotificationService calls
    within SwapService) right after the triggering action's own
    db.session.commit() - never before, so a rolled-back action is never
    recorded as if it succeeded. Exception: app/routes/auth.py calls this
    directly, since login/logout/register have no dedicated service
    layer in this app."""

    @staticmethod
    def log(
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        details: str | None = None,
        actor: User | None = None,
    ) -> None:
        """
        Args:
            action: Namespaced "<domain>.<verb>" string, e.g.
                "shift.create", "swap.approve", "auth.login_failure".
            resource_type: Model class name the action applies to, or
                None for actions with no single target resource.
            resource_id: Primary key of the affected row, or None.
            details: Short human-readable summary, not a structured diff.
            actor: Explicit actor, e.g. for auth.login_failure where the
                attempted user may not be current_user (no session yet).
                Falls back to current_user when omitted - same
                has_request_context() guard as app.get_locale(), so this
                is always safe to call even without a real request.

        A failure writing the audit entry is logged and swallowed, never
        propagated - an audit trail bug must not turn into a denial of
        service for the actual business action it's recording.
        """
        try:
            if (
                actor is None
                and has_request_context()
                and current_user.is_authenticated
            ):
                actor = current_user

            ip_address = flask_request.remote_addr if has_request_context() else None

            AuditLogRepository.create(
                actor_id=actor.id if actor else None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
            )
            db.session.commit()

            log_audit_action(
                action=action,
                user=actor,
                path=flask_request.path if has_request_context() else None,
                details=details,
            )
        except Exception:
            db.session.rollback()
            logger.exception("Failed to write audit log entry for action=%s", action)
