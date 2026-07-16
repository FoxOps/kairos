"""
Tests for the database models.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    AppNotification,
    Group,
    Leave,
    NotificationLog,
    OnCall,
    Setting,
    Shift,
    ShiftType,
    SwapRequest,
    User,
)


class TestGroupModel:
    """Tests for the Group model."""

    def test_group_creation(self, test_app):
        """Test creating a group."""
        with test_app.app_context():
            group = Group(
                name="Test Group", is_part_of_schedule=True, is_part_of_oncall=False
            )
            db.session.add(group)
            db.session.commit()

            assert group.id is not None
            assert group.name == "Test Group"
            assert group.is_part_of_schedule is True
            assert group.is_part_of_oncall is False

    def test_group_unique_name(self, test_app):
        """Test that the group name must be unique."""
        with test_app.app_context():
            group1 = Group(name="Unique Group", is_part_of_schedule=True)
            db.session.add(group1)
            db.session.commit()

            group2 = Group(name="Unique Group", is_part_of_schedule=False)
            db.session.add(group2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_group_default_values(self, test_app):
        """Test the group's default values."""
        with test_app.app_context():
            group = Group(name="Default Group")
            db.session.add(group)
            db.session.commit()

            assert group.is_part_of_schedule is False
            assert group.is_part_of_oncall is False

    def test_group_users_relationship(self, test_app, test_group, test_user):
        """Test the relationship between Group and User."""
        with test_app.app_context():
            assert test_user.group_id == test_group.id
            assert test_user in test_group.users


