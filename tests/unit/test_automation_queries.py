"""Tests for the DB-backed automation lookups that survived the legacy
engine's removal (1.2.0): app/utils/automation/queries.py and the
shift-slot ShiftType resolution in app/utils/automation/rules/shift_slots.py.
Moved from the former tests/unit/test_advanced_shift_automation.py."""

from werkzeug.security import generate_password_hash

from app import db
from app.models import ShiftType, User
from app.utils.automation.queries import get_schedule_users
from app.utils.automation.rules.shift_slots import (
    ROTATION_KEY,
    get_shift_type_by_hours,
    get_shift_type_for_role,
)


class TestShiftTypeByHours:
    """Tests for creating shift types by hours."""

    def test_get_shift_type_by_hours_existing(self, test_app, test_shift_type):
        """Test fetching an existing shift type."""
        with test_app.app_context():
            shift_type = get_shift_type_by_hours(7, 15)

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

            shift_type = get_shift_type_by_hours(13, 21)

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
    get_shift_type_for_role() resolves via the configured ShiftSlotsRule
    id instead, closing that gap."""

    def test_default_matches_legacy_hours(self, test_app):
        shift_type = get_shift_type_for_role(ROTATION_KEY)
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

        shift_type = get_shift_type_for_role(ROTATION_KEY)
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

        shift_type = get_shift_type_for_role(ROTATION_KEY)
        assert shift_type is not None
        assert (shift_type.start_hour, shift_type.end_hour) == (7, 15)


class TestScheduleUsers:
    """queries.get_schedule_users()."""

    def test_get_users_in_schedule_groups(
        self, test_app, test_group, test_user, second_user
    ):
        """Test fetching the users in the schedule groups."""
        with test_app.app_context():
            # test_group has is_part_of_schedule=True by default
            users = get_schedule_users()

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

            users = get_schedule_users()
            user_ids = [u.id for u in users]

            assert test_user.id in user_ids
            assert user_not_in_schedule.id not in user_ids
