"""
Tests for the advanced shift automation module.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

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
        one is on leave), that person must land directly on 09h-17h."""
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
            assert shifts[0].start_time.hour == 9
            assert shifts[0].end_time.hour == 17

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
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(shifts) > 0

    def test_generate_full_schedule_multiple_days(
        self, test_app, test_group, test_user
    ):
        """Test generation over several days."""
        with test_app.app_context():
            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
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
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_generate_full_schedule_with_commit(self, test_app, test_group, test_user):
        """Test that dry_run=False commits the changes."""
        with test_app.app_context():
            initial_count = Shift.query.count()

            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=False
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
            shifts, messages, _unfilled = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )

            # No change should be committed
            final_count = Shift.query.count()
            assert final_count == initial_count

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
            shifts, messages, _unfilled = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
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

            shifts, messages, _unfilled = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )

            # Should generate messages but no deletion
            assert len(messages) > 0

    def test_rebalance_after_leave_rolls_back_fully_on_failure(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: if regenerating the on-calls fails at the
        end of the rebalance, the already-deleted on-call (flushed, not
        committed) and the already-regenerated shifts must be rolled
        back - no partially modified schedule."""
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

            oncall_count_before = OnCall.query.count()
            shift_count_before = Shift.query.count()

            with patch(
                "app.utils.automation.OnCallAutomation.generate_oncall_schedule",
                side_effect=RuntimeError("boom"),
            ):
                raised = False
                try:
                    AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)
                except RuntimeError:
                    raised = True

            assert raised is True
            # Full rollback: the on-call deleted via flush must be back,
            # and no regenerated shift should have survived.
            assert OnCall.query.count() == oncall_count_before
            assert Shift.query.count() == shift_count_before

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

            regenerated_shifts, messages, _unfilled = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)
            )

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
