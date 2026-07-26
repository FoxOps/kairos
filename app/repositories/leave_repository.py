"""
Leave repository for Kairos.

Data access layer for the Leave model - no business logic, no Flask
request/response handling, just queries.
"""

from datetime import date

from sqlalchemy.orm import joinedload

from app import db
from app.models import Leave, User


class LeaveRepository:
    """Data access for the Leave model."""

    @staticmethod
    def get_by_id(leave_id: int) -> Leave | None:
        return db.session.get(Leave, leave_id)

    @staticmethod
    def list_all_with_user() -> list[Leave]:
        return (
            Leave.query.options(joinedload(Leave.user)).order_by(Leave.start_date).all()
        )

    @staticmethod
    def _filtered_query(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ids: list[int] | None = None,
    ):
        """Shared WHERE clause for list_paginated()/list_filtered() -
        backs the /leave filter bar (user/group/date range) and the
        checkbox row-selection ("delete selection" is just
        list_filtered(ids=[...]), no separate code path). Leave is a
        span, not a single day, so date_from/date_to use the same
        "overlap" semantics already established by list_in_window()."""
        query = Leave.query
        if user_id is not None:
            query = query.filter(Leave.user_id == user_id)
        if group_id is not None:
            query = query.join(User, Leave.user_id == User.id).filter(
                User.group_id == group_id
            )
        if date_from is not None:
            query = query.filter(Leave.end_date >= date_from)
        if date_to is not None:
            query = query.filter(Leave.start_date <= date_to)
        if ids is not None:
            query = query.filter(Leave.id.in_(ids))
        return query

    @staticmethod
    def list_paginated(
        page: int,
        per_page: int,
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ids: list[int] | None = None,
    ):
        return (
            LeaveRepository._filtered_query(user_id, group_id, date_from, date_to, ids)
            .options(joinedload(Leave.user))
            .order_by(Leave.start_date)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def list_filtered(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ids: list[int] | None = None,
    ) -> list[Leave]:
        """Every Leave matching the given filters (no filters = matches
        everything), unpaginated - used by LeaveService.delete_filtered(),
        which must loop delete_leave() per row (rebalance side effect),
        not a single bulk SQL DELETE like Shift/OnCall's delete_filtered()."""
        return (
            LeaveRepository._filtered_query(user_id, group_id, date_from, date_to, ids)
            .order_by(Leave.start_date)
            .all()
        )

    @staticmethod
    def list_in_window(
        window_start: date, window_end: date, group_ids: list[int] | None = None
    ) -> list[Leave]:
        query = Leave.query.options(joinedload(Leave.user)).filter(
            Leave.end_date >= window_start,
            Leave.start_date <= window_end,
        )
        if group_ids is not None:
            query = query.join(User, Leave.user_id == User.id).filter(
                User.group_id.in_(group_ids)
            )
        return query.order_by(Leave.start_date).all()

    @staticmethod
    def list_for_user(user_id: int) -> list[Leave]:
        return (
            Leave.query.options(joinedload(Leave.user))
            .filter(Leave.user_id == user_id)
            .order_by(Leave.start_date)
            .all()
        )

    @staticmethod
    def find_conflict(
        user_id: int, start_date: date, end_date: date, exclude_id: int | None = None
    ) -> Leave | None:
        query = Leave.query.filter(
            Leave.user_id == user_id,
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        )
        if exclude_id is not None:
            query = query.filter(Leave.id != exclude_id)
        return query.first()

    @staticmethod
    def count_for_user(user_id: int) -> int:
        return Leave.query.filter_by(user_id=user_id).count()

    @staticmethod
    def list_spans_for_user(user_id: int) -> list[tuple[date, date]]:
        """Every (start_date, end_date) pair for this user's leaves -
        columns-only (no joinedload, no full Leave objects), used by
        the dashboard's day-count stats."""
        return [
            (row.start_date, row.end_date)
            for row in db.session.query(Leave.start_date, Leave.end_date)
            .filter(Leave.user_id == user_id)
            .all()
        ]

    @staticmethod
    def exists_for_user(user_id: int) -> bool:
        return Leave.query.filter_by(user_id=user_id).first() is not None

    @staticmethod
    def create(user_id: int, start_date: date, end_date: date) -> Leave:
        leave = Leave(user_id=user_id, start_date=start_date, end_date=end_date)
        db.session.add(leave)
        return leave

    @staticmethod
    def delete(leave: Leave) -> None:
        db.session.delete(leave)
