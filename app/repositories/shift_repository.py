"""
Shift and ShiftType repositories for Kairos.

Data access layer for Shift/ShiftType models - no business logic, no
Flask request/response handling, just queries.
"""

from datetime import date, datetime

from sqlalchemy.orm import joinedload

from app import db
from app.models import Shift, ShiftType


class ShiftTypeRepository:
    """Data access for the ShiftType model."""

    @staticmethod
    def get_by_id(shift_type_id: int) -> ShiftType | None:
        return db.session.get(ShiftType, shift_type_id)

    @staticmethod
    def get_all() -> list[ShiftType]:
        return ShiftType.query.order_by(ShiftType.name).all()

    @staticmethod
    def name_taken(name: str, exclude_id: int | None = None) -> bool:
        query = ShiftType.query.filter(ShiftType.name == name)
        if exclude_id is not None:
            query = query.filter(ShiftType.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def create(name: str, label: str, start_hour: int, end_hour: int) -> ShiftType:
        shift_type = ShiftType(
            name=name, label=label, start_hour=start_hour, end_hour=end_hour
        )
        db.session.add(shift_type)
        return shift_type

    @staticmethod
    def delete(shift_type: ShiftType) -> None:
        db.session.delete(shift_type)


class ShiftRepository:
    """Data access for the Shift model."""

    @staticmethod
    def get_by_id(shift_id: int) -> Shift | None:
        return db.session.get(Shift, shift_id)

    @staticmethod
    def list_all_with_user() -> list[Shift]:
        return (
            Shift.query.options(joinedload(Shift.user)).order_by(Shift.start_time).all()
        )

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return (
            Shift.query.options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .order_by(Shift.start_time)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def list_in_window(window_start: datetime, window_end: datetime) -> list[Shift]:
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
    def list_for_user(user_id: int) -> list[Shift]:
        return (
            Shift.query.options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .filter(Shift.user_id == user_id)
            .order_by(Shift.start_time)
            .all()
        )

    @staticmethod
    def find_conflict(
        user_id: int, on_date: date, exclude_id: int | None = None
    ) -> Shift | None:
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
    def count_for_dates(dates: list[date]) -> int:
        return Shift.query.filter(Shift.date.in_(dates)).count()

    @staticmethod
    def exists_for_user(user_id: int) -> bool:
        return Shift.query.filter_by(user_id=user_id).first() is not None

    @staticmethod
    def exists_for_shift_type(shift_type_id: int) -> bool:
        return Shift.query.filter_by(shift_type_id=shift_type_id).first() is not None

    @staticmethod
    def list_in_date_range_with_user(start_date: date, end_date: date) -> list[Shift]:
        return (
            Shift.query.options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .filter(Shift.date >= start_date, Shift.date <= end_date)
            .order_by(Shift.user_id, Shift.start_time)
            .all()
        )

    @staticmethod
    def delete_in_date_range(start_date: date, end_date: date) -> int:
        # synchronize_session="evaluate" (not False, unlike the other
        # delete_* methods below): those never had callers holding an
        # already-loaded Shift instance across the delete, this one can
        # (e.g. a caller that fetched a shift, then deletes its whole
        # range) - "evaluate" keeps any such in-session objects properly
        # expunged/detached instead of raising ObjectDeletedError on
        # next access, at zero extra query cost (evaluated in Python
        # against the identity map, no extra SELECT).
        return Shift.query.filter(
            Shift.date >= start_date, Shift.date <= end_date
        ).delete(synchronize_session="evaluate")

    @staticmethod
    def create(
        user_id: int,
        shift_type_id: int,
        start_time: datetime,
        end_time: datetime,
        on_date: date,
    ) -> Shift:
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
    def delete_for_dates(dates: list[date]) -> None:
        Shift.query.filter(Shift.date.in_(dates)).delete(synchronize_session=False)
