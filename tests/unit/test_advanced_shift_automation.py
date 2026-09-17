"""
Tests for the advanced shift automation module.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app import db
from app.models import AutomationConfig, Group, Leave, OnCall, Shift, ShiftType, User
from app.utils.automation import AdvancedShiftAutomation, OnCallAutomation


class TestAdvancedShiftAutomationBasics:
    """Tests for the advanced automation's basic methods."""

    def test_shift_constants(self, test_app):
        """Test that the shift-slot constants are correct."""
        with test_app.app_context():
            assert AdvancedShiftAutomation.SHIFT_07_15 == (7, 15)
            assert AdvancedShiftAutomation.SHIFT_09_17 == (9, 17)
            assert AdvancedShiftAutomation.SHIFT_13_21 == (13, 21)

    def test_get_users_in_schedule_groups(
        self, test_app, test_group, test_user, second_user
    ):
        """Test fetching the users in the schedule groups."""
        with test_app.app_context():
            # test_group has is_part_of_schedule=True by default
            users = AdvancedShiftAutomation.get_users_in_schedule_groups()

            # Should contain test_user and second_user
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids
            assert second_user.id in user_ids

    def test_get_users_in_schedule_groups_excludes_non_schedule(
        self, test_app, test_group, test_user, group_not_in_schedule
    ):
        """Test that users from non-schedule groups are excluded."""
        with test_app.app_context():
            # Create a user in a non-schedule group
            user_not_in_schedule = User(
                name="User Not In Schedule",
                email="notinschedule@test.com",
                password_hash=generate_password_hash("test-password"),
                is_admin=False,
                group_id=group_not_in_schedule.id,
            )
            db.session.add(user_not_in_schedule)
            db.session.commit()

            users = AdvancedShiftAutomation.get_users_in_schedule_groups()
            user_ids = [u.id for u in users]

            assert test_user.id in user_ids
            assert user_not_in_schedule.id not in user_ids

    def test_get_available_users_for_date(
        self, test_app, test_group, test_user, second_user
    ):
        """Test fetching the users available for a date."""
        with test_app.app_context():
            # With no leaves, every user should be available
            test_date = date(2023, 12, 15)
            available_users = AdvancedShiftAutomation.get_available_users_for_date(
                test_date
            )

            user_ids = [u.id for u in available_users]
            assert test_user.id in user_ids
            assert second_user.id in user_ids

    def test_get_available_users_excludes_on_leave(
        self, test_app, test_group, test_user, second_user
    ):
        """Test that users on leave are excluded."""
        with test_app.app_context():
            # Create a leave for test_user
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 10),
                end_date=date(2023, 12, 15),
            )
            db.session.add(leave)
            db.session.commit()

            # Check during the leave
            test_date = date(2023, 12, 12)
            available_users = AdvancedShiftAutomation.get_available_users_for_date(
                test_date
            )

            user_ids = [u.id for u in available_users]
            assert test_user.id not in user_ids
            assert second_user.id in user_ids

    def test_get_oncall_user_for_date(self, test_app, test_user):
        """Test fetching the on-call user for a date."""
        with test_app.app_context():
            # Create an on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Check during the on-call - a weekday (Tuesday), not the
            # weekend: get_oncall_for_date() is anchored to the
            # Monday-Friday shift week (see its docstring), the only
            # real callers (generate_daily_shifts()) never pass weekend
            # dates.
            test_date = date(2023, 12, 5)
            oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(test_date)

            assert oncall_user is not None
            assert oncall_user.id == test_user.id

    def test_get_oncall_user_for_date_no_oncall(self, test_app, test_user):
        """Test that no user is returned when there's no on-call."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(test_date)

            assert oncall_user is None


class TestShiftTypeByHours:
    """Tests for creating shift types by hours."""

    def test_get_shift_type_by_hours_existing(self, test_app, test_shift_type):
        """Test fetching an existing shift type."""
        with test_app.app_context():
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(7, 15)

            assert shift_type is not None
            assert shift_type.start_hour == 7
            assert shift_type.end_hour == 15

    def test_get_shift_type_by_hours_new(self, test_app):
        """Test creating a new shift type."""
        with test_app.app_context():
            # Make sure no 13-21 type exists
            existing = ShiftType.query.filter_by(start_hour=13, end_hour=21).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()

            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(13, 21)

            assert shift_type is not None
            assert shift_type.start_hour == 13
            assert shift_type.end_hour == 21
            assert shift_type.name == "13-21"
            assert shift_type.label == "13h-21h"


class TestGetShiftTypeForSlot:
    """Regression tests for the fix to a pre-existing bug:
    get_shift_type_by_hours() matched ShiftType rows by hours, so an
    admin editing a configured ShiftType's hours via /admin/shift-types
    would silently orphan it (a fresh duplicate got created instead).
    get_shift_type_for_slot() resolves via the configured ShiftSlotsRule
    id instead, closing that gap."""

    def test_default_matches_legacy_hours(self, test_app):
        shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
            AdvancedShiftAutomation.SHIFT_07_15
        )
        assert (shift_type.start_hour, shift_type.end_hour) == (7, 15)

    def test_uses_configured_shift_type_even_with_different_hours(self, test_app):
        from app.models import AutomationRule, ShiftType
        from app.utils.automation.rules import ShiftSlotsRule

        custom = ShiftType(name="custom", label="Custom", start_hour=6, end_hour=14)
        db.session.add(custom)
        db.session.commit()

        default_params = ShiftSlotsRule.resolve()
        AutomationRule.set(
            "shift_slots",
            {**default_params, "rotation_shift_type_id": custom.id},
        )

        shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
            AdvancedShiftAutomation.SHIFT_07_15
        )
        assert shift_type.id == custom.id
        assert (shift_type.start_hour, shift_type.end_hour) == (6, 14)

    def test_falls_back_to_hours_based_lookup_when_configured_id_deleted(
        self, test_app
    ):
        """The configured ShiftType row was deleted outside the normal
        delete-protection guard (e.g. direct DB manipulation) - resolve
        falls back to the historical hours-based fetch-or-create rather
        than crashing."""
        from app.models import AutomationRule, ShiftType
        from app.utils.automation.rules import ShiftSlotsRule

        custom = ShiftType(name="custom2", label="Custom2", start_hour=6, end_hour=14)
        db.session.add(custom)
        db.session.commit()
        custom_id = custom.id

        default_params = ShiftSlotsRule.resolve()
        AutomationRule.set(
            "shift_slots",
            {**default_params, "rotation_shift_type_id": custom_id},
        )

        db.session.delete(custom)
        db.session.commit()

        shift_type = AdvancedShiftAutomation.get_shift_type_for_slot(
            AdvancedShiftAutomation.SHIFT_07_15
        )
        assert shift_type is not None
        assert (shift_type.start_hour, shift_type.end_hour) == (7, 15)


class TestPersistShifts:
    def test_commit_failure_rolls_back_and_returns_error(self, test_app, monkeypatch):
        def _raise():
            raise RuntimeError("boom")

        monkeypatch.setattr(db.session, "commit", _raise)

        shifts, error = AdvancedShiftAutomation._persist_shifts(
            [], dry_run=False, commit=True
        )
        assert shifts == []
        assert error == "boom"


class TestDetermineShiftForUser:
    """Tests for determining a user's shift slot."""

    def test_determine_shift_rotation_after_oncall(
        self, test_app, test_group, test_user
    ):
        """Test rotation: after an on-call, the user should be on 07h-15h."""
        with test_app.app_context():
            # Create an on-call for the previous week
            previous_friday = date(2023, 12, 1)  # Friday
            start_time = datetime.combine(previous_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Check the following week (Monday, after the on-call)
            test_date = date(2023, 12, 11)  # Monday of the following week
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_07_15

    def test_determine_shift_oncall_user_in_schedule(
        self, test_app, test_group, test_user
    ):
        """Test that an on-call user in a schedule group gets the 13h-21h slot."""
        with test_app.app_context():
            # Create an on-call for this week
            friday = date(2023, 12, 1)  # Friday
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Check during the on-call - a weekday (Tuesday): the shift
            # week is Monday-Friday only, see get_oncall_for_date()'s
            # docstring.
            test_date = date(2023, 12, 5)  # Tuesday, within the on-call period
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_13_21

    def test_determine_shift_default(self, test_app, test_group, test_user):
        """Test that the default slot is 09h-17h."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_09_17

    def test_determine_shift_uses_passed_in_oncall_data_without_requerying(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: when oncall_today/oncall_user_last_week are
        supplied by the caller, determine_shift_for_user must not
        re-query OnCall itself. Checked by passing deliberately wrong
        values (inconsistent with the real DB state) and confirming
        those are indeed what drives the decision."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)  # Friday, no real on-call

            # oncall_today mock: test_user is "on call" this day according
            # to the supplied value, even though there's no real on-call
            # in the database for this date.
            fake_oncall = OnCall(
                user_id=test_user.id,
                start_time=datetime.combine(test_date, datetime.min.time()),
                end_time=datetime.combine(test_date, datetime.min.time())
                + timedelta(hours=7),
            )
            tuesday = date(2023, 12, 12)
            fake_oncall.start_time = datetime.combine(tuesday, datetime.min.time())
            fake_oncall.end_time = fake_oncall.start_time + timedelta(hours=7)

            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user,
                tuesday,
                oncall_today=fake_oncall,
                oncall_user_last_week=None,
            )

            # If the method ignored the argument and re-queried the
            # database (where no on-call exists), it would fall back to
            # SHIFT_09_17 (rule 3) instead of SHIFT_13_21 (rule 1).
            assert shift_hours == AdvancedShiftAutomation.SHIFT_13_21

    def test_determine_shift_rotation_before_oncall_next_week(
        self, test_app, test_group, test_user
    ):
        """Symmetric to test_determine_shift_rotation_after_oncall: a user
        who will be on-call *next* week should also get 07h-15h this week,
        not just a user who was on-call last week. Without this, a group
        whose on-call turns are sparse (e.g. shared/pooled across several
        groups) never rotates onto 07h-15h except on the rare week a
        member's on-call already ended - this restores a second, forward-
        looking chance to vary the assignment instead of always falling
        through to the static minimum-coverage fallback."""
        with test_app.app_context():
            next_friday = date(2023, 12, 8)  # Friday, the week after test_date
            start_time = datetime.combine(next_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            test_date = date(2023, 12, 4)  # Monday, the week before the on-call
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_07_15

    def test_determine_shift_transition_friday_outgoing_vs_incoming(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: on the Friday where one on-call ends (7am)
        and the next one starts (9pm), both genuinely overlap that
        calendar day - get_oncall_for_date() used to pick one of the two
        arbitrarily (unordered `.first()` on an interval-overlap query),
        so the wrong person could end up on 1pm-9pm depending on
        implementation-detail row ordering. The correct rule: the
        OUTGOING person (on-call ending that Friday) is on 1pm-9pm - they
        remain "this week's on-call" for shift purposes through their
        last day; the INCOMING person (on-call starting that evening)
        is NOT - shift changes only happen the following Monday, so they
        get whatever the default (9am-5pm) gives, same as the day
        before."""
        with test_app.app_context():
            outgoing_friday = date(2023, 12, 1)  # Friday
            incoming_friday = outgoing_friday + timedelta(days=7)  # next Friday

            outgoing_oncall = OnCall(
                user_id=test_user.id,
                start_time=datetime.combine(
                    outgoing_friday, datetime.min.time()
                ).replace(hour=21),
                end_time=datetime.combine(incoming_friday, datetime.min.time()).replace(
                    hour=7
                ),
            )
            incoming_oncall = OnCall(
                user_id=second_user.id,
                start_time=datetime.combine(
                    incoming_friday, datetime.min.time()
                ).replace(hour=21),
                end_time=datetime.combine(
                    incoming_friday + timedelta(days=7), datetime.min.time()
                ).replace(hour=7),
            )
            db.session.add_all([outgoing_oncall, incoming_oncall])
            db.session.commit()

            outgoing_shift = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, incoming_friday
            )
            incoming_shift = AdvancedShiftAutomation.determine_shift_for_user(
                second_user, incoming_friday
            )

            assert outgoing_shift == AdvancedShiftAutomation.SHIFT_13_21
            assert incoming_shift == AdvancedShiftAutomation.SHIFT_09_17


