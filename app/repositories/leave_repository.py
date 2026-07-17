"""
Leave repository for Leviia Schedule.

Data access layer for the Leave model - no business logic, no Flask
request/response handling, just queries.
"""

from datetime import date

from sqlalchemy.orm import joinedload

from app import db
from app.models import Leave


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
    def list_paginated(page: int, per_page: int):
        return (
            Leave.query.options(joinedload(Leave.user))
            .order_by(Leave.start_date)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def list_in_window(window_start: date, window_end: date) -> list[Leave]:
        return (
            Leave.query.options(joinedload(Leave.user))
            .filter(
                Leave.end_date >= window_start,
                Leave.start_date <= window_end,
            )
            .order_by(Leave.start_date)
            .all()
        )

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