class TestUserModel:
    """Tests for the User model."""

    def test_user_creation(self, test_app, test_group):
        """Test creating a user."""
        with test_app.app_context():
            user = User(name="New User", email="new@test.com", group_id=test_group.id)
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.name == "New User"
            assert user.email == "new@test.com"
            assert user.is_admin is False

    def test_user_unique_email(self, test_app, test_group):
        """Test that the user's email must be unique."""
        with test_app.app_context():
            user1 = User(name="User 1", email="unique@test.com", group_id=test_group.id)
            db.session.add(user1)
            db.session.commit()

            user2 = User(name="User 2", email="unique@test.com", group_id=test_group.id)
            db.session.add(user2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_password_hashing(self, test_app, test_group):
        """Test password hashing."""
        with test_app.app_context():
            user = User(
                name="Password User", email="password@test.com", group_id=test_group.id
            )
            user.set_password("mysecretpassword")
            db.session.add(user)
            db.session.commit()

            assert user.password_hash is not None
            assert user.password_hash != "mysecretpassword"
            assert user.check_password("mysecretpassword") is True
            assert user.check_password("wrongpassword") is False

    def test_user_default_values(self, test_app, test_group):
        """Test the user's default values."""
        with test_app.app_context():
            user = User(
                name="Default User", email="default@test.com", group_id=test_group.id
            )
            db.session.add(user)
            db.session.commit()

            assert user.is_admin is False

    def test_user_repr(self, test_app, test_group):
        """Test the user's string representation."""
        with test_app.app_context():
            user = User(name="Repr User", email="repr@test.com", group_id=test_group.id)
            db.session.add(user)
            db.session.commit()

            repr_str = repr(user)
            assert "Repr User" in repr_str
            assert "repr@test.com" in repr_str

    def test_user_relationships(self, test_app, test_user, test_shift_type, test_group):
        """Test the user's relationships."""
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

            # Create an on-call for the user
            oncall_start = datetime(2023, 12, 1, 21, 0)
            oncall_end = oncall_start + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=oncall_start, end_time=oncall_end
            )
            db.session.add(oncall)

            # Create a leave for the user
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)
            db.session.commit()

            # Check the relationships
            assert len(test_user.shifts) == 1
            assert test_user.shifts[0].id == shift.id
            assert len(test_user.on_calls) == 1
            assert test_user.on_calls[0].id == oncall.id
            assert len(test_user.leaves) == 1
            assert test_user.leaves[0].id == leave.id
            assert test_user.group.id == test_group.id

    def test_effective_timezone_uses_own_preference_when_set(self, test_app, test_user):
        with test_app.app_context():
            test_user.timezone = "America/New_York"
            db.session.commit()

            assert test_user.effective_timezone() == "America/New_York"

    def test_effective_timezone_falls_back_to_org_default(self, test_app, test_user):
        with test_app.app_context():
            assert test_user.timezone is None
            assert test_user.effective_timezone() == "Europe/Paris"

    def test_effective_timezone_reflects_admin_default_change(
        self, test_app, test_user
    ):
        """A user without a personal preference must pick up a change to
        the org default retroactively - the fallback is resolved at read
        time, not baked into the column."""
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_default_timezone("America/New_York")

            assert test_user.effective_timezone() == "America/New_York"

    def test_effective_language_uses_own_preference_when_set(self, test_app, test_user):
        with test_app.app_context():
            test_user.language = "en"
            db.session.commit()

            assert test_user.effective_language() == "en"

    def test_effective_language_falls_back_to_org_default(self, test_app, test_user):
        with test_app.app_context():
            assert test_user.language is None
            assert test_user.effective_language() == "fr"

    def test_effective_language_reflects_admin_default_change(
        self, test_app, test_user
    ):
        """A user without a personal preference must pick up a change to
        the org default retroactively - the fallback is resolved at read
        time, not baked into the column."""
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_default_language("en")

            assert test_user.effective_language() == "en"

    def test_effective_date_format_uses_own_preference_when_set(
        self, test_app, test_user
    ):
        with test_app.app_context():
            test_user.date_format = "%Y-%m-%d"
            db.session.commit()

            assert test_user.effective_date_format() == "%Y-%m-%d"

    def test_effective_date_format_falls_back_to_org_default(self, test_app, test_user):
        with test_app.app_context():
            assert test_user.date_format is None
            assert test_user.effective_date_format() == "%d/%m/%Y"

    def test_effective_time_format_uses_own_preference_when_set(
        self, test_app, test_user
    ):
        with test_app.app_context():
            test_user.time_format = "%I:%M %p"
            db.session.commit()

            assert test_user.effective_time_format() == "%I:%M %p"

    def test_effective_time_format_falls_back_to_org_default(self, test_app, test_user):
        with test_app.app_context():
            assert test_user.time_format is None
            assert test_user.effective_time_format() == "%H:%M"

    def test_notification_preferences_default_to_enabled(self, test_app, test_group):
        """No opt-out existed before this preference was added - default
        must be True so existing/new users keep getting the emails they
        already got, until they explicitly disable one."""
        with test_app.app_context():
            user = User(
                name="Default Notif User",
                email="default-notif@test.com",
                group_id=test_group.id,
            )
            db.session.add(user)
            db.session.commit()

            assert user.shift_notifications_enabled is True
            assert user.oncall_notifications_enabled is True

    def test_apprise_target_ids_default_to_empty(self, test_app, test_user):
        with test_app.app_context():
            assert test_user.get_apprise_shift_target_ids() == []
            assert test_user.get_apprise_oncall_target_ids() == []

    def test_apprise_shift_target_ids_round_trip(self, test_app, test_user):
        with test_app.app_context():
            test_user.set_apprise_shift_target_ids([1, 2, 3])
            db.session.commit()

            assert test_user.get_apprise_shift_target_ids() == [1, 2, 3]

    def test_apprise_oncall_target_ids_round_trip(self, test_app, test_user):
        with test_app.app_context():
            test_user.set_apprise_oncall_target_ids([5])
            db.session.commit()

            assert test_user.get_apprise_oncall_target_ids() == [5]

    def test_set_empty_apprise_target_ids_stores_none(self, test_app, test_user):
        with test_app.app_context():
            test_user.set_apprise_shift_target_ids([1])
            test_user.set_apprise_shift_target_ids([])
            db.session.commit()

            assert test_user.apprise_shift_target_ids is None
            assert test_user.get_apprise_shift_target_ids() == []


