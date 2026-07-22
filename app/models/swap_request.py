"""
SwapRequest model for Kairos.

This module contains the SwapRequest model for shift exchange requests
between users, subject to administrator validation.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from app import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shift import Shift
    from app.models.user import User

# Sentinel distinguishing "never preloaded" from "preloaded but None"
# (e.g. reviewer before an admin decision) - a plain None default
# couldn't tell the two apart.
_NOT_PRELOADED = object()


class SwapRequest(BaseModel):
    """
    SwapRequest model for tracking shift exchange requests between users.

    A requester proposes to give up one of their shifts (shift_id) to
    target_user. The target user must first confirm the request and pick
    which of their own shifts to offer back (target_shift_id) - or decline
    outright - before an administrator gets to approve/reject it. The
    requester never picks target_shift_id themselves anymore: it stays
    null while status is PENDING (awaiting the target's own decision) and
    only gets filled in by SwapService.confirm_swap() at the moment the
    target confirms, together with the status transition to
    AWAITING_ADMIN. If target_shift_id ends up null even after
    confirmation, it's a one-way give-away rather than a reciprocal
    exchange.

    Attributes:
        requester_id: Foreign key to User - who initiates the request
        shift_id: Foreign key to Shift - the requester's shift being offered
        target_user_id: Foreign key to User - who is being proposed the swap
        target_shift_id: Foreign key to Shift - target's shift offered back,
            set by the target at confirmation time, not by the requester at
            creation time (nullable - null means a one-way give-away)
        status: One of PENDING (awaiting target confirmation), AWAITING_ADMIN
            (target confirmed, awaiting admin), APPROVED, REJECTED,
            CANCELLED, REVERTED
        reviewed_by_id: Foreign key to User - who made the final decision
            (an admin for APPROVED/REVERTED, either an admin or the target
            user themselves for REJECTED - see SwapService.target_reject_swap)
        reviewed_at: Timestamp of that decision
        admin_comment: Optional comment left on decision (despite the name,
            also used for the target's own decline reason)
    """

    __tablename__ = "swap_request"

    PENDING = "pending"
    AWAITING_ADMIN = "awaiting_admin"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    REVERTED = "reverted"

    requester_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    shift_id = db.Column(
        db.Integer, db.ForeignKey("shift.id"), nullable=False, index=True
    )
    target_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    target_shift_id = db.Column(
        db.Integer, db.ForeignKey("shift.id"), nullable=True, index=True
    )
    status = db.Column(db.String(20), nullable=False, default=PENDING, index=True)
    reviewed_by_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True, index=True
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    admin_comment = db.Column(db.Text, nullable=True)

    # Composite indexes for frequent "my requests" / "pending queue" lookups
    __table_args__ = (
        db.Index("idx_swap_requester_status", "requester_id", "status"),
        db.Index("idx_swap_target_status", "target_user_id", "status"),
    )

    # No ORM db.relationship() here: this model has 3 distinct FKs to User
    # (requester/target_user/reviewer) + 2 to Shift, a first in this repo.
    # Other models (Leave, Shift, OnCall) only have a single FK to User and
    # expose their relation via a backref declared on the User side (see
    # app/models/user.py) - mypy never statically analyzes that (invisible
    # dynamic attribute). An explicit db.relationship() here would be seen
    # by mypy, but hard-typed as RelationshipProperty[Any] by the
    # SQLAlchemy 2.0 stubs without the dedicated mypy plugin (not installed
    # in this project) - hence plain @property methods that do a
    # db.session.get() on access.
    # Instance-level cache populated by
    # SwapRequestRepository._preload_related() to avoid an N+1 on list
    # views (admin/swaps.html, swaps.html). Needed because SQLAlchemy's
    # identity map holds weak references: a bulk SELECT whose result isn't
    # kept referenced anywhere else can be garbage-collected before these
    # @property methods read it, triggering an individual query despite
    # the preload (non-deterministic, depends on GC timing). Storing the
    # objects here, on the instance itself, guarantees a strong reference
    # for as long as the SwapRequest row stays alive.
    _cached_requester: "User | None | object" = _NOT_PRELOADED
    _cached_target_user: "User | None | object" = _NOT_PRELOADED
    _cached_reviewer: "User | None | object" = _NOT_PRELOADED
    _cached_shift: "Shift | None | object" = _NOT_PRELOADED
    _cached_target_shift: "Shift | None | object" = _NOT_PRELOADED

    @property
    def requester(self) -> "User":
        if self._cached_requester is not _NOT_PRELOADED:
            return cast("User", self._cached_requester)
        from app.models.user import User

        # requester_id is NOT NULL - the cast documents that FK guarantee.
        return cast(User, db.session.get(User, self.requester_id))

    @property
    def target_user(self) -> "User":
        if self._cached_target_user is not _NOT_PRELOADED:
            return cast("User", self._cached_target_user)
        from app.models.user import User

        return cast(User, db.session.get(User, self.target_user_id))

    @property
    def reviewer(self) -> "User | None":
        if self._cached_reviewer is not _NOT_PRELOADED:
            return cast("User | None", self._cached_reviewer)
        if self.reviewed_by_id is None:
            return None
        from app.models.user import User

        return db.session.get(User, self.reviewed_by_id)

    @property
    def shift(self) -> "Shift":
        if self._cached_shift is not _NOT_PRELOADED:
            return cast("Shift", self._cached_shift)
        from app.models.shift import Shift

        return cast(Shift, db.session.get(Shift, self.shift_id))

    @property
    def target_shift(self) -> "Shift | None":
        if self._cached_target_shift is not _NOT_PRELOADED:
            return cast("Shift | None", self._cached_target_shift)
        if self.target_shift_id is None:
            return None
        from app.models.shift import Shift

        return db.session.get(Shift, self.target_shift_id)

    def is_awaiting_target(self) -> bool:
        """Check if this request is still awaiting the target's own
        confirmation, before it even reaches the admin's queue."""
        return self.status == self.PENDING

    def is_awaiting_admin(self) -> bool:
        """Check if the target has confirmed and this is now in the
        admin's queue."""
        return self.status == self.AWAITING_ADMIN

    def is_active(self) -> bool:
        """Check if this request is still unresolved (awaiting either the
        target's confirmation or the admin's decision) - used to gate
        requester-side cancellation and to exclude from purge/"resolved"
        queries."""
        return self.status in (self.PENDING, self.AWAITING_ADMIN)

    def mark_reviewed(
        self, admin_user_id: int, status: str, comment: str | None = None
    ) -> None:
        """Set the review outcome fields (caller is responsible for commit).

        Args:
            admin_user_id: ID of the admin making the decision
            status: New status (APPROVED, REJECTED, or REVERTED)
            comment: Optional comment explaining the decision
        """
        self.status = status
        self.reviewed_by_id = admin_user_id
        self.reviewed_at = datetime.now(timezone.utc)
        self.admin_comment = comment

    def __repr__(self) -> str:
        return f"<SwapRequest {self.id} - {self.status} - shift {self.shift_id} -> user {self.target_user_id}>"
