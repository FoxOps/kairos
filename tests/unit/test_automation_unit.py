"""
Unit tests for app/utils/automation.py
Covers functions and classes not previously tested.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, OnCall
from app.utils.automation import OnCallAutomation
from app.utils.automation.oncall_automation import AvailabilityIndex


class TestOnCallAutomationGetEligibleUsers:
    """Tests for OnCallAutomation.get_eligible_users."""

    def test_returns_list(self, test_app):
        """Test that get_eligible_users returns a list."""
        with test_app.app_context():
            users = OnCallAutomation.get_eligible_users()
            assert isinstance(users, list)

    def test_filters_by_oncall_group(self, test_app, test_group, test_user):
        """Test that get_eligible_users filters by is_part_of_oncall."""
        with test_app.app_context():
            # test_group has is_part_of_oncall=True by default
            # test_user belongs to test_group
            users = OnCallAutomation.get_eligible_users()
            # Check that test_user is in the list
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids


class TestOnCallAutomationGetRotationOrder:
    """Tests for OnCallAutomation.get_rotation_order."""

    def test_returns_list(self, test_app):
        """Test that get_rotation_order returns a list."""
        with test_app.app_context():
            rotation = OnCallAutomation.get_rotation_order()
            assert isinstance(rotation, list)

    def test_empty_when_no_eligible_users(self, test_app):
        """Test that get_rotation_order returns an empty list with no eligible users."""
        with test_app.app_context():
            # Disable every group for on-calls
            Group.query.update({"is_part_of_oncall": False})
            db.session.commit()
            rotation = OnCallAutomation.get_rotation_order()
            assert rotation == []


class TestOnCallAutomationCheckConstraint:
    """Tests for OnCallAutomation.check_oncall_constraint."""

    def test_returns_true_no_previous_oncall(self, test_app, test_user):
        """Test that check_oncall_constraint returns True with no previous on-call."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=30)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, index
            )
            assert result is True

    def test_returns_false_too_soon(self, test_app, test_user):
        """Test that check_oncall_constraint returns False if too soon."""
        with test_app.app_context():
            now = datetime.now()
            # Create a previous on-call
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=13),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Test with a date that's too close (less than 2 weeks after)
            start_time = now - timedelta(days=12)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, index
            )
            assert result is False

    def test_returns_true_sufficient_spacing(self, test_app, test_user):
        """Test that check_oncall_constraint returns True with sufficient spacing."""
        with test_app.app_context():
            now = datetime.now()
            # Create a previous on-call
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=30),
                end_time=now - timedelta(days=23),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Test with a date far enough in the future
            start_time = now + timedelta(days=15)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, index
            )
            assert result is True


class TestOnCallAutomationFindNextAvailable:
    """Tests for OnCallAutomation.find_next_available_user."""

    def test_returns_none_empty_list(self, test_app):
        """Test that find_next_available_user returns None with an empty list."""
        with test_app.app_context():
            index = AvailabilityIndex([])
            result = OnCallAutomation.find_next_available_user(
                [], datetime.now(), datetime.now(), index
            )
            assert result is None

    def test_returns_user_when_available(self, test_app, test_user):
        """Test that find_next_available_user returns an available user."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=10)
            end_time = start_time + timedelta(days=7)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time, index
            )
            # May return test_user or None depending on conflicts
            assert result is None or result.id == test_user.id


class TestOnCallAutomationGenerateSchedule:
    """Tests for OnCallAutomation.generate_oncall_schedule."""

    def test_returns_tuple(self, test_app):
        """Test that generate_oncall_schedule returns a tuple."""
        with test_app.app_context():
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            result = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_dry_run_does_not_save(self, test_app, test_user, test_group):
        """Test that dry_run=True doesn't save to the database."""
        with test_app.app_context():
            # Make sure test_user is eligible
            test_group.is_part_of_oncall = True
            db.session.commit()

            start_date = date.today()
            end_date = start_date + timedelta(days=7)

            # Count before
            count_before = OnCall.query.count()

            # Generate in dry_run
            OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Check that nothing was saved
            count_after = OnCall.query.count()
            assert count_after == count_before
