"""
Shift and ShiftType repositories for Leviia Schedule.

Data access layer for Shift/ShiftType models - no business logic, no
Flask request/response handling, just queries.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app import db
from app.models import Shift, ShiftType


class ShiftTypeRepository:
    """Data access for the ShiftType model."""

    @staticmethod
    def get_by_id(shift_type_id: int) -> Optional[ShiftType]:
        return db.session.get(ShiftType, shift_type_id)

    @staticmethod
    def get_all() -> List[ShiftType]:
        return ShiftType.query.order_by(ShiftType.name).all()


class ShiftRepository:
    """Data access for the Shift model."""

    @staticmethod
    def get_by_id(shift_id: int) -> Optional[Shift]:
        return db.session.get(Shift, shift_id)

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return (
            Shift.query.options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .order_by(Shift.start_time)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def list_in_window(window_start: datetime, window_end: datetime) -> List[Shift]:
        return (
            Shift.query.options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .filter(
                Shift.start_time >= window_start,
                Shift.start_time <= window_end,
            )
            .order_by(Shift.start_time)
            .all()
        )

    @staticmethod
    def list_for_user(user_id: int) -> List[Shift]:
        return (
            Shift.query.options(joinedload(Shift.shift_type))
            .filter(Shift.user_id == user_id)
            .order_by(Shift.start_time)
            .all()
        )

    @staticmethod
    def find_conflict(user_id: int, on_date: date, exclude_id: Optional[int] = None) -> Optional[Shift]:
        query = Shift.query.filter(Shift.user_id == user_id, Shift.date == on_date)
        if exclude_id is not None:
            query = query.filter(Shift.id != exclude_id)
        return query.first()

    @staticmethod
    def count_all() -> int:
        return Shift.query.count()

    @staticmethod
    def count_for_user(user_id: int) -> int:
        return Shift.query.filter_by(user_id=user_id).count()

    @staticmethod
    def count_for_date(on_date: date) -> int:
        return Shift.query.filter_by(date=on_date).count()

    @staticmethod
    def count_for_dates(dates: List[date]) -> int:
        return Shift.query.filter(Shift.date.in_(dates)).count()

    @staticmethod
    def create(user_id: int, shift_type_id: int, start_time: datetime, end_time: datetime, on_date: date) -> Shift:
        shift = Shift(
            user_id=user_id,
            shift_type_id=shift_type_id,
            start_time=start_time,
            end_time=end_time,
            date=on_date,
        )
        db.session.add(shift)
        return shift

    @staticmethod
    def delete(shift: Shift) -> None:
        db.session.delete(shift)

    @staticmethod
    def delete_all() -> None:
        Shift.query.delete(synchronize_session=False)

    @staticmethod
    def delete_for_user(user_id: int) -> None:
        Shift.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    @staticmethod
    def delete_for_date(on_date: date) -> None:
        Shift.query.filter_by(date=on_date).delete(synchronize_session=False)

    @staticmethod
    def delete_for_dates(dates: List[date]) -> None:
        Shift.query.filter(Shift.date.in_(dates)).delete(synchronize_session=False)
