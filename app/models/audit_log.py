"""
AuditLog model for Kairos.

Append-only record of "who did what, when, to which resource" across
the app (user/group/shift/oncall/leave/shift_type/swap CRUD, settings
changes, auth events) - see AuditService (app/services/audit_service.py)
for the single write path and CLAUDE.md's "Audit trail" section for the
full architecture. Not to be confused with NotificationLog (email
send-dedup only) or AppNotification (in-app bell icon, swap-only scope).
"""

from typing import TYPE_CHECKING, cast

from app import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User

_NOT_PRELOADED = object()


class AuditLog(BaseModel):
    """
    AuditLog model for tracking business-relevant mutations and auth events.

    Attributes:
        actor_id: Foreign key to User who performed the action - nullable,
            no action in this app is currently attributed to a
            non-authenticated/system caller, but the column stays
            nullable as the safe default (same as User.timezone/language).
        action: Namespaced "<domain>.<verb>" string, e.g. "shift.create",
            "swap.approve", "auth.login_failure" - see CLAUDE.md for the
            full naming convention and the list of values in use.
        resource_type: Model class name the action applies to (e.g.
            "Shift", "User", "Setting"), or None for actions with no
            single target resource (e.g. auth.login_failure).
        resource_id: Primary key of the affected row, or None.
        details: Short human-readable summary (e.g. "Jean Dupont
            <jean@example.com>") - deliberately not a structured
            field-by-field before/after diff, see CLAUDE.md.
        ip_address: Request IP at the time of the action (IPv6-safe
            length), mainly useful for auth.* entries.
    """

    __tablename__ = "audit_log"

    actor_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True, index=True
    )
    action = db.Column(db.String(64), nullable=False, index=True)
    resource_type = db.Column(db.String(32), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    __table_args__ = (
        db.Index("idx_audit_log_resource", "resource_type", "resource_id"),
    )

    # Same @property-over-db.relationship() pattern as SwapRequest (see
    # that model's comment) - avoids the SQLAlchemy 2.0 stub typing issue
    # (RelationshipProperty[Any] without the dedicated mypy plugin).
    _cached_actor: "User | None | object" = _NOT_PRELOADED

    @property
    def actor(self) -> "User | None":
        if self._cached_actor is not _NOT_PRELOADED:
            return cast("User | None", self._cached_actor)
        if self.actor_id is None:
            return None
        from app.models.user import User

        return db.session.get(User, self.actor_id)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} actor={self.actor_id} resource={self.resource_type}:{self.resource_id}>"
