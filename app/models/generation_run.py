"""
GenerationRun model for Kairos.

Record-keeping for AutomationApplyService.apply_plan() (phase 5 of the
automation engine rework) - one row per attempted apply of a
SchedulePlan, whether it succeeded or failed. Not an audit trail
substitute (AuditService.log() is still called separately, after a
successful commit) - this table exists so a support engineer/admin can
correlate "did apply run against a stale plan" (input_fingerprint) and
see exactly why a given apply failed (error_detail), independent of the
general-purpose audit log.
"""

from typing import TYPE_CHECKING, cast

from app import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User

_NOT_PRELOADED = object()


class GenerationRun(BaseModel):
    """
    Attributes:
        start_date/end_date: The period this run's SchedulePlan covered.
        input_fingerprint: SchedulePlan.input_fingerprint (sha256 hex) -
            lets a later investigation confirm whether apply ran
            against a plan computed from stale input.
        outcome: "applied" or "failed" - a plain string, matching this
            codebase's existing convention for planner-adjacent status
            fields (ProposedOnCall.change_type, RuleViolation.severity),
            not a new SQL enum type.
        error_detail: Populated only when outcome != "applied".
        actor_id: Foreign key to User who triggered the apply - nullable,
            same reasoning as AuditLog.actor_id (a future
            automatically-triggered apply, e.g. a cron-driven refresh,
            has no human actor).
    """

    __tablename__ = "generation_runs"

    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    input_fingerprint = db.Column(db.String(64), nullable=False)
    outcome = db.Column(db.String(20), nullable=False, index=True)
    error_detail = db.Column(db.Text, nullable=True)
    actor_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True, index=True
    )

    # Same @property-over-db.relationship() pattern as AuditLog/SwapRequest
    # (see AuditLog's own comment) - avoids the SQLAlchemy 2.0 stub typing
    # issue (RelationshipProperty[Any] without the dedicated mypy plugin).
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
        return (
            f"<GenerationRun {self.start_date}-{self.end_date} "
            f"outcome={self.outcome}>"
        )