class TestShiftTypeModel:
    """Tests for the ShiftType model."""

    def test_shift_type_creation(self, test_app):
        """Test creating a shift type."""
        with test_app.app_context():
            shift_type = ShiftType(
                name="morning", label="Matin", start_hour=7, end_hour=15
            )
            db.session.add(shift_type)
            db.session.commit()

            assert shift_type.id is not None
            assert shift_type.name == "morning"
            assert shift_type.label == "Matin"
            assert shift_type.start_hour == 7
            assert shift_type.end_hour == 15

    def test_shift_type_unique_name(self, test_app):
        """Test that the shift-type name must be unique."""
        with test_app.app_context():
            shift_type1 = ShiftType(
                name="unique", label="Unique", start_hour=8, end_hour=16
            )
            db.session.add(shift_type1)
            db.session.commit()

            shift_type2 = ShiftType(
                name="unique", label="Another", start_hour=9, end_hour=17
            )
            db.session.add(shift_type2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_shift_type_shifts_relationship(self, test_app, test_shift_type, test_user):
        """Test the relationship between ShiftType and Shift."""
        with test_app.app_context():
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

            assert len(test_shift_type.shifts) == 1
            assert test_shift_type.shifts[0].id == shift.id


class TestShiftModel:
    """Tests for the Shift model."""

    def test_shift_creation(self, test_app, test_user, test_shift_type):
        """Test creating a shift."""
        with test_app.app_context():
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

            assert shift.id is not None
            assert shift.user_id == test_user.id
            assert shift.shift_type_id == test_shift_type.id
            assert shift.date == shift_date

    def test_shift_relationships(self, test_app, test_shift):
        """Test the shift's relationships."""
        with test_app.app_context():
            assert test_shift.user is not None
            assert test_shift.shift_type is not None
            assert test_shift in test_shift.user.shifts
            assert test_shift in test_shift.shift_type.shifts


class TestOnCallModel:
    """Tests for the OnCall model."""

    def test_oncall_creation(self, test_app, test_user):
        """Test creating an on-call."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            assert oncall.id is not None
            assert oncall.user_id == test_user.id
            assert oncall.start_time == start_time
            assert oncall.end_time == end_time

    def test_oncall_relationship(self, test_app, test_oncall):
        """Test the relationship between OnCall and User."""
        with test_app.app_context():
            assert test_oncall.user is not None
            assert test_oncall in test_oncall.user.on_calls


class TestLeaveModel:
    """Tests for the Leave model."""

    def test_leave_creation(self, test_app, test_user):
        """Test creating a leave."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            assert leave.id is not None
            assert leave.user_id == test_user.id
            assert leave.start_date == start_date
            assert leave.end_date == end_date

    def test_leave_relationship(self, test_app, test_leave):
        """Test the relationship between Leave and User."""
        with test_app.app_context():
            assert test_leave.user is not None
            assert test_leave in test_leave.user.leaves

    def test_leave_without_reason(self, test_app, test_user):
        """Test creating a leave with no reason."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            assert leave.id is not None


class TestNotificationLogModel:
    """Tests for the NotificationLog model."""

    def test_notification_log_creation(self, test_app, test_user):
        """Test creating a notification log."""
        with test_app.app_context():
            period_start = datetime(2026, 7, 13).date()
            log = NotificationLog(
                user_id=test_user.id,
                notification_type="shift_weekly",
                period_start=period_start,
            )
            db.session.add(log)
            db.session.commit()

            assert log.id is not None
            assert log.user_id == test_user.id
            assert log.notification_type == "shift_weekly"
            assert log.period_start == period_start

    def test_unique_constraint_prevents_duplicate(self, test_app, test_user):
        """The same (user, type, period) can't be recorded twice."""
        with test_app.app_context():
            period_start = datetime(2026, 7, 13).date()
            db.session.add(
                NotificationLog(
                    user_id=test_user.id,
                    notification_type="shift_weekly",
                    period_start=period_start,
                )
            )
            db.session.commit()

            db.session.add(
                NotificationLog(
                    user_id=test_user.id,
                    notification_type="shift_weekly",
                    period_start=period_start,
                )
            )
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_different_notification_type_is_allowed(self, test_app, test_user):
        """Same user/period but different type: no conflict."""
        with test_app.app_context():
            period_start = datetime(2026, 7, 13).date()
            db.session.add(
                NotificationLog(
                    user_id=test_user.id,
                    notification_type="shift_weekly",
                    period_start=period_start,
                )
            )
            db.session.add(
                NotificationLog(
                    user_id=test_user.id,
                    notification_type="oncall_weekly",
                    period_start=period_start,
                )
            )
            db.session.commit()

            assert NotificationLog.query.count() == 2

    def test_already_sent_true_when_logged(self, test_app, test_user):
        with test_app.app_context():
            period_start = datetime(2026, 7, 13).date()
            db.session.add(
                NotificationLog(
                    user_id=test_user.id,
                    notification_type="shift_weekly",
                    period_start=period_start,
                )
            )
            db.session.commit()

            assert (
                NotificationLog.already_sent(test_user.id, "shift_weekly", period_start)
                is True
            )

    def test_already_sent_false_when_not_logged(self, test_app, test_user):
        with test_app.app_context():
            period_start = datetime(2026, 7, 13).date()
            assert (
                NotificationLog.already_sent(test_user.id, "shift_weekly", period_start)
                is False
            )


class TestSwapRequestModel:
    """Tests for the SwapRequest model."""

    def test_swap_request_creation(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        """Test creating a swap request."""
        with test_app.app_context():
            swap_request = SwapRequest(
                requester_id=test_user.id,
                shift_id=test_swap_shift.id,
                target_user_id=second_user.id,
            )
            db.session.add(swap_request)
            db.session.commit()

            assert swap_request.id is not None
            assert swap_request.status == SwapRequest.PENDING
            assert swap_request.target_shift_id is None

    def test_swap_request_relationships(self, test_app, test_swap_request):
        """Test the requester/target_user/shift properties (not ORM relationships)."""
        with test_app.app_context():
            assert test_swap_request.requester.id == test_swap_request.requester_id
            assert test_swap_request.target_user.id == test_swap_request.target_user_id
            assert test_swap_request.shift.id == test_swap_request.shift_id
            assert test_swap_request.target_shift is None
            assert test_swap_request.reviewer is None

    def test_is_pending(self, test_app, test_swap_request):
        with test_app.app_context():
            assert test_swap_request.is_pending() is True
            test_swap_request.status = SwapRequest.APPROVED
            assert test_swap_request.is_pending() is False

    def test_mark_reviewed(self, test_app, test_swap_request, second_user):
        with test_app.app_context():
            test_swap_request.mark_reviewed(
                second_user.id, SwapRequest.REJECTED, comment="Conflit de planning"
            )
            assert test_swap_request.status == SwapRequest.REJECTED
            assert test_swap_request.reviewed_by_id == second_user.id
            assert test_swap_request.reviewed_at is not None
            assert test_swap_request.admin_comment == "Conflit de planning"


class TestAppNotificationModel:
    """Tests for the AppNotification model."""

    def test_creation_defaults_to_unread(self, test_app, test_user):
        with test_app.app_context():
            notification = AppNotification(
                user_id=test_user.id,
                notification_type="swap_request_created",
                message="Test",
            )
            db.session.add(notification)
            db.session.commit()

            assert notification.id is not None
            assert notification.read_at is None
            assert notification.is_unread() is True
            assert notification.link is None

    def test_mark_read(self, test_app, test_user):
        with test_app.app_context():
            notification = AppNotification(
                user_id=test_user.id,
                notification_type="swap_approved",
                message="Test",
                link="/swaps",
            )
            db.session.add(notification)
            db.session.commit()

            notification.mark_read()
            assert notification.read_at is not None
            assert notification.is_unread() is False


class TestSettingModel:
    """Tests for the Setting model (generic key/value admin settings store)."""

    def test_get_returns_default_when_missing(self, test_app):
        with test_app.app_context():
            assert Setting.get("does_not_exist") is None
            assert Setting.get("does_not_exist", default="fallback") == "fallback"

    def test_set_then_get_round_trips_string(self, test_app):
        with test_app.app_context():
            Setting.set("default_timezone", "Europe/Paris")
            assert Setting.get("default_timezone") == "Europe/Paris"

    def test_set_then_get_round_trips_non_string_types(self, test_app):
        with test_app.app_context():
            Setting.set("items_per_page", 25)
            Setting.set("notifications_enabled", True)
            Setting.set("some_list", [1, 2, 3])

            assert Setting.get("items_per_page") == 25
            assert Setting.get("notifications_enabled") is True
            assert Setting.get("some_list") == [1, 2, 3]

    def test_set_upserts_existing_key(self, test_app):
        with test_app.app_context():
            Setting.set("default_timezone", "Europe/Paris")
            Setting.set("default_timezone", "America/New_York")

            assert Setting.get("default_timezone") == "America/New_York"
            assert Setting.query.filter_by(key="default_timezone").count() == 1

    def test_different_keys_do_not_collide(self, test_app):
        with test_app.app_context():
            Setting.set("key_a", "value_a")
            Setting.set("key_b", "value_b")

            assert Setting.get("key_a") == "value_a"
            assert Setting.get("key_b") == "value_b"
            assert Setting.query.count() == 2
