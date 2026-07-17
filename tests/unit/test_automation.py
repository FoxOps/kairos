"""
Tests for the on-call and shift automation module.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, Leave, OnCall, User
from app.utils.automation import (
    AdvancedShiftAutomation,
    OnCallAutomation,
    get_automation_status,
)
from app.utils.automation.oncall_automation import AvailabilityIndex


class TestOnCallAutomation:
    """Tests for the on-call automation."""

    def test_get_eligible_users(self, test_app, test_group, test_user, second_user):
        """Test fetching the users eligible for on-calls."""
        with test_app.app_context():
            # Create a third user in the same group
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            eligible_users = OnCallAutomation.get_eligible_users()
            # Every user in the group is eligible (is_part_of_oncall=True)
            assert len(eligible_users) == 3
            assert all(user.group.is_part_of_oncall for user in eligible_users)

    def test_get_rotation_order_default(
        self, test_app, test_group, test_user, second_user
    ):
        """Test the default rotation order (alphabetical)."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Zebra User",  # Z to be last alphabetically
                email="zebra@test.com",
                password_hash="zebra123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = OnCallAutomation.get_rotation_order()
            assert len(rotation_order) == 3
            # Check that the order is alphabetical
            # Note: Admin User starts with 'A', Second User with 'S', Zebra User with 'Z'
            names = [u.name for u in rotation_order]
            assert names == sorted(names)

    def test_get_rotation_order_custom(
        self, test_app, test_group, test_user, second_user
    ):
        """Test a custom rotation order."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Custom order: second_user, user3, test_user
            custom_order = [second_user.id, user3.id, test_user.id]
            rotation_order = OnCallAutomation.get_rotation_order(custom_order)

            assert len(rotation_order) == 3
            assert rotation_order[0].id == second_user.id
            assert rotation_order[1].id == user3.id
            assert rotation_order[2].id == test_user.id

    def test_find_next_available_user(
        self, test_app, test_group, test_user, second_user
    ):
        """Test finding the next available user."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = [test_user, second_user, user3]

            # Create an existing on-call for test_user
            start_time = datetime(2024, 1, 5, 21, 0)  # Friday, January 5, 2024 at 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Find an available user for the same period
            index = AvailabilityIndex([test_user.id, second_user.id, user3.id])
            available_user = OnCallAutomation.find_next_available_user(
                rotation_order, start_time, end_time, index
            )

            # test_user isn't available, so second_user should be returned
            assert available_user is not None
            assert available_user.id == second_user.id

            # Clean up
            db.session.delete(oncall)
            db.session.commit()

    def test_generate_oncall_schedule_dry_run(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generating on-calls in dry-run mode."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 2, 23)  # 8 weeks later

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Should generate 7 or 8 on-calls depending on the exact end date
            assert len(oncalls) >= 7
            assert len(messages) > 0

            # Check that the on-calls are spaced one week apart
            for i in range(1, len(oncalls)):
                assert oncalls[i].start_time == oncalls[i - 1].start_time + timedelta(
                    days=7
                )

    def test_generate_oncall_schedule_with_rotation(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generation with a custom rotation order."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 19)  # 2 weeks later

            # Custom order: second_user, test_user, user3
            rotation_order = [second_user.id, test_user.id, user3.id]

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order, dry_run=True
            )

            # end_date inclusive: 3 Fridays (01/05, 01/12, 01/19).
            assert len(oncalls) == 3
            # The first on-call should be for second_user
            assert oncalls[0].user_id == second_user.id
            # The second on-call should be for test_user
            assert oncalls[1].user_id == test_user.id


class TestFullScheduleGeneration:
    """Tests for the full schedule generation."""

    def test_generate_full_schedule_dry_run(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        """Test the full generation in dry-run mode."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 19)  # 2 weeks later

            # AdvancedShiftAutomation.generate_full_schedule only
            # generates shifts (business days); on-calls are generated
            # separately by OnCallAutomation.generate_oncall_schedule.
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(shifts) > 0
            assert len(messages) > 0

            oncalls, oncall_messages, _unfilled = (
                OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, dry_run=True
                )
            )
            # end_date inclusive: 3 Fridays (01/05, 01/12, 01/19).
            assert len(oncalls) == 3

    def test_get_automation_status(self, test_app, test_group, test_user, second_user):
        """Test fetching the automation status."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            status = get_automation_status()

            assert "oncall_count" in status
            assert "shift_count" in status
            assert "oncall_eligible_users" in status
            assert "shift_eligible_users" in status
            assert "next_available_oncall_date" in status

            # Check the values
            assert status["oncall_eligible_users"] == 3
            assert status["shift_eligible_users"] == 3


class TestEdgeCases:
    """Tests for edge cases."""

    def test_generate_oncall_no_eligible_users(self, test_app):
        """Test generating on-calls with no eligible users."""
        with test_app.app_context():
            # Create a group without is_part_of_oncall
            group = Group(
                name="No OnCall", is_part_of_schedule=True, is_part_of_oncall=False
            )
            db.session.add(group)
            db.session.commit()

            start_date = date(2024, 1, 5)
            end_date = date(2024, 1, 19)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(oncalls) == 0
            assert any("Aucun utilisateur éligible" in msg for msg in messages)

    def test_generate_oncall_with_leave_conflict(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generating on-calls with a leave conflict."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Create a leave for test_user
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 5),
                end_date=date(2024, 1, 12),
            )
            db.session.add(leave)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday
            # Bounded to the end of the leave (not 2 weeks after like the
            # other tests): beyond that, test_user legitimately becomes
            # assignable again once their leave ends - this test
            # specifically checks the exclusion DURING the leave, not
            # beyond it.
            end_date = date(2024, 1, 12)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # end_date inclusive: 2 Fridays (01/05, 01/12), both covered
            # by test_user's leave.
            assert len(oncalls) == 2
            assert all(oncall.user_id != test_user.id for oncall in oncalls)

            # Clean up
            db.session.delete(leave)
            db.session.commit()
