"""
OnCall repository for Kairos.

Data access layer for the OnCall model - no business logic, no Flask
request/response handling, just queries.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import joinedload

from app import db
from app.models import OnCall, User


class OnCallRepository:
    """Data access for the OnCall model."""

    @staticmethod
    def get_by_id(oncall_id: int) -> OnCall | None:
        return db.session.get(OnCall, oncall_id)

    @staticmethod
    def list_all_with_user(group_ids: list[int] | None = None) -> list[OnCall]:
        query = OnCall.query.options(joinedload(OnCall.user))
        if group_ids is not None:
            query = query.join(User, OnCall.user_id == User.id).filter(
                User.group_id.in_(group_ids)
            )
        return query.order_by(OnCall.start_time).all()

    @staticmethod
    def _filtered_query(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ids: list[int] | None = None,
    ):
        """Shared WHERE clause for list_paginated()/delete_filtered() -
        backs the /oncall filter bar (user/group/date range) and the
        checkbox row-selection ("delete selection" is just
        delete_filtered(ids=[...]), no separate code path). OnCall is
        a span, not a single day, so date_from/date_to use the same
        "overlap" semantics as list_in_window()/_overlapping_range_filter(),
        just with each bound independently optional. group_id is resolved
        via a User.id subquery, not a join - SQLAlchemy's bulk
        Query.delete() rejects a query that already has a join()/
        outerjoin() applied, and this WHERE clause is shared with
        delete_filtered(), so it must stay delete()-safe. Same pattern
        as delete_overlapping_range()."""
        query = OnCall.query
        if user_id is not None:
            query = query.filter(OnCall.user_id == user_id)
        if group_id is not None:
            group_user_ids = User.query.filter_by(group_id=group_id).with_entities(
                User.id
            )
            query = query.filter(OnCall.user_id.in_(group_user_ids))
        if date_from is not None:
            query = query.filter(
                OnCall.end_time >= datetime.combine(date_from, datetime.min.time())
            )
        if date_to is not None:
            query = query.filter(
                OnCall.start_time
                < datetime.combine(date_to + timedelta(days=1), datetime.min.time())
            )
        if ids is not None:
            query = query.filter(OnCall.id.in_(ids))
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
            OnCallRepository._filtered_query(user_id, group_id, date_from, date_to, ids)
            .options(joinedload(OnCall.user))
            .order_by(OnCall.start_time)
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def delete_filtered(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ids: list[int] | None = None,
    ) -> int:
        """Bulk-deletes every OnCall matching the given filters (no
        filters = matches everything) - backs /oncall/delete-filtered,
        the single action replacing the old delete-all/delete-all-for-
        user routes. synchronize_session="evaluate" (not False, see
        delete_overlapping_range()'s own comment above): a caller can
        hold an already-loaded OnCall instance across this call. Except
        when group_id is set: "evaluate" can't reconcile a subquery
        IN-clause against already-loaded session objects in Python -
        "fetch" runs one extra SELECT for matching PKs first instead."""
        sync_mode = "fetch" if group_id is not None else "evaluate"
        return OnCallRepository._filtered_query(
            user_id, group_id, date_from, date_to, ids
        ).delete(synchronize_session=sync_mode)

    @staticmethod
    def list_in_window(
        window_start: datetime,
        window_end: datetime,
        group_ids: list[int] | None = None,
    ) -> list[OnCall]:
        query = OnCall.query.options(joinedload(OnCall.user)).filter(
            OnCall.start_time <= window_end,
            OnCall.end_time >= window_start,
        )
        if group_ids is not None:
            query = query.join(User, OnCall.user_id == User.id).filter(
                User.group_id.in_(group_ids)
            )
        return query.order_by(OnCall.start_time).all()

    @staticmethod
    def delete_older_than(cutoff: datetime) -> int:
        """Delete on-calls that ended strictly before cutoff - used by
        ScheduleCleanupService for the retention-based automatic purge.
        Keyed on end_time (not start_time): an on-call still in progress
        or only just starting must never be purged just because it
        started long ago in a pathological retention setting."""
        return OnCall.query.filter(OnCall.end_time < cutoff).delete(
            synchronize_session=False
        )

    @staticmethod
    def list_for_user(user_id: int) -> list[OnCall]:
        return (
            OnCall.query.options(joinedload(OnCall.user))
            .filter(OnCall.user_id == user_id)
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
    def list_spans_for_user(user_id: int) -> list[tuple[datetime, datetime]]:
        """Every (start_time, end_time) pair for this user's on-calls -
        columns-only (no joinedload, no full OnCall objects), used by
        the dashboard's day-count stats."""
        return [
            (row.start_time, row.end_time)
            for row in db.session.query(OnCall.start_time, OnCall.end_time)
            .filter(OnCall.user_id == user_id)
            .all()
        ]

    @staticmethod
    def count_for_group(group_id: int) -> int:
        """OnCall has no group_id column of its own - reachable only via
        its owning User."""
        return (
            OnCall.query.join(User, OnCall.user_id == User.id)
            .filter(User.group_id == group_id)
            .count()
        )

    @staticmethod
    def exists_for_user(user_id: int) -> bool:
        return OnCall.query.filter_by(user_id=user_id).first() is not None

    @staticmethod
    def get_starting_at(
        start_time: datetime, group_id: int | None = None
    ) -> OnCall | None:
        """On-call that starts at exactly this instant (used to find the
        upcoming Friday 9pm on-call for notifications). `group_id`: when
        given, only an on-call held by a member of that Group counts -
        used by get_automation_status()'s per-group "next available"
        computation, where more than one group can have a concurrent
        on-call for the same slot in "per_group" scheduling mode."""
        query = OnCall.query.options(joinedload(OnCall.user)).filter(
            OnCall.start_time == start_time
        )
        if group_id is not None:
            query = query.join(User, OnCall.user_id == User.id).filter(
                User.group_id == group_id
            )
        return query.first()

    @staticmethod
    def _overlapping_range_filter(start_date, end_date):
        """Shared WHERE clause for [start_date, end_date] (dates, not
        datetimes) - list_overlapping_range()/delete_overlapping_range()
        below both filter on it, one to fetch rows, one to bulk-delete."""
        from datetime import datetime, timedelta

        return (
            OnCall.start_time
            < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(start_date, datetime.min.time()),
        )

    @staticmethod
    def list_overlapping_range(start_date, end_date) -> list[OnCall]:
        """On-calls overlapping [start_date, end_date] (dates, not datetimes)."""
        return OnCall.query.filter(
            *OnCallRepository._overlapping_range_filter(start_date, end_date)
        ).all()

    @staticmethod
    def delete_overlapping_range(start_date, end_date, group_id=None) -> int:
        # synchronize_session="evaluate": see the identical comment on
        # ShiftRepository.delete_in_date_range() - callers here can hold
        # an already-loaded OnCall instance across the delete. group_id
        # uses a subquery, not a join: SQLAlchemy's bulk delete()
        # rejects a query with join()/outerjoin() already applied
        # ("Can't call Query.update() or Query.delete() when join()...
        # has been called").
        query = OnCall.query.filter(
            *OnCallRepository._overlapping_range_filter(start_date, end_date)
        )
        sync_mode = "evaluate"
        if group_id is not None:
            group_user_ids = User.query.filter_by(group_id=group_id).with_entities(
                User.id
            )
            query = query.filter(OnCall.user_id.in_(group_user_ids))
            # "evaluate" can't reconcile a subquery IN-clause against
            # already-loaded session objects in Python - "fetch" runs
            # one extra SELECT for matching PKs first instead.
            sync_mode = "fetch"
        return query.delete(synchronize_session=sync_mode)

    @staticmethod
    def create(
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        group_id: int | None = None,
    ) -> OnCall:
        oncall = OnCall(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            group_id=group_id,
        )
        db.session.add(oncall)
        return oncall

    @staticmethod
    def delete(oncall: OnCall) -> None:
        db.session.delete(oncall)