class TestHandleTwoUsersCase:
    """Tests for the special case with 2 available users."""

    def test_handle_two_users_case_oncall_gets_13_21(
        self, test_app, test_group, test_user, second_user
    ):
        """Test that the on-call user gets 13h-21h."""
        with test_app.app_context():
            # Create an on-call for test_user
            friday = date(2023, 12, 1)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Test with both users available - a weekday (Tuesday): the
            # shift week is Monday-Friday only, see
            # get_oncall_for_date()'s docstring.
            test_date = date(2023, 12, 5)
            available_users = [test_user, second_user]
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            assert len(assignments) == 2
            assert assignments[test_user] == AdvancedShiftAutomation.SHIFT_13_21
            assert assignments[second_user] == AdvancedShiftAutomation.SHIFT_07_15

    def test_handle_two_users_case_no_oncall(
        self, test_app, test_group, test_user, second_user
    ):
        """Test the case with 2 users but no on-call."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            available_users = [test_user, second_user]
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            # With no on-call, per the current logic, both get 07h-15h
            # because the method checks whether oncall_user exists and
            # whether user.id == oncall_user.id. If oncall_user is None,
            # then user.id == oncall_user.id is False and so
            # assignments[user] = SHIFT_07_15
            assert len(assignments) == 2
            assert assignments[test_user] == AdvancedShiftAutomation.SHIFT_07_15
            assert assignments[second_user] == AdvancedShiftAutomation.SHIFT_07_15

    def test_handle_two_users_case_not_two_users(
        self, test_app, test_group, test_user, second_user
    ):
        """Test that the method returns an empty dict when it isn't exactly 2 users."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            available_users = [
                test_user,
                second_user,
                test_user,
            ]  # 3 users (test_user duplicated)
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            assert assignments == {}


