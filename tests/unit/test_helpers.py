"""
Tests for the helper functions (conflict validation).
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift
from app.utils.helpers import (
    _get_overlapping_leave,
    _get_overlapping_oncall,
    _get_overlapping_shift,
    _has_overlapping_oncall,
    build_shift_type_color_map,
    can_add_leave,
    can_add_oncall,
    can_add_shift,
    format_date_fr,
    get_bool,
    get_int,
    is_user_on_leave,
    is_user_on_shift,
)


class TestHelperFunctions:
    """Tests for the internal helper functions."""

    def test_is_user_on_shift_true(self, test_app, test_user, test_shift_type):
        """Test that a user has a shift on a given date."""
        with test_app.app_context():
            # Create a shift for the user
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            result = is_user_on_shift(test_user.id, shift_date)
            assert result is True

    def test_is_user_on_shift_false(self, test_app, test_user):
        """Test that a user has no shift on a given date."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            result = is_user_on_shift(test_user.id, shift_date)
            assert result is False

    def test_is_user_on_leave_true(self, test_app, test_user):
        """Test that a user is on leave on a given date."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Check in the middle of the leave
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 12).date())
            assert result is True

    def test_is_user_on_leave_false(self, test_app, test_user):
        """Test that a user isn't on leave on a given date."""
        with test_app.app_context():
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 1).date())
            assert result is False

    def test_has_overlapping_oncall_true(self, test_app, test_user):
        """Test that a user has an overlapping on-call."""
        with test_app.app_context():
            # Create an existing on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Check the overlap
            new_start = datetime(2023, 12, 2, 10, 0)
            new_end = datetime(2023, 12, 5, 10, 0)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is True

    def test_has_overlapping_oncall_false(self, test_app, test_user):
        """Test that a user has no overlapping on-call."""
        with test_app.app_context():
            # Create an existing on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Check with no overlap
            new_start = datetime(2023, 12, 15, 21, 0)
            new_end = new_start + timedelta(days=7, hours=-14)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is False

    def test_get_overlapping_leave(self, test_app, test_user):
        """Test fetching an overlapping leave."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Look for an overlapping leave
            result = _get_overlapping_leave(
                test_user.id,
                datetime(2023, 12, 12).date(),
                datetime(2023, 12, 14).date(),
            )
            assert result is not None
            assert result.id == leave.id

    def test_get_overlapping_leave_none(self, test_app, test_user):
        """Test that no overlapping leave is found."""
        with test_app.app_context():
            result = _get_overlapping_leave(
                test_user.id, datetime(2023, 12, 1).date(), datetime(2023, 12, 5).date()
            )
            assert result is None


class TestCanAddShift:
    """Tests for can_add_shift."""

    def test_can_add_shift_valid(self, test_app, test_user):
        """Test that a shift can be added on a valid date."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Monday
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert can_add is True

    def test_can_add_shift_weekend_saturday(self, test_app, test_user):
        """Test that a shift can't be added on a Saturday."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 2).date()  # Saturday
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_weekend_sunday(self, test_app, test_user):
        """Test that a shift can't be added on a Sunday."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 3).date()  # Sunday
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_user_on_leave(self, test_app, test_user):
        """Test that a shift can't be added if the user is on leave."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            shift_date = leave.start_date  # Leave start date
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_user_already_has_shift(
        self, test_app, test_user, test_shift_type
    ):
        """Test that a shift can't be added if the user already has one."""
        with test_app.app_context():
            # Create an existing shift
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            shift_date = shift.date
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_multiple_users_same_day(
        self, test_app, test_user, second_user
    ):
        """Test that several users can have shifts on the same day."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Monday

            # Add a shift for the first user
            can_add1 = can_add_shift(test_user, shift_date, "morning")
            assert can_add1 is True

            # Add a shift for the second user on the same day
            can_add2 = can_add_shift(second_user, shift_date, "morning")
            assert can_add2 is True


class TestCanAddOnCall:
    """Tests for can_add_oncall."""

    def test_can_add_oncall_valid(self, test_app, test_user):
        """Test that an on-call can be added on a Friday at 21h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Friday 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert can_add is True

    def test_can_add_oncall_wrong_day_saturday(self, test_app, test_user):
        """Test that an on-call can't be added on a Saturday."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 2, 21, 0)  # Saturday 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_day_monday(self, test_app, test_user):
        """Test that an on-call can't be added on a Monday."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 4, 21, 0)  # Monday 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_hour_20h(self, test_app, test_user):
        """Test that an on-call can't be added at 20h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 20, 0)  # Friday 20h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_hour_22h(self, test_app, test_user):
        """Test that an on-call can't be added at 22h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 22, 0)  # Friday 22h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_user_on_leave(self, test_app, test_user):
        """Test that an on-call can't be added if the user is on leave."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Create an on-call that overlaps the leave
            start_time = datetime(2023, 12, 8, 21, 0)  # Friday before the leave
            end_time = start_time + timedelta(days=7, hours=-14)  # Overlaps the leave
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_overlapping(self, test_app, test_user):
        """Test that an on-call can't be added if it overlaps another."""
        with test_app.app_context():
            # Create an existing on-call
            start_time = datetime(2023, 12, 1, 21, 0)  # Friday 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Try to add an overlapping on-call
            new_start_time = datetime(2023, 12, 1, 21, 0)  # Same date
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, new_start_time, new_end_time)
            assert not can_add

    def test_can_add_oncall_different_users_same_period(
        self, test_app, test_user, second_user
    ):
        """Test that different users can have on-calls in the same period."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Friday 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            # Add an on-call for the first user
            can_add1 = can_add_oncall(test_user, start_time, end_time)
            assert can_add1 is True

            # Add an on-call for the second user in the same period
            can_add2 = can_add_oncall(second_user, start_time, end_time)
            assert can_add2 is True


class TestCanAddLeave:
    """Tests for can_add_leave."""

    def test_can_add_leave_valid(self, test_app, test_user, second_user):
        """Test that a leave can be added over a valid period."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_invalid_dates(self, test_app, test_user):
        """Test that a leave can't be added if the end date is before the start date."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 25).date()
            end_date = datetime(2023, 12, 20).date()  # End date before start date
            can_add = can_add_leave(test_user, start_date, end_date)
            assert not can_add

    def test_can_add_leave_same_day(self, test_app, test_user, second_user):
        """Test that a leave can be added for a single day."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 20).date()
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_overlapping(self, test_app, test_user):
        """Test that a leave can't be added if it overlaps another leave."""
        with test_app.app_context():
            # Create an existing leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            can_add = can_add_leave(test_user, start_date, end_date)
            assert not can_add

    def test_can_add_leave_user_has_shift(
        self, test_app, test_user, second_user, test_shift_type
    ):
        """Test that a leave can be added even if the user has a shift (leaves take priority)."""
        with test_app.app_context():
            # Create a shift
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            start_date = shift.date
            end_date = shift.date + timedelta(days=1)
            can_add = can_add_leave(test_user, start_date, end_date)
            # Leaves take priority, so this must be allowed
            assert can_add is True

    def test_can_add_leave_user_has_oncall(self, test_app, test_user, second_user):
        """Test that a leave can be added even if the user has an on-call (leaves take priority)."""
        with test_app.app_context():
            # Create an on-call
            start_time = datetime(2023, 12, 1, 21, 0)  # Friday 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            start_date = oncall.start_time.date()
            end_date = oncall.end_time.date()
            can_add = can_add_leave(test_user, start_date, end_date)
            # Leaves take priority, so this must be allowed
            assert can_add is True

    def test_can_add_leave_rejected_when_dropping_headcount_to_zero(
        self, test_app, test_user
    ):
        """Rule 6: a leave that would drop the available headcount to 0
        (the only schedule-eligible user) must be rejected."""
        with test_app.app_context():
            # A business-day Wednesday, test_user is the only user in the schedule group
            start_date = date(2023, 12, 20)
            end_date = date(2023, 12, 20)
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is False

    def test_can_add_leave_allowed_when_headcount_stays_above_zero(
        self, test_app, test_user, second_user
    ):
        """Rule 6: with a second schedule-eligible user available, the
        first user's leave remains allowed."""
        with test_app.app_context():
            start_date = date(2023, 12, 20)
            end_date = date(2023, 12, 20)
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_rejected_when_last_remaining_user_takes_leave(
        self, test_app, test_user, second_user
    ):
        """Rule 6: if second_user is already on leave that day, test_user
        (the last one available) can no longer take leave that same day."""
        with test_app.app_context():
            target_date = date(2023, 12, 20)
            existing_leave = Leave(
                user_id=second_user.id, start_date=target_date, end_date=target_date
            )
            db.session.add(existing_leave)
            db.session.commit()

            can_add = can_add_leave(test_user, target_date, target_date)
            assert can_add is False

    def test_can_add_leave_different_users_overlapping(
        self, test_app, test_user, second_user
    ):
        """Test that different users can have overlapping leaves."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()

            # Add a leave for the first user
            can_add1 = can_add_leave(test_user, start_date, end_date)
            assert can_add1 is True

            # Add a leave for the second user in the same period
            can_add2 = can_add_leave(second_user, start_date, end_date)
            assert can_add2 is True


class TestGetBool:
    def test_true_variants(self, monkeypatch):
        for v in ("true", "1", "yes", "y", "on", "TRUE", "On"):
            monkeypatch.setenv("TEST_BOOL", v)
            assert get_bool("TEST_BOOL") is True

    def test_false_variants(self, monkeypatch):
        for v in ("false", "0", "no", "n", "off", "FALSE"):
            monkeypatch.setenv("TEST_BOOL", v)
            assert get_bool("TEST_BOOL") is False

    def test_missing_var_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL_MISSING", raising=False)
        assert get_bool("TEST_BOOL_MISSING", default=True) is True
        assert get_bool("TEST_BOOL_MISSING", default=False) is False

    def test_unrecognized_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "bogus")
        assert get_bool("TEST_BOOL", default=True) is True


class TestGetInt:
    def test_valid_int(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "42")
        assert get_int("TEST_INT") == 42

    def test_missing_var_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_INT_MISSING", raising=False)
        assert get_int("TEST_INT_MISSING", default=7) == 7

    def test_invalid_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "not-a-number")
        assert get_int("TEST_INT", default=99) == 99


class TestFormatFunctions:
    def test_format_date_fr_weekday_abbreviations(self):
        # 2026-07-13 is a Monday
        assert format_date_fr(date(2026, 7, 13)) == "lun. 13/07"
        assert format_date_fr(date(2026, 7, 14)) == "mar. 14/07"
        assert format_date_fr(date(2026, 7, 19)) == "dim. 19/07"

    def test_format_date_fr_datetime(self):
        assert format_date_fr(datetime(2026, 7, 13, 9, 30)) == "lun. 13/07"

    def test_format_date_fr_none(self):
        assert format_date_fr(None) == ""

    def test_format_date_fr_custom_format(self):
        assert format_date_fr(date(2026, 7, 13), "%a %d/%m/%Y") == "lun. 13/07/2026"

    def test_format_date_fr_english_locale(self, test_app):
        from flask_babel import force_locale

        with test_app.app_context(), force_locale("en"):
            assert format_date_fr(date(2026, 7, 13)) == "Mon. 13/07"
            assert format_date_fr(date(2026, 7, 19)) == "Sun. 19/07"


class TestBuildShiftTypeColorMap:
    def test_all_colors_within_palette(self):
        from app.utils.helpers.common_helpers import SHIFT_TYPE_COLOR_PALETTE

        color_map = build_shift_type_color_map([1, 2, 3])
        assert all(c in SHIFT_TYPE_COLOR_PALETTE for c in color_map.values())

    def test_distinct_colors_for_non_contiguous_ids(self):
        """Regression test: a raw modulo on the ID collides two types
        whose IDs differ by a multiple of the palette size (e.g. 2 and 8
        with a 6-entry palette) - rank-based mapping avoids this."""
        from app.utils.helpers.common_helpers import SHIFT_TYPE_COLOR_PALETTE

        n = len(SHIFT_TYPE_COLOR_PALETTE)
        color_map = build_shift_type_color_map([2, 2 + n])
        assert color_map[2] != color_map[2 + n]

    def test_deterministic_for_same_input(self):
        assert build_shift_type_color_map([5, 1, 3]) == build_shift_type_color_map(
            [1, 3, 5]
        )

    def test_wraps_around_palette_beyond_capacity(self):
        from app.utils.helpers.common_helpers import SHIFT_TYPE_COLOR_PALETTE

        n = len(SHIFT_TYPE_COLOR_PALETTE)
        color_map = build_shift_type_color_map(range(1, n + 2))
        ids_sorted = list(range(1, n + 2))
        assert color_map[ids_sorted[0]] == color_map[ids_sorted[-1]]

    def test_ignores_none(self):
        color_map = build_shift_type_color_map([1, None, 2])
        assert None not in color_map

    def test_empty_input(self):
        assert build_shift_type_color_map([]) == {}

    def test_excludes_error_color(self):
        from app.utils.helpers.common_helpers import SHIFT_TYPE_COLOR_PALETTE

        assert "error" not in SHIFT_TYPE_COLOR_PALETTE


class TestOverlappingShiftAndOnCallHelpers:
    def test_get_overlapping_shift_found(self, test_app, test_user, test_shift_type):
        with test_app.app_context():
            shift_date = date(2026, 7, 13)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(shift_date, datetime.min.time()),
                end_time=datetime.combine(shift_date, datetime.max.time()),
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            result = _get_overlapping_shift(
                test_user.id, date(2026, 7, 10), date(2026, 7, 15)
            )
            assert result is not None
            assert result.id == shift.id

    def test_get_overlapping_shift_none(self, test_app, test_user):
        with test_app.app_context():
            result = _get_overlapping_shift(
                test_user.id, date(2026, 7, 10), date(2026, 7, 15)
            )
            assert result is None

    def test_get_overlapping_oncall_found(self, test_app, test_user):
        with test_app.app_context():
            start = datetime(2026, 7, 10, 21, 0)
            end = start + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start, end_time=end)
            db.session.add(oncall)
            db.session.commit()

            result = _get_overlapping_oncall(
                test_user.id, date(2026, 7, 9), date(2026, 7, 16)
            )
            assert result is not None
            assert result.id == oncall.id

    def test_get_overlapping_oncall_none(self, test_app, test_user):
        with test_app.app_context():
            result = _get_overlapping_oncall(
                test_user.id, date(2026, 7, 9), date(2026, 7, 16)
            )
            assert result is None
