"""
SwapRequest repository for Leviia Schedule.

Data access layer for the SwapRequest model - no business logic, no Flask
request/response handling, just queries.
"""

from sqlalchemy import or_

from app import db
from app.models import SwapRequest


class SwapRequestRepository:
    """Data access for the SwapRequest model.

    requester/target_user/shift/target_shift are plain @property lookups
    on the model (see app/models/swap_request.py), not ORM relationships -
    no joinedload/eager-loading available here, one extra query per access.
    Acceptable at this app's scale (small team scheduling, short lists).
    """

    @staticmethod
    def get_by_id(swap_request_id: int) -> SwapRequest | None:
        return db.session.get(SwapRequest, swap_request_id)

    @staticmethod
    def list_pending() -> list[SwapRequest]:
        return (
            SwapRequest.query.filter(SwapRequest.status == SwapRequest.PENDING)
            .order_by(SwapRequest.created_at)
            .all()
        )

    @staticmethod
    def list_for_user(user_id: int) -> list[SwapRequest]:
        """All requests involving user_id, as either requester or target."""
        return (
            SwapRequest.query.filter(
                or_(
                    SwapRequest.requester_id == user_id,
                    SwapRequest.target_user_id == user_id,
                )
            )
            .order_by(SwapRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def list_by_status(status: str) -> list[SwapRequest]:
        return (
            SwapRequest.query.filter(SwapRequest.status == status)
            .order_by(SwapRequest.created_at.desc())
            .all()
        )

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
    def delete(swap_request: SwapRequest) -> None:
        db.session.delete(swap_request)
