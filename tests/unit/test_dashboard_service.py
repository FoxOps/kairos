"""
Tests for app/services/dashboard_service.py::DashboardService.get_stats() -
day-based counts (not row/event counts) for shifts/on-calls/leaves, each
with an all-time total, a this-month count, a last-month count, and a
trend delta (this month - last month). "Month" boundaries are computed
relative to date.today() at test-run time (no time-freezing anywhere
else in this test suite, matching that convention) rather than
hardcoded literal dates.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift
from app.services.dashboard_service import DashboardService


def _month_bounds(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    next_month_first = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = next_month_first - timedelta(days=1)
    return first, last


class TestDashboardServiceZeroData:
    def test_all_zero_for_a_user_with_no_data(self, test_app, test_user):
        stats = DashboardService.get_stats(test_user)

        for key in ("shift", "oncall", "leave"):
            assert stats[key]["total"] == 0
            assert stats[key]["this_month"] == 0
            assert stats[key]["last_month"] == 0
            assert stats[key]["trend"] == 0


class TestDashboardServiceShiftDays:
    def test_shift_days_total_and_this_month(
        self, test_app, test_user, test_shift_type
    ):
        this_month_first, _ = _month_bounds(date.today())

        for offset in (0, 1, 2):
            d = this_month_first + timedelta(days=offset)
            db.session.add(
                Shift(
                    user_id=test_user.id,
                    shift_type_id=test_shift_type.id,
                    date=d,
                    start_time=datetime.combine(d, datetime.min.time()),
                    end_time=datetime.combine(d, datetime.min.time())
                    + timedelta(hours=8),
                )
            )
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["shift"]["total"] == 3
        assert stats["shift"]["this_month"] == 3
        assert stats["shift"]["last_month"] == 0
        assert stats["shift"]["trend"] == 3

    def test_shift_days_last_month(self, test_app, test_user, test_shift_type):
        this_month_first, _ = _month_bounds(date.today())
        last_month_day = this_month_first - timedelta(days=1)

        db.session.add(
            Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                date=last_month_day,
                start_time=datetime.combine(last_month_day, datetime.min.time()),
                end_time=datetime.combine(last_month_day, datetime.min.time())
                + timedelta(hours=8),
            )
        )
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["shift"]["total"] == 1
        assert stats["shift"]["this_month"] == 0
        assert stats["shift"]["last_month"] == 1
        assert stats["shift"]["trend"] == -1


class TestDashboardServiceOnCallDays:
    def test_oncall_days_rounds_to_whole_day(self, test_app, test_user):
        start = datetime.combine(date.today(), datetime.min.time())
        end = start + timedelta(hours=155)  # 6.458... days
        db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["oncall"]["total"] == 6

    def test_oncall_span_straddling_month_boundary_splits_proportionally(
        self, test_app, test_user
    ):
        this_month_first, _ = _month_bounds(date.today())
        # 4 days before month start -> 3 days into the new month
        # (inclusive day-count: 4 in last month, 3 in this month, 7 total)
        start = datetime.combine(
            this_month_first - timedelta(days=4), datetime.min.time()
        )
        end = datetime.combine(
            this_month_first + timedelta(days=2), datetime.min.time()
        ) + timedelta(hours=23, minutes=59)
        db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["oncall"]["this_month"] == 3
        assert stats["oncall"]["last_month"] == 4

    def test_oncall_this_month_never_exceeds_total_for_a_span_within_one_month(
        self, test_app, test_user
    ):
        """Regression test: this_month/last_month used to sum whole
        inclusive calendar days from .date()-truncated bounds, while
        total summed fractional duration (seconds/86400) - for a
        ~6.4-day span entirely inside one month, this_month (8,
        date-based: 7 days apart + 1 inclusive) could exceed total (6,
        duration-based)."""
        this_month_first, _ = _month_bounds(date.today())
        start = datetime.combine(
            this_month_first + timedelta(days=5), datetime.min.time()
        ) + timedelta(hours=21)
        end = start + timedelta(hours=154)  # ~6.4167 days later, same month

        db.session.add(OnCall(user_id=test_user.id, start_time=start, end_time=end))
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["oncall"]["total"] == 6
        assert stats["oncall"]["this_month"] == 6
        assert stats["oncall"]["this_month"] <= stats["oncall"]["total"]


class TestDashboardServiceLeaveDays:
    def test_leave_days_uses_inclusive_duration(self, test_app, test_user):
        start = date.today()
        end = start + timedelta(days=2)  # 3 inclusive days
        db.session.add(Leave(user_id=test_user.id, start_date=start, end_date=end))
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        assert stats["leave"]["total"] == 3

    def test_leave_span_straddling_month_boundary_splits_proportionally(
        self, test_app, test_user
    ):
        this_month_first, _ = _month_bounds(date.today())
        start = this_month_first - timedelta(days=2)
        end = this_month_first + timedelta(days=1)
        db.session.add(Leave(user_id=test_user.id, start_date=start, end_date=end))
        db.session.commit()

        stats = DashboardService.get_stats(test_user)

        # last month: start_date, start+1 (2 days); this month: month_first,
        # month_first+1 (2 days) - 4 inclusive days total
        assert stats["leave"]["total"] == 4
        assert stats["leave"]["last_month"] == 2
        assert stats["leave"]["this_month"] == 2