class TestGenerateDailyShifts:
    """Tests for the daily shift generation."""

    def test_generate_daily_shifts_weekend(self, test_app):
        """Test that no shift is generated on weekends."""
        with test_app.app_context():
            saturday = date(2023, 12, 2)  # Saturday
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                saturday, dry_run=True
            )

            assert len(shifts) == 0
            assert any("week-end" in msg.lower() for msg in messages)

    def test_generate_daily_shifts_weekend_message_translates_to_english(
        self, test_app
    ):
        """Regression guard: automation messages used to be raw French
        f-strings, never wrapped in _(), so they ignored the acting
        admin's language preference entirely."""
        from flask_babel import force_locale

        with test_app.app_context(), force_locale("en"):
            saturday = date(2023, 12, 2)  # Saturday
            _shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                saturday, dry_run=True
            )

            assert any("weekend" in msg.lower() for msg in messages)
            assert not any("week-end" in msg.lower() for msg in messages)

    def test_generate_daily_shifts_no_available_users(self, test_app, test_group):
        """Test that no shift is generated when no user is available."""
        with test_app.app_context():
            # Create a leave for every user
            users = User.query.all()
            for user in users:
                leave = Leave(
                    user_id=user.id,
                    start_date=date(2023, 12, 15),
                    end_date=date(2023, 12, 20),
                )
                db.session.add(leave)
            db.session.commit()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 0
            assert any("disponible" in msg.lower() for msg in messages)

    def test_generate_daily_shifts_with_one_user(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: with a single person available (the other
        one is on leave), that person must land directly on 07h-15h
        (rule 7: 7am-3pm minimum coverage - even in this degraded,
        1-person case)."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            leave = Leave(
                user_id=second_user.id,
                start_date=test_date,
                end_date=test_date,
            )
            db.session.add(leave)
            db.session.commit()

            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 1
            assert shifts[0].user_id == test_user.id
            assert shifts[0].start_time.hour == 7
            assert shifts[0].end_time.hour == 15

    def test_generate_daily_shifts_one_user_commit_failure(
        self, test_app, test_group, test_user, second_user, monkeypatch
    ):
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            leave = Leave(
                user_id=second_user.id, start_date=test_date, end_date=test_date
            )
            db.session.add(leave)
            db.session.commit()

            monkeypatch.setattr(
                db.session,
                "commit",
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            )

            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=False
            )
            assert shifts == []
            assert any("[ERROR]" in m for m in messages)

    def test_generate_daily_shifts_honors_configured_rotation_shift_type(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test for the ShiftType-by-hours orphan bug fix:
        when the rotation slot (rule 7's 07h-15h fallback) is
        overridden to point at a ShiftType with different hours, the
        generated shift must use THAT ShiftType's actual hours, not
        the legacy 7-15 literal."""
        from app.models import AutomationRule, ShiftType
        from app.utils.automation.rules import ShiftSlotsRule

        with test_app.app_context():
            custom = ShiftType(
                name="custom-rotation", label="Custom", start_hour=6, end_hour=14
            )
            db.session.add(custom)
            db.session.commit()

            default_params = ShiftSlotsRule.resolve()
            AutomationRule.set(
                "shift_slots",
                {**default_params, "rotation_shift_type_id": custom.id},
            )

            test_date = date(2023, 12, 15)
            leave = Leave(
                user_id=second_user.id, start_date=test_date, end_date=test_date
            )
            db.session.add(leave)
            db.session.commit()

            shifts, _messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 1
            assert shifts[0].shift_type_id == custom.id
            assert shifts[0].start_time.hour == 6
            assert shifts[0].end_time.hour == 14

    def test_generate_daily_shifts_with_two_users(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        """Test generation with exactly 2 available users."""
        with test_app.app_context():
            # Make sure only these two users are in the schedule group
            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Should generate shifts for both users
            assert len(shifts) == 2
            assert any(test_user.id == s.user_id for s in shifts)
            assert any(second_user.id == s.user_id for s in shifts)

    def test_generate_daily_shifts_two_users_commit_failure(
        self, test_app, test_group, test_user, second_user, test_shift_type, monkeypatch
    ):
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            monkeypatch.setattr(
                db.session,
                "commit",
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            )

            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=False
            )
            assert shifts == []
            assert any("[ERROR]" in m for m in messages)

    def test_generate_daily_shifts_with_three_users(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generation with 3 available users."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Should generate shifts for all 3 users
            assert len(shifts) == 3

    def test_generate_daily_shifts_three_plus_users_commit_failure(
        self, test_app, test_group, test_user, second_user, monkeypatch
    ):
        with test_app.app_context():
            user3 = User(
                name="Third User Commit",
                email="third-commit@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            test_date = date(2023, 12, 15)
            monkeypatch.setattr(
                db.session,
                "commit",
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            )

            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=False
            )
            assert shifts == []
            assert any("[ERROR]" in m for m in messages)

    def test_generate_daily_shifts_no_shifts_generated_warns(
        self, test_app, test_group, test_user, second_user, monkeypatch
    ):
        """generated_shifts stays empty for the 3+-users path despite
        real available users - structurally only reachable if
        schedule_users diverges from available_users between the two
        get_users_in_schedule_groups() calls inside this code path (an
        invariant that always holds in practice, since both derive from
        the same query), so forced here via a second-call override."""
        user3 = User(
            name="Third User Warn",
            email="third-warn@test.com",
            password_hash=generate_password_hash("third-password"),
            is_admin=False,
            group_id=test_group.id,
        )
        db.session.add(user3)
        db.session.commit()

        test_date = date(2023, 12, 15)
        real_get_users = AdvancedShiftAutomation.get_users_in_schedule_groups
        calls = {"n": 0}

        def flaky_get_users(group=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return real_get_users(group=group)
            return []

        monkeypatch.setattr(
            AdvancedShiftAutomation, "get_users_in_schedule_groups", flaky_get_users
        )

        shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
            test_date, dry_run=True
        )
        assert shifts == []
        assert any("[WARN]" in m and "Aucun shift" in m for m in messages)

    def test_no_shifts_generated_on_a_weekend_flags_skip(
        self, test_app, test_group, test_user, second_user, monkeypatch
    ):
        """The "elif WeekendDefinitionRule.is_weekend(...)" branch right
        after the empty-generated_shifts check - structurally
        unreachable via any real weekday/weekend combination, since a
        real weekend is already filtered out by this same method's own
        early check a few lines above (before even fetching available
        users). Forced here via a call-counter so the top check sees
        "not weekend" but this later check sees "weekend"."""
        from app.utils.automation.rules import WeekendDefinitionRule

        user3 = User(
            name="Third User Weekend",
            email="third-weekend@test.com",
            password_hash=generate_password_hash("third-password"),
            is_admin=False,
            group_id=test_group.id,
        )
        db.session.add(user3)
        db.session.commit()

        test_date = date(2023, 12, 15)
        calls = {"n": 0}

        def flaky_is_weekend(d, group=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return False
            return True

        monkeypatch.setattr(WeekendDefinitionRule, "is_weekend", flaky_is_weekend)

        real_get_users = AdvancedShiftAutomation.get_users_in_schedule_groups
        user_calls = {"n": 0}

        def flaky_get_users(group=None):
            user_calls["n"] += 1
            if user_calls["n"] == 1:
                return real_get_users(group=group)
            return []

        monkeypatch.setattr(
            AdvancedShiftAutomation, "get_users_in_schedule_groups", flaky_get_users
        )

        shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
            test_date, dry_run=True
        )
        assert shifts == []
        assert any("[SKIP]" in m and "week-end" in m for m in messages)

    def test_generate_daily_shifts_ensures_07_15_coverage_with_three_users(
        self, test_app, test_group, test_user, second_user
    ):
        """Rule 7 regression test: with 3+ users and no on-call context at
        all (neither this week's nor last week's on-call is set), rules
        1/2 never fire for anyone and rule 3 alone would put everyone on
        09h-17h - leaving 07h-09h/17h-21h uncovered. At least one person
        must still land on 07h-15h."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 3
            assert any(
                shift.start_time.hour == 7 and shift.end_time.hour == 15
                for shift in shifts
            )

    def test_generate_daily_shifts_07_15_fallback_honors_rotation_order(
        self, test_app, test_group, test_user, second_user
    ):
        """The rule 7 fallback picks the first available user in the
        configured rotation order, not an arbitrary/incidental one."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            AutomationConfig.set_rotation_order(
                [user3.id, second_user.id, test_user.id]
            )

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 3
            covering_07_15 = [
                shift
                for shift in shifts
                if shift.start_time.hour == 7 and shift.end_time.hour == 15
            ]
            assert len(covering_07_15) == 1
            assert covering_07_15[0].user_id == user3.id

    def test_generate_daily_shifts_07_15_fallback_rotates_across_weeks(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: the rule 7 fallback must not pick the same
        person every time it triggers - it should rotate week over week,
        same as every other rule in this engine. Without this, a group
        whose on-call turns are sparse (no natural rule 1/2 match for
        weeks at a time) would see the identical person parked on
        7am-3pm indefinitely, and everyone else frozen on 9am-5pm - the
        exact "no rotation between weeks" bug this test guards against."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            AutomationConfig.set_rotation_order(
                [user3.id, second_user.id, test_user.id]
            )

            def fallback_user_id(test_date):
                shifts, _messages = AdvancedShiftAutomation.generate_daily_shifts(
                    test_date, dry_run=True
                )
                covering_07_15 = [
                    shift
                    for shift in shifts
                    if shift.start_time.hour == 7 and shift.end_time.hour == 15
                ]
                assert len(covering_07_15) == 1
                return covering_07_15[0].user_id

            week1 = date(2023, 12, 15)  # Friday
            week2 = week1 + timedelta(days=7)
            week3 = week1 + timedelta(days=14)

            picks = {
                fallback_user_id(week1),
                fallback_user_id(week2),
                fallback_user_id(week3),
            }
            # 3 users in rotation, 3 consecutive weeks -> all 3 must
            # appear, not the same one every time.
            assert picks == {user3.id, second_user.id, test_user.id}

    def test_generate_daily_shifts_dry_run_no_commit(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test that dry_run=True doesn't commit the changes."""
        with test_app.app_context():
            # Count the existing shifts
            initial_count = Shift.query.count()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Check that no shift was added to the database
            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_generate_daily_shifts_with_commit(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test that dry_run=False commits the changes."""
        with test_app.app_context():
            # Count the existing shifts
            initial_count = Shift.query.count()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=False
            )

            # Check that the shifts were added
            final_count = Shift.query.count()
            assert final_count > initial_count


class TestGenerateFullSchedule:
    """Tests for the full schedule generation."""

    def test_generate_full_schedule_single_day(self, test_app, test_group, test_user):
        """Test generation for a single day."""
        with test_app.app_context():
            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 15)
            shifts, messages, _unfilled_shifts = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=True
                )
            )

            assert len(shifts) > 0

    def test_generate_full_schedule_multiple_days(
        self, test_app, test_group, test_user
    ):
        """Test generation over several days."""
        with test_app.app_context():
            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages, _unfilled_shifts = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=True
                )
            )

            # Should generate shifts for every business day
            # 15, 16, 17, 18, 19, 20 = 6 days (Monday to Friday + Saturday)
            # But only Monday through Friday
            workdays = [
                d
                for d in range((end_date - start_date).days + 1)
                if (start_date + timedelta(days=d)).weekday() < 5
            ]
            assert (
                len(shifts)
                == len(workdays)
                * User.query.join(Group).filter(Group.is_part_of_schedule).count()
            )

    def test_generate_full_schedule_dry_run(self, test_app, test_group, test_user):
        """Test that dry_run=True doesn't commit."""
        with test_app.app_context():
            initial_count = Shift.query.count()

            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages, _unfilled_shifts = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=True
                )
            )

            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_generate_full_schedule_with_commit(self, test_app, test_group, test_user):
        """Test that dry_run=False commits the changes."""
        with test_app.app_context():
            initial_count = Shift.query.count()

            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages, _unfilled_shifts = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=False
                )
            )

            final_count = Shift.query.count()
            assert final_count > initial_count


