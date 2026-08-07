"""
Dashboard service for Kairos.

Business logic backing /dashboard (app/routes/dashboard_routes.py::user_dashboard()) -
previously queried Shift/OnCall/Leave directly from the route, bypassing
the repository layer entirely; moved here to match this app's routes ->
services -> repositories layering.
"""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models import Leave, OnCall, Shift, ShiftType, User
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.utils.helpers import build_shift_type_color_map


def _month_bounds(today: date) -> tuple[date, date, date, date]:
    """(this_month_start, this_month_end, last_month_start, last_month_end)."""
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    # next month's day-1, minus a day, to get this month's actual last day
    next_month_start = (this_month_start.replace(day=28) + timedelta(days=4)).replace(
        day=1
    )
    this_month_end = next_month_start - timedelta(days=1)
    return this_month_start, this_month_end, last_month_start, last_month_end


def _clipped_days(
    span_start: date, span_end: date, window_start: date, window_end: date
) -> int:
    """Inclusive days of [span_start, span_end] that fall within
    [window_start, window_end] - 0 if there's no overlap. Used to split
    a date-only span (Leave) proportionally across a month boundary
    instead of wholly attributing it to whichever month it starts in."""
    overlap_start = max(span_start, window_start)
    overlap_end = min(span_end, window_end)
    return max(0, (overlap_end - overlap_start).days + 1)


def _clipped_duration_days(
    span_start: datetime, span_end: datetime, window_start: date, window_end: date
) -> float:
    """Fractional-day overlap between a datetime span [span_start,
    span_end] (OnCall - not whole calendar days) and an inclusive
    calendar-day window [window_start, window_end] - same seconds/86400
    unit as the all-time total below, so a month's count can never
    exceed it. Using _clipped_days() (whole inclusive calendar days) on
    an OnCall's .date()-truncated bounds instead of this would
    overcount: e.g. a ~6.4-day on-call (Fri 21:00 -> next Fri 07:00)
    rounds to a total of 6, but its two calendar-day dates are 7 days
    apart, i.e. 8 inclusive days - a real bug caught during this pass."""
    window_start_dt = datetime.combine(window_start, datetime.min.time())
    window_end_dt = datetime.combine(
        window_end + timedelta(days=1), datetime.min.time()
    )
    overlap_start = max(span_start, window_start_dt)
    overlap_end = min(span_end, window_end_dt)
    return max(0.0, (overlap_end - overlap_start).total_seconds() / 86400)


class DashboardService:
    """Supporting business logic for /dashboard."""

    @staticmethod
    def get_stats(user: User) -> dict[str, dict[str, int]]:
        """Day-based counts (not row/event counts) for shifts/on-calls/
        leaves: each with an all-time total, a this-month count, a
        last-month count, and a trend delta (this month - last month).
        "Month" is the full calendar month window, not clipped to
        today - a shift already scheduled later this month still counts
        for "this month" (this month is naturally a mix of past-actual
        and future-scheduled; last month is fully settled - a
        deliberate asymmetry, not an oversight)."""
        today = date.today()
        this_start, this_end, last_start, last_end = _month_bounds(today)

        shift_dates = ShiftRepository.list_dates_for_user(user.id)
        shift_total = len(shift_dates)
        shift_this_month = sum(1 for d in shift_dates if this_start <= d <= this_end)
        shift_last_month = sum(1 for d in shift_dates if last_start <= d <= last_end)

        oncall_spans = OnCallRepository.list_spans_for_user(user.id)
        oncall_total = round(
            sum((end - start).total_seconds() / 86400 for start, end in oncall_spans)
        )
        oncall_this_month = round(
            sum(
                _clipped_duration_days(start, end, this_start, this_end)
                for start, end in oncall_spans
            )
        )
        oncall_last_month = round(
            sum(
                _clipped_duration_days(start, end, last_start, last_end)
                for start, end in oncall_spans
            )
        )

        leave_spans = LeaveRepository.list_spans_for_user(user.id)
        leave_total = sum(
            (end - start).days + 1 for start, end in leave_spans
        )  # same formula as Leave.duration()
        leave_this_month = sum(
            _clipped_days(start, end, this_start, this_end)
            for start, end in leave_spans
        )
        leave_last_month = sum(
            _clipped_days(start, end, last_start, last_end)
            for start, end in leave_spans
        )

        return {
            "shift": {
                "total": shift_total,
                "this_month": shift_this_month,
                "last_month": shift_last_month,
                "trend": shift_this_month - shift_last_month,
            },
            "oncall": {
                "total": oncall_total,
                "this_month": oncall_this_month,
                "last_month": oncall_last_month,
                "trend": oncall_this_month - oncall_last_month,
            },
            "leave": {
                "total": leave_total,
                "this_month": leave_this_month,
                "last_month": leave_last_month,
                "trend": leave_this_month - leave_last_month,
            },
        }

    @staticmethod
    def get_dashboard_data(user: User) -> dict[str, Any]:
        """Everything /dashboard's template needs beyond get_stats()'s
        day-based numbers: upcoming/recent lists and the shift-type
        breakdown chart - moved here from the route as-is (same
        queries), only the direct-model-query-in-a-route layering
        violation is fixed, not the logic itself."""
        now = datetime.now()
        today = date.today()

        upcoming_shifts = (
            Shift.query.options(joinedload(Shift.shift_type))
            .filter(Shift.user_id == user.id, Shift.start_time >= now)
            .order_by(Shift.start_time)
            .limit(5)
            .all()
        )

        upcoming_oncalls = (
            OnCall.query.filter(OnCall.user_id == user.id, OnCall.start_time >= now)
            .order_by(OnCall.start_time)
            .limit(5)
            .all()
        )

        upcoming_leaves = (
            Leave.query.filter(Leave.user_id == user.id, Leave.start_date >= today)
            .order_by(Leave.start_date)
            .limit(5)
            .all()
        )

        recent_shifts = (
            Shift.query.options(joinedload(Shift.shift_type))
            .filter(Shift.user_id == user.id, Shift.end_time <= now)
            .order_by(Shift.end_time.desc())
            .limit(5)
            .all()
        )

        shift_types = ShiftType.query.all()
        # A .count() per shift type (loop) used to run as many queries as
        # there were types - replaced with a single GROUP BY.
        counts_by_type_id = dict(
            db.session.query(Shift.shift_type_id, func.count(Shift.id))
            .filter(Shift.user_id == user.id)
            .group_by(Shift.shift_type_id)
            .all()
        )
        shift_types_stats = [
            {
                "id": shift_type.id,
                "name": shift_type.name,
                "label": shift_type.label,
                "count": counts_by_type_id[shift_type.id],
            }
            for shift_type in shift_types
            if counts_by_type_id.get(shift_type.id, 0) > 0
        ]

        # By rank among the existing types (not by id % palette size),
        # otherwise two types whose IDs differ by a multiple of the
        # palette size end up with the same color.
        shift_type_colors = build_shift_type_color_map(st.id for st in shift_types)

        return {
            "stats": DashboardService.get_stats(user),
            "upcoming_shifts": upcoming_shifts,
            "upcoming_oncalls": upcoming_oncalls,
            "upcoming_leaves": upcoming_leaves,
            "recent_shifts": recent_shifts,
            "shift_types_stats": shift_types_stats,
            "shift_type_colors": shift_type_colors,
        }
