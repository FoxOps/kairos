"""
SwapRequest model for Leviia Schedule.

This module contains the SwapRequest model for shift exchange requests
between users, subject to administrator validation.
"""

from datetime import datetime
from typing import TYPE_CHECKING, cast

from app import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shift import Shift
    from app.models.user import User


class SwapRequest(BaseModel):
    """
    SwapRequest model for tracking shift exchange requests between users.

    A requester proposes to give up one of their shifts (shift_id) to
    target_user, optionally in exchange for one of target_user's shifts
    (target_shift_id) - if target_shift_id is null, it's a one-way
    give-away rather than a reciprocal exchange. An administrator must
    approve the request before the underlying Shift rows are reassigned.

    Attributes:
        requester_id: Foreign key to User - who initiates the request
        shift_id: Foreign key to Shift - the requester's shift being offered
        target_user_id: Foreign key to User - who is being proposed the swap
        target_shift_id: Foreign key to Shift - target's shift offered back
            (nullable - null means a one-way give-away)
        status: One of PENDING, APPROVED, REJECTED, CANCELLED
        reviewed_by_id: Foreign key to User - admin who reviewed the request
        reviewed_at: Timestamp of the admin decision
        admin_comment: Optional comment left by the admin on decision
    """

    __tablename__ = "swap_request"

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

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

    # Pas de db.relationship() ORM ici : ce modèle a 3 FK distinctes vers
    # User (requester/target_user/reviewer) + 2 vers Shift, un cas inédit
    # dans ce repo. Les autres modèles (Leave, Shift, OnCall) n'ont qu'une
    # seule FK vers User et exposent leur relation via un backref déclaré
    # côté User (voir app/models/user.py) - mypy ne l'analyse alors jamais
    # statiquement (attribut dynamique invisible). Une db.relationship()
    # explicite ici serait elle bien vue par mypy, mais typée en dur
    # RelationshipProperty[Any] par les stubs SQLAlchemy 2.0 sans le
    # plugin mypy dédié (non installé dans ce projet) - donc de simples
    # @property suivant le pattern déjà utilisé par
    # User.next_shift/current_oncall (app/models/user.py).
    @property
    def requester(self) -> "User":
        from app.models.user import User

        # requester_id est NOT NULL - cast documente cette garantie FK.
        return cast(User, db.session.get(User, self.requester_id))

    @property
    def target_user(self) -> "User":
        from app.models.user import User

        return cast(User, db.session.get(User, self.target_user_id))

    @property
    def reviewer(self) -> "User | None":
        if self.reviewed_by_id is None:
            return None
        from app.models.user import User

        return db.session.get(User, self.reviewed_by_id)

    @property
    def shift(self) -> "Shift":
        from app.models.shift import Shift

        return cast(Shift, db.session.get(Shift, self.shift_id))

    @property
    def target_shift(self) -> "Shift | None":
        if self.target_shift_id is None:
            return None
        from app.models.shift import Shift

        return db.session.get(Shift, self.target_shift_id)

    def is_pending(self) -> bool:
        """Check if this request is still awaiting an admin decision."""
        return self.status == self.PENDING

    def mark_reviewed(
        self, admin_user_id: int, status: str, comment: str | None = None
    ) -> None:
        """Set the review outcome fields (caller is responsible for commit).

        Args:
            admin_user_id: ID of the admin making the decision
            status: New status (APPROVED or REJECTED)
            comment: Optional comment explaining the decision
        """
        self.status = status
        self.reviewed_by_id = admin_user_id
        self.reviewed_at = datetime.utcnow()
        self.admin_comment = comment

    def __repr__(self) -> str:
        return f"<SwapRequest {self.id} - {self.status} - shift {self.shift_id} -> user {self.target_user_id}>"