class TestRebalanceAfterLeave:
    """Tests for rebalancing after adding a leave."""

    def test_rebalance_after_leave_does_not_duplicate_adjacent_oncalls(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: the period regenerated after a leave is
        extended by ±30 days (padding) around the affected Fridays, and
        can therefore include on-calls for OTHER Fridays already
        assigned to other users. The old code only removed the leave
        owner's own on-calls (leave.user_id) before regenerating across
        the whole extended period, creating duplicate on-calls on
        adjacent Fridays unrelated to the leave."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            friday_before = date(2023, 12, 1)
            friday_leave = date(2023, 12, 8)
            friday_after = date(2023, 12, 15)

            def make_oncall(user_id, friday):
                start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
                end = start + timedelta(days=7, hours=-14)
                return OnCall(user_id=user_id, start_time=start, end_time=end)

            db.session.add(make_oncall(test_user.id, friday_before))
            db.session.add(make_oncall(second_user.id, friday_leave))
            db.session.add(make_oncall(user3.id, friday_after))
            db.session.commit()

            # second_user goes on leave during their own on-call week
            leave = Leave(
                user_id=second_user.id,
                start_date=date(2023, 12, 10),
                end_date=date(2023, 12, 11),
            )
            db.session.add(leave)
            db.session.commit()

            AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            for friday in (friday_before, friday_leave, friday_after):
                day_start = datetime.combine(friday, datetime.min.time())
                count = OnCall.query.filter(
                    OnCall.start_time == day_start.replace(hour=21)
                ).count()
                assert count == 1, (
                    f"{count} on-calls found for Friday {friday} "
                    "(expected duplicate absent with the fix)"
                )

    def test_rebalance_after_leave_dry_run(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test rebalancing in dry_run mode."""
        with test_app.app_context():
            # Create a leave
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 15),
                end_date=date(2023, 12, 20),
            )
            db.session.add(leave)
            db.session.commit()

            # Count the initial shifts
            initial_count = Shift.query.count()

            # Run the rebalance in dry_run
            shifts, messages, _unfilled, _failed, _failed_oncall, _unfilled_shifts = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=True)
            )

            # No change should be committed
            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_rebalance_after_leave_dry_run_reports_deleted_shifts(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """dry_run's own "[DELETED] N shifts" flash - needs a
        pre-existing shift on one of the rebalanced days, unlike
        test_rebalance_after_leave_dry_run above (no pre-existing
        shifts there)."""
        with test_app.app_context():
            leave_date = date(2023, 12, 15)
            existing_shift = Shift(
                date=leave_date,
                start_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=15
                ),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(existing_shift)
            leave = Leave(
                user_id=test_user.id, start_date=leave_date, end_date=leave_date
            )
            db.session.add(leave)
            db.session.commit()

            _shifts, messages, *_rest = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )
            assert any("[DELETED]" in m for m in messages)

    def test_rebalance_after_leave_deletes_existing_shifts(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Same as above, non-dry-run: existing shifts on a rebalanced
        day actually get deleted inside the per-day SAVEPOINT."""
        with test_app.app_context():
            leave_date = date(2023, 12, 15)
            existing_shift = Shift(
                date=leave_date,
                start_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=15
                ),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(existing_shift)
            leave = Leave(
                user_id=test_user.id, start_date=leave_date, end_date=leave_date
            )
            db.session.add(leave)
            db.session.commit()
            existing_shift_id = existing_shift.id

            _shifts, messages, *_rest = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=False
            )
            assert any("[DELETED]" in m for m in messages)
            assert db.session.get(Shift, existing_shift_id) is None

    def test_rebalance_after_leave_with_oncall(self, test_app, test_group, test_user):
        """Test rebalancing with an overlapping on-call."""
        with test_app.app_context():
            # Create an on-call
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            # Create a leave that overlaps the on-call
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            # Run the rebalance
            shifts, messages, _unfilled, _failed, _failed_oncall, _unfilled_shifts = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=True)
            )

            # Should mention the removal of the on-call or shifts
            # The message can be in French or English
            assert any(
                "astreinte" in msg.lower()
                or "supprim" in msg.lower()
                or "shift" in msg.lower()
                or "delete" in msg.lower()
                or "removed" in msg.lower()
                for msg in messages
            )

    def test_rebalance_after_leave_uses_configured_rotation_order(
        self, test_app, test_group, test_user, second_user
    ):
        """Rebalancing must honor the configured rotation order
        (AutomationConfig) instead of falling back to alphabetical order
        (a hardcoded rotation_order_ids=None was a bug, now fixed)."""
        with test_app.app_context():
            AutomationConfig.set_rotation_order([second_user.id, test_user.id])

            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            with patch(
                "app.utils.automation.OnCallAutomation.generate_oncall_schedule",
                wraps=OnCallAutomation.generate_oncall_schedule,
            ) as mocked_generate:
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            assert mocked_generate.call_args.kwargs["rotation_order_ids"] == [
                second_user.id,
                test_user.id,
            ]

    def test_rebalance_after_leave_does_not_lock_out_window_on_future_oncalls(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test for a real production incident: rebalance_
        after_leave() only regenerates a ±30-day window around the
        leave, leaving on-calls *outside* that window (including ones
        further in the future than the window itself) untouched. A
        version of AvailabilityIndex/meets_spacing_constraint that only
        tracked "the single most recently created on-call" per user
        (rather than checking every known interval, both before and
        after) would treat one of those future on-calls as if it were
        the immediately preceding one - computing a nonsensical
        negative gap that failed the 2-week spacing check for every
        candidate on every week of the whole window, even with zero
        real leave conflicts. Confirmed against a real deployment's
        data (4 eligible users, one mid-window leave) before this fix:
        100% of the window (12/12 weeks) came back unfilled."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            user4 = User(
                name="Fourth User",
                email="fourth@test.com",
                password_hash="fourth123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add_all([user3, user4])
            db.session.commit()

            rotation_order = [test_user.id, second_user.id, user3.id, user4.id]
            AutomationConfig.set_rotation_order(rotation_order)

            # A clean, conflict-free schedule already exists across a
            # wide span - crucially including on-calls *after* the leave
            # below's ±30-day rebalance window, left untouched by it.
            OnCallAutomation.generate_oncall_schedule(
                date(2023, 11, 3),
                date(2024, 5, 31),
                rotation_order_ids=rotation_order,
                dry_run=False,
                commit=True,
            )

            # Leave roughly in the middle of that schedule - its own
            # ±30-day rebalance window won't reach the tail end of the
            # existing future on-calls, which is exactly the scenario
            # that exposed the bug (on-calls existing *after* the
            # window, not just before it).
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 18),
            )
            db.session.add(leave)
            db.session.commit()

            (
                _shifts,
                _messages,
                unfilled_oncall_dates,
                _failed,
                _failed_oncall,
                _unfilled_shifts,
            ) = AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            assert unfilled_oncall_dates == []

    def test_rebalance_after_leave_preserves_unaffected_weeks(
        self, test_app, test_group, test_user, second_user
    ):
        """Real user report: automatic rebalances after a leave
        reshuffled weeks that had nothing to do with the leave, slowly
        drifting the rotation over many successive leaves. The
        rebalance's on-call regeneration now prefers keeping each
        week's existing occupant (captured before the window is wiped)
        over blindly replaying the rotation order.

        With ample rotation slack (6 users here), replacing the single
        leave-affected week's occupant doesn't force a legal-spacing
        cascade onto any other week (unlike a tight 3-4 user pool,
        where the replacement candidate's own nearby slot can collide -
        a real, expected reshuffle in that case, not a bug - see
        TestOnCallMaxFillSearch for that scenario). So here every other
        week in the window must come out exactly as it went in."""
        with test_app.app_context():
            extra_users = []
            for i in range(4):
                u = User(
                    name=f"Extra User {i}",
                    email=f"extra{i}@test.com",
                    password_hash="extra123",
                    is_admin=False,
                    group_id=test_group.id,
                )
                db.session.add(u)
                extra_users.append(u)
            db.session.commit()

            rotation_order = [test_user.id, second_user.id] + [
                u.id for u in extra_users
            ]
            AutomationConfig.set_rotation_order(rotation_order)

            OnCallAutomation.generate_oncall_schedule(
                date(2023, 11, 3),
                date(2024, 3, 1),
                rotation_order_ids=rotation_order,
                dry_run=False,
                commit=True,
            )

            before = {
                oc.start_time.date(): oc.user_id
                for oc in OnCall.query.filter(
                    OnCall.start_time >= datetime(2023, 12, 1),
                    OnCall.start_time <= datetime(2024, 2, 1),
                ).all()
            }

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 5),
            )
            db.session.add(leave)
            db.session.commit()

            AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            after = {
                oc.start_time.date(): oc.user_id
                for oc in OnCall.query.filter(
                    OnCall.start_time >= datetime(2023, 12, 1),
                    OnCall.start_time <= datetime(2024, 2, 1),
                ).all()
            }

            # Every week except the one whose occupant went on leave
            # must be completely unchanged. The leave (Jan 3-5, a
            # Wed-Fri) overlaps the on-call that *started* the
            # previous Friday (Dec 29 21h -> Jan 5 07h), not the
            # calendar week the leave dates themselves fall in.
            leave_week = date(2023, 12, 29)
            unchanged_weeks = {d: u for d, u in before.items() if d != leave_week}
            for friday, user_id in unchanged_weeks.items():
                assert after.get(friday) == user_id, (
                    f"week {friday} changed from {user_id} to "
                    f"{after.get(friday)} despite no conflict"
                )

    def test_rebalance_after_leave_no_overlap(self, test_app, test_group, test_user):
        """Test rebalancing with a leave that overlaps nothing."""
        with test_app.app_context():
            # Create a leave in the future with no overlap
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 5),
            )
            db.session.add(leave)
            db.session.commit()

            shifts, messages, _unfilled, _failed, _failed_oncall, _unfilled_shifts = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=True)
            )

            # Should generate messages but no deletion
            assert len(messages) > 0

    def test_rebalance_after_leave_isolates_oncall_regen_failure_from_shifts(
        self, test_app, test_group, test_user, second_user
    ):
        """Bug hunt: the on-call regeneration section runs in its own
        SAVEPOINT (see rebalance_after_leave's docstring) - a failure
        there must no longer discard the shifts already regenerated by
        the day loop above it, and must no longer raise (the caller,
        LeaveService, can't distinguish 'total failure' from 'partial
        success with a flagged gap' if this still raised). Superseded
        the old test_rebalance_after_leave_rolls_back_fully_on_failure,
        which asserted the opposite (full rollback, exception
        propagated) - that was the bug being fixed here, not a
        contract worth preserving."""
        with test_app.app_context():
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            shift_count_before = Shift.query.count()

            with patch(
                "app.utils.automation.OnCallAutomation.generate_oncall_schedule",
                side_effect=RuntimeError("boom"),
            ):
                (
                    _shifts,
                    messages,
                    _unfilled,
                    _failed,
                    failed_oncall_period,
                    _unfilled_shifts,
                ) = AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            # No exception propagated - the failure is reported, not raised.
            assert len(failed_oncall_period) == 2
            assert any("astreintes" in m.lower() for m in messages)
            # The shifts regenerated by the day loop still got committed
            # despite the on-call section failing afterward.
            assert Shift.query.count() > shift_count_before
            # The leave owner's own on-call was still removed (correct:
            # they're on leave) - just never replaced, a gap flagged for
            # manual admin action rather than silently left stale.
            assert (
                OnCall.query.filter_by(
                    user_id=test_user.id, start_time=start_time
                ).first()
                is None
            )

    def test_rebalance_after_leave_isolates_one_failing_shift_day(
        self, test_app, test_group, test_user, second_user
    ):
        """The core bug report this fix addresses: a failure regenerating
        ONE day's shifts inside the ±30-day window must not wipe out
        every other day already regenerated in the same window - only
        that one day is left unfilled/unchanged and flagged in
        failed_shift_dates, the rest of the window still gets its
        shifts."""
        with test_app.app_context():
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            failing_day = date(2023, 12, 20)
            real_generate_daily_shifts = AdvancedShiftAutomation.generate_daily_shifts

            def flaky_generate_daily_shifts(target_date, *args, **kwargs):
                if target_date == failing_day:
                    raise RuntimeError("boom")
                return real_generate_daily_shifts(target_date, *args, **kwargs)

            with patch.object(
                AdvancedShiftAutomation,
                "generate_daily_shifts",
                side_effect=flaky_generate_daily_shifts,
            ):
                (
                    _shifts,
                    messages,
                    _unfilled,
                    failed_shift_dates,
                    _failed_oncall,
                    _unfilled_shifts,
                ) = AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            assert failed_shift_dates == [failing_day]
            assert any(
                failing_day.strftime("%d/%m/%Y") in m and "[ERROR]" in m
                for m in messages
            )
            # Every other weekday in the window still got a shift - the
            # single failing day didn't take the rest down with it.
            other_weekday = date(2023, 12, 19)  # Tuesday, in the same window
            assert Shift.query.filter_by(date=other_weekday).first() is not None
            # The failing day itself was left exactly as it was before
            # the attempt (no partially-written shift for it either).
            assert Shift.query.filter_by(date=failing_day).count() == 0

    def test_rebalance_after_leave_commits_once_on_success(
        self, test_app, test_group, test_user, second_user
    ):
        """A successful rebalance (dry_run=False) must actually persist
        the regenerated on-calls and shifts (a single final commit, no
        lost intermediate commits)."""
        with test_app.app_context():
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            (
                regenerated_shifts,
                messages,
                _unfilled,
                _failed,
                _failed_oncall,
                _unfilled_shifts,
            ) = AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            # test_user's old on-call for this period was indeed deleted
            # and that deletion persisted (not just flush()'d then lost
            # for lack of a commit). Checked on (user, start_time) rather
            # than id: SQLite may reuse a deleted rowid for the new
            # on-call regenerated on the same date.
            assert (
                OnCall.query.filter_by(
                    user_id=test_user.id, start_time=start_time
                ).first()
                is None
            )
            # The returned regenerated shifts must also exist in the database.
            assert len(regenerated_shifts) > 0
            for shift in regenerated_shifts:
                assert db.session.get(Shift, shift.id) is not None

    def test_rebalance_after_leave_crossing_year_boundary(
        self, test_app, test_group, test_user, second_user
    ):
        """No test previously exercised the ±30-day padding window
        (see this method's own docstring) crossing a calendar year
        boundary - a plausible spot for a latent date-arithmetic bug
        (e.g. any code computing "next year" or formatting dates as
        strings instead of using plain date/timedelta math). A leave
        during the last on-call week of December pads the regeneration
        window on both sides by 30 days, reaching back into November
        and forward into February of the following year."""
        with test_app.app_context():
            # A 3rd user is required: with only 2 rotating users, the
            # default 2-week minimum on-call spacing constraint makes
            # every other consecutive Friday unfillable regardless of
            # the year-boundary question this test targets (confirmed
            # by first running this test with just test_user/
            # second_user: 3 Fridays came back unfilled with a
            # "délai légal non respecté" warning, an expected
            # consequence of too few users, not a bug).
            user3 = User(
                name="Third User Boundary",
                email="third-boundary@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Last Friday of 2023, on-call spans the year boundary
            # itself (Fri 29/12/2023 21:00 -> Fri 05/01/2024 07:00).
            friday = date(2023, 12, 29)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            # Leave falls inside that on-call week, in January of the
            # new year.
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )
            db.session.add(leave)
            db.session.commit()

            (
                regenerated_shifts,
                messages,
                _unfilled,
                failed_shift_dates,
                failed_oncall_period,
                _unfilled_shifts,
            ) = AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

            # No day/section in the padded window (roughly late
            # November 2023 through early February 2024) failed.
            assert failed_shift_dates == []
            assert failed_oncall_period == []

            # The old on-call spanning the boundary was replaced by a
            # freshly regenerated one for the same Friday, still
            # correctly dated in 2023 (not shifted a year by mistake).
            regenerated_oncall = OnCall.query.filter(
                OnCall.start_time == start_time
            ).first()
            assert regenerated_oncall is not None
            assert regenerated_oncall.start_time.year == 2023
            assert regenerated_oncall.end_time.year == 2024

            # Shifts were regenerated into January AND February of the
            # new year, both with the correct year - not silently
            # dropped or misdated at the boundary.
            shift_years = {shift.date.year for shift in regenerated_shifts}
            assert 2023 in shift_years
            assert 2024 in shift_years
            february_shifts = [
                shift for shift in regenerated_shifts if shift.date.month == 2
            ]
            assert february_shifts, (
                "the +30 day padding past the last Friday (05/01/2024) "
                "should reach into February 2024"
            )

    def test_rebalance_after_leave_per_group_mode_does_not_lose_other_groups_oncall(
        self, test_app, test_group, test_user
    ):
        """Regression test: under oncall_scheduling_mode="per_group",
        concurrent on-calls (one per group, for the same Friday) are
        expected and valid. A leave for a group-A user rebalancing
        group A's own window must not wipe a concurrent group-B
        on-call that happens to fall in the same ±30-day window and
        then fail to restore it (the regeneration, correctly scoped to
        group A only, has no way to recreate group B's on-call) - see
        OnCallRepository.delete_overlapping_range()'s new `group_id`
        param, added specifically to close this gap."""
        from app.services import SettingsService

        SettingsService.set_oncall_scheduling_mode("per_group")

        group_b = Group(name="Rebalance Group B", is_part_of_oncall=True)
        db.session.add(group_b)
        db.session.commit()
        user_b = User(
            name="Group B User",
            email="group-b-rebalance@test.com",
            password_hash=generate_password_hash("password123"),
            is_admin=False,
            group_id=group_b.id,
        )
        db.session.add(user_b)
        db.session.commit()

        friday = date(2023, 12, 15)
        start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)

        group_a_oncall = OnCall(
            user_id=test_user.id, start_time=start_time, end_time=end_time
        )
        group_b_oncall = OnCall(
            user_id=user_b.id, start_time=start_time, end_time=end_time
        )
        db.session.add_all([group_a_oncall, group_b_oncall])
        db.session.commit()
        group_b_oncall_id = group_b_oncall.id

        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 16),
            end_date=date(2023, 12, 18),
        )
        db.session.add(leave)
        db.session.commit()

        AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

        # Group B's on-call must survive completely untouched - same
        # row, same user, same times - even though group A's own
        # on-call for that same Friday was correctly regenerated.
        survivor = db.session.get(OnCall, group_b_oncall_id)
        assert survivor is not None
        assert survivor.user_id == user_b.id
        assert survivor.start_time == start_time
        assert survivor.end_time == end_time

    def test_rebalance_after_leave_per_group_mode_honors_group_rule_override(
        self, test_app, test_group, test_user, second_user
    ):
        """The leave-owner's own Group's rule overrides (e.g. a
        custom on-call anchor weekday) must actually be resolved
        during the rebalance, not the org-wide default - mirrors the
        same per-group rule-value gating already covered for
        check_shift_rule_violations()/check_oncall_rule_violations()."""
        from app.models import AutomationRule
        from app.services import SettingsService

        SettingsService.set_oncall_scheduling_mode("per_group")

        user3 = User(
            name="Third User Rebalance Group",
            email="third-rebalance-group@test.com",
            password_hash=generate_password_hash("third-password"),
            is_admin=False,
            group_id=test_group.id,
        )
        db.session.add(user3)
        db.session.commit()

        # test_group's own override: on-call weeks start on Thursday
        # (weekday=3), not the org-wide default Friday (weekday=4).
        AutomationRule.set(
            "oncall_anchor",
            {"weekday": 3, "start_hour": 21, "end_hour": 7},
            group=test_group,
        )

        thursday = date(2023, 12, 14)
        start_time = datetime.combine(thursday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)
        db.session.add(
            OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
        )
        db.session.commit()

        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 15),
            end_date=date(2023, 12, 16),
        )
        db.session.add(leave)
        db.session.commit()

        AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)

        # The regenerated on-calls in this window must still start on
        # Thursday (the group's own override), not fall back to the
        # org-wide Friday default.
        regenerated = OnCall.query.filter(
            OnCall.start_time >= datetime.combine(thursday, datetime.min.time())
        ).all()
        assert regenerated
        assert all(oc.start_time.weekday() == 3 for oc in regenerated)

    def test_rebalance_after_leave_setup_failure_rolls_back_and_reraises(
        self, test_app, test_group, test_user, monkeypatch
    ):
        """A failure in the setup step (before the per-day loop even
        starts) - nothing has been generated yet, so this is a full
        rollback + re-raise, not the per-day isolation used once the
        loop is under way (see this method's own docstring)."""
        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 15),
            end_date=date(2023, 12, 15),
        )
        db.session.add(leave)
        db.session.commit()

        from app.services import SettingsService

        monkeypatch.setattr(
            SettingsService,
            "get_shift_scheduling_mode",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        with pytest.raises(RuntimeError):
            AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=True)
