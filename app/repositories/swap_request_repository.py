"""
SwapRequest repository for Leviia Schedule.

Data access layer for the SwapRequest model - no business logic, no Flask
request/response handling, just queries.
"""

from sqlalchemy import or_

from app import db
from app.models import Shift, SwapRequest, User


class SwapRequestRepository:
    """Data access for the SwapRequest model.

    requester/target_user/shift/target_shift are plain @property lookups
    on the model (see app/models/swap_request.py), not ORM relationships -
    no joinedload/eager-loading available here. To avoid turning that into
    an N+1 (4-6 extra queries per row on admin/swaps.html + swaps.html,
    ~240-360 queries on a 30+30 row page), every list_*() method below
    bulk-loads the referenced User/Shift rows and stashes them directly on
    each SwapRequest instance's _cached_* attributes (see
    app/models/swap_request.py) - a plain bulk SELECT whose result isn't
    kept referenced anywhere is not enough on its own, since SQLAlchemy's
    identity map holds weak references and the loaded rows can be garbage
    collected before the properties read them (observed empirically).
    """

    @staticmethod
    def _preload_related(swap_requests: list[SwapRequest]) -> list[SwapRequest]:
        if not swap_requests:
            return swap_requests

        user_ids: set[int] = set()
        shift_ids: set[int] = set()
        for sr in swap_requests:
            user_ids.add(sr.requester_id)
            user_ids.add(sr.target_user_id)
            if sr.reviewed_by_id is not None:
                user_ids.add(sr.reviewed_by_id)
            shift_ids.add(sr.shift_id)
            if sr.target_shift_id is not None:
                shift_ids.add(sr.target_shift_id)

        users_by_id = (
            {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
            if user_ids
            else {}
        )
        shifts_by_id = (
            {s.id: s for s in Shift.query.filter(Shift.id.in_(shift_ids)).all()}
            if shift_ids
            else {}
        )

        for sr in swap_requests:
            sr._cached_requester = users_by_id.get(sr.requester_id)
            sr._cached_target_user = users_by_id.get(sr.target_user_id)
            sr._cached_reviewer = (
                users_by_id.get(sr.reviewed_by_id)
                if sr.reviewed_by_id is not None
                else None
            )
            sr._cached_shift = shifts_by_id.get(sr.shift_id)
            sr._cached_target_shift = (
                shifts_by_id.get(sr.target_shift_id)
                if sr.target_shift_id is not None
                else None
            )

        return swap_requests

    @staticmethod
    def get_by_id(swap_request_id: int) -> SwapRequest | None:
        return db.session.get(SwapRequest, swap_request_id)

    @staticmethod
    def list_pending() -> list[SwapRequest]:
        results = (
            SwapRequest.query.filter(SwapRequest.status == SwapRequest.PENDING)
            .order_by(SwapRequest.created_at)
            .all()
        )
        return SwapRequestRepository._preload_related(results)

    @staticmethod
    def list_for_user(user_id: int) -> list[SwapRequest]:
        """All requests involving user_id, as either requester or target."""
        results = (
            SwapRequest.query.filter(
                or_(
                    SwapRequest.requester_id == user_id,
                    SwapRequest.target_user_id == user_id,
                )
            )
            .order_by(SwapRequest.created_at.desc())
            .all()
        )
        return SwapRequestRepository._preload_related(results)

    @staticmethod
    def list_by_status(status: str) -> list[SwapRequest]:
        results = (
            SwapRequest.query.filter(SwapRequest.status == status)
            .order_by(SwapRequest.created_at.desc())
            .all()
        )
        return SwapRequestRepository._preload_related(results)

    @staticmethod
    def has_pending_for_shift(shift_id: int) -> bool:
        return (
            SwapRequest.query.filter(
                SwapRequest.shift_id == shift_id,
                SwapRequest.status == SwapRequest.PENDING,
            ).first()
            is not None
        )

    @staticmethod
    def create(
        requester_id: int,
        shift_id: int,
        target_user_id: int,
        target_shift_id: int | None = None,
    ) -> SwapRequest:
        swap_request = SwapRequest(
            requester_id=requester_id,
            shift_id=shift_id,
            target_user_id=target_user_id,
            target_shift_id=target_shift_id,
            status=SwapRequest.PENDING,
        )
        db.session.add(swap_request)
        return swap_request

    @staticmethod
    def purge_resolved_for_user(user_id: int) -> int:
        """Delete resolved (non-pending) requests involving user_id (as
        either requester or target). Returns the number deleted. A given
        row can therefore also disappear for the other party involved -
        it's a single shared historical record, not a per-user view."""
        return SwapRequest.query.filter(
            or_(
                SwapRequest.requester_id == user_id,
                SwapRequest.target_user_id == user_id,
            ),
            SwapRequest.status != SwapRequest.PENDING,
        ).delete(synchronize_session=False)

    @staticmethod
    def purge_all_resolved() -> int:
        """Delete all resolved (non-pending) requests, across every user.
        Returns the number deleted."""
        return SwapRequest.query.filter(
            SwapRequest.status != SwapRequest.PENDING
        ).delete(synchronize_session=False)
