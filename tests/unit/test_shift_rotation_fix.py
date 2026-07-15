"""
Test checking that shift rotation works correctly.
This test checks that the first day of an on-call (Monday) uses 09h-17h, not 13h-21h.
"""

from datetime import date, datetime, timedelta

import pytest

from app import create_app, db
from app.models import Group, OnCall, User
from app.utils.automation import AdvancedShiftAutomation


@pytest.fixture
def app_context():
    """Create an app context for the tests."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_shift_rotation_first_day_of_oncall(app_context):
    """Test that the first day of an on-call (Monday) uses 09h-17h, not 13h-21h."""
    with app_context.app_context():
        # Create a group eligible for shifts and on-calls
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Create a user
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Create an on-call for the user (from Friday 21:00 to the following Friday 07:00)
        friday = date(2024, 6, 21)  # Friday
        start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)  # Following Friday 07:00

        oncall = OnCall(user_id=user.id, start_time=start_time, end_time=end_time)
        db.session.add(oncall)
        db.session.commit()

        # Test Monday (first business day of the on-call)
        monday = date(2024, 6, 24)  # Monday
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"Monday (first on-call day) should be 09h-17h, got {shift}"

        # Test Tuesday (2nd day)
        tuesday = date(2024, 6, 25)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, tuesday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Tuesday (2nd on-call day) should be 13h-21h, got {shift}"

        # Test Wednesday (3rd day)
        wednesday = date(2024, 6, 26)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, wednesday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Wednesday (3rd on-call day) should be 13h-21h, got {shift}"

        # Test Thursday (4th day)
        thursday = date(2024, 6, 27)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, thursday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Thursday (4th on-call day) should be 13h-21h, got {shift}"

        # Test Friday (last on-call day)
        friday = date(2024, 6, 28)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, friday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"Friday (last on-call day) should be 09h-17h, got {shift}"


def test_shift_rotation_after_previous_oncall(app_context):
    """Test that rotation works after an on-call the previous week."""
    with app_context.app_context():
        # Create an eligible group
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Create a user
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Create an on-call for the previous week (from Friday 21:00 to the following Friday 07:00)
        previous_friday = date(2024, 6, 14)  # Friday of the previous week
        start_time = datetime.combine(previous_friday, datetime.min.time()).replace(
            hour=21
        )
        end_time = start_time + timedelta(days=7, hours=-14)

        previous_oncall = OnCall(
            user_id=user.id, start_time=start_time, end_time=end_time
        )
        db.session.add(previous_oncall)
        db.session.commit()

        # Test the Monday of the following week (after the on-call)
        next_monday = date(2024, 6, 24)  # Monday of the following week
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, next_monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_07_15
        ), f"Monday after an on-call should be 07h-15h (rotation), got {shift}"


def test_shift_default_for_non_oncall_user(app_context):
    """Test that users not on call use the default slot (09h-17h)."""
    with app_context.app_context():
        # Create an eligible group
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Create a user
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Don't create an on-call for this user

        # Test any given Monday
        monday = date(2024, 6, 24)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"A user not on call should be 09h-17h, got {shift}"
