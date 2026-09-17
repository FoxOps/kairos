"""Phase 7 follow-up: build_planning_request(restrict_to_group_id=...)
narrows oncall_groups/schedule_groups to at most that one group under
"per_group" mode - built for
AdvancedShiftAutomation.rebalance_after_leave()'s own cutover, which
must never replan every other group's schedule just because one user
in one group took a leave."""

from datetime import date

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, User
from app.services.settings_service import SettingsService
from app.utils.automation.planner import adapters


def _make_group(name, **kwargs):
    group = Group(name=name, **kwargs)
    db.session.add(group)
    db.session.commit()
    return group


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


class TestRestrictToGroupIdUnderPerGroupMode:
    def test_narrows_to_the_given_group_only(self, test_app):
        group_a = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        group_b = _make_group("B", is_part_of_schedule=True, is_part_of_oncall=True)
        _make_user("UA", "ua@x.com", group_a)
        _make_user("UB", "ub@x.com", group_b)
        SettingsService.set_oncall_scheduling_mode("per_group")
        SettingsService.set_shift_scheduling_mode("per_group")

        request = adapters.build_planning_request(
            date(2026, 9, 4),
            date(2026, 9, 10),
            restrict_to_group_id=group_a.id,
        )

        assert request.oncall_groups == (group_a.id,)
        assert request.schedule_groups == (group_a.id,)

    def test_ineligible_group_narrows_to_empty(self, test_app):
        group_a = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        not_eligible = _make_group(
            "C", is_part_of_schedule=False, is_part_of_oncall=False
        )
        _make_user("UA", "ua@x.com", group_a)
        SettingsService.set_oncall_scheduling_mode("per_group")
        SettingsService.set_shift_scheduling_mode("per_group")

        request = adapters.build_planning_request(
            date(2026, 9, 4),
            date(2026, 9, 10),
            restrict_to_group_id=not_eligible.id,
        )

        assert request.oncall_groups == ()
        assert request.schedule_groups == ()


class TestRestrictToGroupIdUnderSharedMode:
    def test_has_no_effect_when_mode_is_shared(self, test_app):
        group = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        _make_user("U0", "u0@x.com", group)
        # Default scheduling mode is "shared" - not set explicitly here.

        request = adapters.build_planning_request(
            date(2026, 9, 4),
            date(2026, 9, 10),
            restrict_to_group_id=group.id,
        )

        assert request.oncall_groups == (None,)
        assert request.schedule_groups == (None,)
