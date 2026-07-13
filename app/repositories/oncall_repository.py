"""
OnCall repository for Leviia Schedule.

Data access layer for the OnCall model - no business logic, no Flask
request/response handling, just queries.
"""

from datetime import datetime

from sqlalchemy.orm import joinedload

from app import db
from app.models import OnCall


class OnCallRepository:
    """Data access for the OnCall model."""

    @staticmethod
    def get_by_id(oncall_id: int) -> OnCall | None:
        return db.session.get(OnCall, oncall_id)

    @staticmethod
    def list_all_with_user() -> list[OnCall]:
        return (
            OnCall.query.options(joinedload(OnCall.user))
            .order_by(OnCall.start_time)
            .all()
        )

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return (
            OnCall.query.options(joinedload(OnCall.user))
            .order_by(OnCall.start_time)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def list_in_window(window_start: datetime, window_end: datetime) -> list[OnCall]:
        return (
            OnCall.query.options(joinedload(OnCall.user))
            .filter(
                OnCall.start_time <= window_end,
                OnCall.end_time >= window_start,
            )
            .order_by(OnCall.start_time)
            .all()
        )

    @staticmethod
    def list_for_user(user_id: int) -> list[OnCall]:
        return (
            OnCall.query.filter(OnCall.user_id == user_id)
            .order_by(OnCall.start_time)
            .all()
        )

    @staticmethod
    def find_conflict(
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_id: int | None = None,
    ) -> OnCall | None:
        query = OnCall.query.filter(
            OnCall.user_id == user_id,
            OnCall.start_time <= end_time,
            OnCall.end_time >= start_time,
        )
        if exclude_id is not None:
            query = query.filter(OnCall.id != exclude_id)
        return query.first()

    @staticmethod
    def count_all() -> int:
        return OnCall.query.count()

    @staticmethod
    def count_for_user(user_id: int) -> int:
        return OnCall.query.filter_by(user_id=user_id).count()

    @staticmethod
    def exists_for_user(user_id: int) -> bool:
        return OnCall.query.filter_by(user_id=user_id).first() is not None

    @staticmethod
    def list_overlapping_range(start_date, end_date) -> list[OnCall]:
        """Astreintes chevauchant [start_date, end_date] (dates, pas datetimes)."""
        from datetime import datetime, timedelta

        return OnCall.query.filter(
            OnCall.start_time
            < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(start_date, datetime.min.time()),
        ).all()

    @staticmethod
    def delete_overlapping_range(start_date, end_date) -> int:
        oncalls = OnCallRepository.list_overlapping_range(start_date, end_date)
        for oncall in oncalls:
            db.session.delete(oncall)
        return len(oncalls)

    @staticmethod
    def create(user_id: int, start_time: datetime, end_time: datetime) -> OnCall:
        oncall = OnCall(user_id=user_id, start_time=start_time, end_time=end_time)
        db.session.add(oncall)
        return oncall

    @staticmethod
    def delete(oncall: OnCall) -> None:
        db.session.delete(oncall)

    @staticmethod
    def delete_all() -> None:
        OnCall.query.delete(synchronize_session=False)

    @staticmethod
    def delete_for_user(user_id: int) -> None:
        OnCall.query.filter_by(user_id=user_id).delete(synchronize_session=False)
