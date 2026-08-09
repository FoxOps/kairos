"""
Tests for per-Group rule VALUE resolution in the manual-creation
validation path (app/utils/helpers/common_helpers.py's
check_shift_rule_violations()/check_oncall_rule_violations()) - the
same "per_group" scheduling mode concept covered for automatic
generation by tests/unit/test_automation_group_scoping.py, but for the
create/move-a-single-shift-or-oncall path (ShiftService/OnCallService)
instead.

Mirrors generation's own mode gating: check_shift_rule_violations()
only resolves the acting user's own Group override when
shift_scheduling_mode is "per_group" (else group=None, org-wide,
exactly today's behavior); check_oncall_rule_violations() does the
same for oncall_scheduling_mode. shared (the default) must behave
identically to before this feature - a Group override existing in the
database is not enough on its own to change validation behavior.
"""

from datetime import datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import AutomationRule, Group, ShiftType, User
from app.services import SettingsService
from app.utils.helpers.common_helpers import (
    check_oncall_rule_violations,
    check_shift_rule_violations,
)


def _make_user(name, email, group):
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash("x"),
        is_admin=False,
        group_id=group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestCheckShiftRuleViolationsStaffingLimitsGroupScoping:
    def test_group_override_applies_when_shift_mode_per_group(
        self, test_app, test_group, test_shift_type
    ):
        SettingsService.set_shift_scheduling_mode("per_group")
        user = _make_user("A", "a@test.com", test_group)
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": None, "max": 0}},
            group=test_group,
        )

        error = check_shift_rule_violations(
            user, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )

        assert error is not None

    def test_group_override_ignored_when_shift_mode_shared(
        self, test_app, test_group, test_shift_type
    ):
        assert SettingsService.get_shift_scheduling_mode() == "shared"
        user = _make_user("A", "a@test.com", test_group)
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": None, "max": 0}},
            group=test_group,
        )

        error = check_shift_rule_violations(
            user, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )

        assert error is None


class TestCheckShiftRuleViolationsOnCallOverlapGroupScoping:
    def test_group_override_applies_when_shift_mode_per_group(
        self, test_app, test_group, test_shift_type
    ):
        from app.models import OnCall

        SettingsService.set_shift_scheduling_mode("per_group")
        user = _make_user("A", "a@test.com", test_group)
        db.session.add(
            OnCall(
                user_id=user.id,
                start_time=datetime(2023, 12, 4, 6, 0),
                end_time=datetime(2023, 12, 4, 20, 0),
            )
        )
        db.session.commit()

        AutomationRule.set("oncall_shift_overlap", {"block": False}, group=test_group)

        error = check_shift_rule_violations(
            user, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )

        assert error is None

    def test_group_override_ignored_when_shift_mode_shared(
        self, test_app, test_group, test_shift_type
    ):
        from app.models import OnCall

        assert SettingsService.get_shift_scheduling_mode() == "shared"
        user = _make_user("A", "a@test.com", test_group)
        db.session.add(
            OnCall(
                user_id=user.id,
                start_time=datetime(2023, 12, 4, 6, 0),
                end_time=datetime(2023, 12, 4, 20, 0),
            )
        )
        db.session.commit()

        AutomationRule.set("oncall_shift_overlap", {"block": False}, group=test_group)

        error = check_shift_rule_violations(
            user, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )

        assert error is not None


class TestCheckOnCallRuleViolationsGroupScoping:
    def test_group_override_applies_when_oncall_mode_per_group(
        self, test_app, test_group
    ):
        from app.models import Shift

        SettingsService.set_oncall_scheduling_mode("per_group")
        user = _make_user("A", "a@test.com", test_group)
        shift_type = ShiftType(name="am", label="AM", start_hour=7, end_hour=15)
        db.session.add(shift_type)
        db.session.commit()
        db.session.add(
            Shift(
                user_id=user.id,
                shift_type_id=shift_type.id,
                date=datetime(2023, 12, 4).date(),
                start_time=datetime(2023, 12, 4, 7, 0),
                end_time=datetime(2023, 12, 4, 15, 0),
            )
        )
        db.session.commit()

        AutomationRule.set("oncall_shift_overlap", {"block": False}, group=test_group)

        error = check_oncall_rule_violations(
            user, datetime(2023, 12, 4, 6, 0), datetime(2023, 12, 4, 20, 0)
        )

        assert error is None

    def test_group_override_ignored_when_oncall_mode_shared(self, test_app, test_group):
        from app.models import Shift

        assert SettingsService.get_oncall_scheduling_mode() == "shared"
        user = _make_user("A", "a@test.com", test_group)
        shift_type = ShiftType(name="am", label="AM", start_hour=7, end_hour=15)
        db.session.add(shift_type)
        db.session.commit()
        db.session.add(
            Shift(
                user_id=user.id,
                shift_type_id=shift_type.id,
                date=datetime(2023, 12, 4).date(),
                start_time=datetime(2023, 12, 4, 7, 0),
                end_time=datetime(2023, 12, 4, 15, 0),
            )
        )
        db.session.commit()

        AutomationRule.set("oncall_shift_overlap", {"block": False}, group=test_group)

        error = check_oncall_rule_violations(
            user, datetime(2023, 12, 4, 6, 0), datetime(2023, 12, 4, 20, 0)
        )

        assert error is not None


class TestGroupScopingDoesNotAffectOtherGroup:
    def test_shift_mode_per_group_other_groups_user_unaffected(
        self, test_app, test_group, test_shift_type
    ):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()

        SettingsService.set_shift_scheduling_mode("per_group")
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": None, "max": 0}},
            group=test_group,
        )

        error_a = check_shift_rule_violations(
            user_a, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )
        error_b = check_shift_rule_violations(
            user_b, datetime(2023, 12, 4).date(), shift_type=test_shift_type
        )

        assert error_a is not None
        assert error_b is None
