"""
Shift and ShiftType repositories for Kairos.

Data access layer for Shift/ShiftType models - no business logic, no
Flask request/response handling, just queries.
"""

from datetime import date, datetime

from sqlalchemy.orm import joinedload

from app import db
from app.models import Shift, ShiftType, User


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
    def list_all_with_user(group_ids: list[int] | None = None) -> list[Shift]:
        query = Shift.query.options(joinedload(Shift.user))
        if group_ids is not None:
            query = query.join(User, Shift.user_id == User.id).filter(
                User.group_id.in_(group_ids)
            )
        return query.order_by(Shift.start_time).all()

    @staticmethod
    def _filtered_query(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type_id: int | None = None,
        ids: list[int] | None = None,
    ):
        """Shared WHERE clause for list_paginated()/delete_filtered() -
        backs the /schedule filter bar (user/group/date range/shift
        type) and the checkbox row-selection ("delete selection" is
        just delete_filtered(ids=[...]), no separate code path). group_id
        is resolved via a User.id subquery, not a join (Shift has no
        group_id column of its own, same as count_for_group()) -
        SQLAlchemy's bulk Query.delete() rejects a query that already
        has a join()/outerjoin() applied ("Can't call Query.update() or
        Query.delete() when join()... has been called"), and this WHERE
        clause is shared with delete_filtered(), so it must stay
        delete()-safe. Same pattern as delete_overlapping_range()."""
        query = Shift.query
        if user_id is not None:
            query = query.filter(Shift.user_id == user_id)
        if group_id is not None:
            group_user_ids = User.query.filter_by(group_id=group_id).with_entities(
                User.id
            )
            query = query.filter(Shift.user_id.in_(group_user_ids))
        if date_from is not None:
            query = query.filter(Shift.date >= date_from)
        if date_to is not None:
            query = query.filter(Shift.date <= date_to)
        if shift_type_id is not None:
            query = query.filter(Shift.shift_type_id == shift_type_id)
        if ids is not None:
            query = query.filter(Shift.id.in_(ids))
        return query

    @staticmethod
    def list_paginated(
        page: int,
        per_page: int,
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type_id: int | None = None,
        ids: list[int] | None = None,
    ):
        return (
            ShiftRepository._filtered_query(
                user_id, group_id, date_from, date_to, shift_type_id, ids
            )
            .options(joinedload(Shift.user), joinedload(Shift.shift_type))
            .order_by(Shift.start_time)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def delete_filtered(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type_id: int | None = None,
        ids: list[int] | None = None,
    ) -> int:
        """Bulk-deletes every Shift matching the given filters (no
        filters = matches everything) - backs /shift/delete-filtered,
        the single action replacing the old delete-all/delete-all-for-
        user/delete-day/delete-week routes. synchronize_session="evaluate"
        (not False, see delete_in_date_range()'s own comment above): a
        caller can hold an already-loaded Shift instance across this call.
        Except when group_id is set: "evaluate" can't reconcile a
        subquery IN-clause against already-loaded session objects in
        Python - "fetch" runs one extra SELECT for matching PKs first
        instead (same as delete_overlapping_range())."""
        sync_mode = "fetch" if group_id is not None else "evaluate"
        return ShiftRepository._filtered_query(
            user_id, group_id, date_from, date_to, shift_type_id, ids
        ).delete(synchronize_session=sync_mode)

    @staticmethod
    def list_in_window(
        window_start: datetime,
        window_end: datetime,
        group_ids: list[int] | None = None,
    ) -> list[Shift]:
        query = Shift.query.options(
            joinedload(Shift.user), joinedload(Shift.shift_type)
        ).filter(
            Shift.start_time >= window_start,
            Shift.start_time <= window_end,
        )
        if group_ids is not None:
            query = query.join(User, Shift.user_id == User.id).filter(
                User.group_id.in_(group_ids)
            )
        return query.order_by(Shift.start_time).all()

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
    def get_day_count_stats(
        user_id: int,
        this_month_start: date,
        this_month_end: date,
        last_month_start: date,
        last_month_end: date,
    ) -> tuple[int, int, int]:
        """(total, this_month, last_month) shift counts for the
        dashboard's day-based stats - one SQL aggregate query (COUNT +
        conditional SUM) instead of fetching every date this user has
        ever had a shift on into Python and counting there. Replaces
        the previous list_dates_for_user() + Python loop, which grew
        unbounded with a user's tenure (one row transferred per shift
        ever assigned, on every /dashboard load). COUNT/SUM/CASE are
        plain portable SQL - no date arithmetic, works identically on
        SQLite/PostgreSQL/MySQL."""
        from sqlalchemy import case, func

        total, this_month, last_month = (
            db.session.query(
                func.count(Shift.id),
                func.sum(
                    case(
                        (
                            Shift.date.between(this_month_start, this_month_end),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            Shift.date.between(last_month_start, last_month_end),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
            .filter(Shift.user_id == user_id)
            .one()
        )
        return total or 0, this_month or 0, last_month or 0

    @staticmethod
    def count_for_group(group_id: int) -> int:
        """Shift has no group_id column of its own - reachable only via
        its owning User."""
        return (
            Shift.query.join(User, Shift.user_id == User.id)
            .filter(User.group_id == group_id)
            .count()
        )

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
    def delete_in_date_range(
        start_date: date, end_date: date, group_id: int | None = None
    ) -> int:
        # synchronize_session="evaluate" (not False, unlike the other
        # delete_* methods below): those never had callers holding an
        # already-loaded Shift instance across the delete, this one can
        # (e.g. a caller that fetched a shift, then deletes its whole
        # range) - "evaluate" keeps any such in-session objects properly
        # expunged/detached instead of raising ObjectDeletedError on
        # next access, at zero extra query cost (evaluated in Python
        # against the identity map, no extra SELECT). group_id (optional,
        # used by AutomationAdminService to scope a per-group regenerate)
        # is resolved via a User.id subquery, not a join - same reason as
        # delete_filtered() above - and forces synchronize_session="fetch"
        # instead, since "evaluate" can't reconcile a subquery IN-clause
        # against already-loaded session objects in Python.
        query = Shift.query.filter(Shift.date >= start_date, Shift.date <= end_date)
        sync_mode = "evaluate"
        if group_id is not None:
            group_user_ids = User.query.filter_by(group_id=group_id).with_entities(
                User.id
            )
            query = query.filter(Shift.user_id.in_(group_user_ids))
            sync_mode = "fetch"
        return query.delete(synchronize_session=sync_mode)

    @staticmethod
    def delete_older_than(cutoff_date: date) -> int:
        """Delete shifts strictly before cutoff_date - used by
        ScheduleCleanupService for the retention-based automatic purge,
        never by anything user-facing (delete_in_date_range above is the
        one every admin-triggered action already uses)."""
        return Shift.query.filter(Shift.date < cutoff_date).delete(
            synchronize_session=False
        )

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
