"""
Tests for optional per-Group scoping of the automation generation
entry points - both halves of "per_group" scheduling mode
(SettingsService.get_shift_scheduling_mode()/get_oncall_scheduling_mode()):
partitioning the eligible-user pool so two groups don't compete for the
same on-call/staffing budget (TestGetEligibleUsersGroupScoping and
friends below), and resolving rule *values* (weekend/slots/spacing/
anchor) per Group instead of a single org-wide value
(TestWeekendDefinitionRuleValueGroupScoping and friends further down -
each configures a Group-specific AutomationRule override via
AutomationRule.set(rule_type, params, group=group) and proves it only
affects that group's own generation, not another group's or the
org-wide default). group=None (the default everywhere) must keep
today's pooled behavior unchanged in both cases.
"""

from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from app import db
from app.models import AutomationConfig, AutomationRule, Group, OnCall, ShiftType, User
from app.utils.automation import queries
from app.utils.automation.planner import build_planning_request, plan_schedule


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


class TestGetEligibleUsersGroupScoping:
    def test_group_none_pools_every_eligible_group(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        eligible = queries.get_oncall_users()
        assert {u.id for u in eligible} == {u1.id, u2.id}

    def test_group_given_restricts_to_that_group(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        eligible = queries.get_oncall_users(group=test_group)
        assert {u.id for u in eligible} == {u1.id}


class TestGetUsersInScheduleGroupsGroupScoping:
    def test_group_given_restricts_to_that_group(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        users = queries.get_schedule_users(group=test_group)
        assert {u.id for u in users} == {u1.id}


def _plan(start_date, end_date):
    """Both scheduling modes "per_group" - one independent planning pass
    per Group, the mode every test below is about."""
    from app.services import SettingsService

    SettingsService.set_shift_scheduling_mode("per_group")
    SettingsService.set_oncall_scheduling_mode("per_group")
    return plan_schedule(build_planning_request(start_date, end_date))


def _oncalls_for(plan, group):
    return [o for o in plan.oncalls if o.group_id == group.id]


def _shifts_for(plan, group):
    return [s for s in plan.shifts if s.group_id == group.id]


class TestPlannerOnCallGroupScoping:
    def test_two_groups_get_independent_rotations(self, test_app, test_group):
        """The key observable behavior of per_group mode for on-calls:
        each participating group runs its own full weekly rotation, so
        the same Friday can end up with more than one concurrent
        on-call - one per group - instead of a single pooled winner."""
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        plan = _plan(friday, friday)

        assert [o.user_id for o in _oncalls_for(plan, test_group)] == [u1.id]
        assert [o.user_id for o in _oncalls_for(plan, other_group)] == [u2.id]

    def test_rotation_order_ids_outside_group_are_ignored(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)
        AutomationConfig.set_rotation_order([u2.id, u1.id])

        friday = date(2023, 12, 1)
        plan = _plan(friday, friday)

        assert [o.user_id for o in _oncalls_for(plan, test_group)] == [u1.id]


class TestPlannerShiftGroupScoping:
    def test_two_groups_get_independent_shift_generation(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        monday = date(2023, 12, 4)
        plan = _plan(monday, monday)

        assert {s.user_id for s in _shifts_for(plan, test_group)} == {u1.id}
        assert {s.user_id for s in _shifts_for(plan, other_group)} == {u2.id}


class TestWeekendDefinitionRuleValueGroupScoping:
    def test_group_override_only_affects_that_groups_generation(
        self, test_app, test_group
    ):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        # Monday - a normal working day under the org-wide default
        # (weekend_days=[5, 6]). Overriding it to [0] for test_group
        # only should make test_group's own generation skip it while
        # other_group still generates normally.
        monday = date(2023, 12, 4)
        AutomationRule.set(
            "weekend_definition", {"weekend_days": [0]}, group=test_group
        )

        plan = _plan(monday, monday)

        assert _shifts_for(plan, test_group) == []
        assert len(_shifts_for(plan, other_group)) == 1


class TestShiftSlotsRuleValueGroupScoping:
    def test_group_override_changes_shift_type_used(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        custom_type = ShiftType(
            name="custom", label="Custom", start_hour=6, end_hour=14
        )
        db.session.add(custom_type)
        db.session.commit()

        AutomationRule.set(
            "shift_slots",
            {
                "oncall_shift_type_id": custom_type.id,
                "rotation_shift_type_id": custom_type.id,
                "default_shift_type_id": custom_type.id,
            },
            group=test_group,
        )

        monday = date(2023, 12, 4)
        plan = _plan(monday, monday)

        assert _shifts_for(plan, test_group)[0].shift_type_id == custom_type.id
        assert _shifts_for(plan, other_group)[0].shift_type_id != custom_type.id


class TestOnCallAnchorRuleValueGroupScoping:
    def test_group_override_changes_anchor_weekday(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        # Org default anchor is Friday (4). Override test_group to
        # anchor on Monday (0) instead - only a Monday-starting week
        # should get filled for that group, while other_group keeps
        # anchoring on the org-default Friday.
        AutomationRule.set(
            "oncall_anchor",
            {"weekday": 0, "start_hour": 21, "end_hour": 7},
            group=test_group,
        )

        plan = _plan(date(2023, 12, 1), date(2023, 12, 4))

        oncalls_a = _oncalls_for(plan, test_group)
        oncalls_b = _oncalls_for(plan, other_group)
        assert [(o.user_id, o.start_time) for o in oncalls_a] == [
            (u1.id, datetime(2023, 12, 4, 21, 0))
        ]
        assert [(o.user_id, o.start_time) for o in oncalls_b] == [
            (u2.id, datetime(2023, 12, 1, 21, 0))
        ]


class TestOnCallSpacingRuleValueGroupScoping:
    def test_group_override_relaxes_minimum_spacing(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        # Org default is 2 weeks minimum spacing between on-calls for
        # the same person - with only 1 rotating user, every week after
        # the first is unfillable under that default. Relaxing it to 0
        # for test_group only should let that single user cover every
        # week for their own group.
        AutomationRule.set("oncall_spacing", {"min_spacing_weeks": 0}, group=test_group)

        friday = date(2023, 12, 1)
        plan = _plan(friday, friday + timedelta(days=7))

        oncalls_a = _oncalls_for(plan, test_group)
        assert len(oncalls_a) == 2
        assert {o.user_id for o in oncalls_a} == {u1.id}
        assert not [
            u
            for u in plan.unfilled
            if u.kind == "oncall_week" and u.group_id == test_group.id
        ]


class TestGetAutomationStatusGroupScoping:
    def test_counts_scoped_to_group(self, test_app, test_group, test_shift_type):
        from app.models import Shift
        from app.utils.automation import get_automation_status

        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        db.session.add(
            Shift(
                user_id=user_a.id,
                shift_type_id=test_shift_type.id,
                date=date(2023, 12, 4),
                start_time=datetime(2023, 12, 4, 7, 0),
                end_time=datetime(2023, 12, 4, 15, 0),
            )
        )
        db.session.add(
            OnCall(
                user_id=user_a.id,
                start_time=datetime(2023, 12, 1, 21, 0),
                end_time=datetime(2023, 12, 8, 7, 0),
            )
        )
        db.session.add(
            Shift(
                user_id=user_b.id,
                shift_type_id=test_shift_type.id,
                date=date(2023, 12, 4),
                start_time=datetime(2023, 12, 4, 7, 0),
                end_time=datetime(2023, 12, 4, 15, 0),
            )
        )
        db.session.commit()

        status_a = get_automation_status(group=test_group)
        status_b = get_automation_status(group=other_group)

        assert status_a["shift_count"] == 1
        assert status_a["oncall_count"] == 1
        assert status_b["shift_count"] == 1
        assert status_b["oncall_count"] == 0

    def test_eligible_users_scoped_to_group(self, test_app, test_group):
        from app.utils.automation import get_automation_status

        other_group = Group(
            name="Other", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)
        _make_user("C", "c@test.com", other_group)

        status_a = get_automation_status(group=test_group)
        status_b = get_automation_status(group=other_group)

        assert status_a["oncall_eligible_users"] == 1
        assert status_a["shift_eligible_users"] == 1
        assert status_b["oncall_eligible_users"] == 2
        assert status_b["shift_eligible_users"] == 2

    def test_include_next_available_false_skips_computation(self, test_app, test_group):
        from app.utils.automation import get_automation_status

        status = get_automation_status(group=test_group, include_next_available=False)
        assert status["next_available_oncall_date"] is None

    def test_next_available_oncall_date_does_not_leak_across_groups(
        self, test_app, test_group
    ):
        """Regression test, same class as
        TestGetOnCallForDateGroupScoping above: in per_group mode two
        groups can have a concurrent on-call for the same anchor week -
        the per-group "next available" computation must not see the
        other group's on-call and think this group's slot is taken."""
        from app.utils.automation import get_automation_status

        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        anchor_start = datetime(2023, 12, 1, 21, 0)  # Friday 21:00
        anchor_end = anchor_start + timedelta(days=7, hours=-14)
        db.session.add(
            OnCall(user_id=user_b.id, start_time=anchor_start, end_time=anchor_end)
        )
        db.session.commit()

        status_a = get_automation_status(group=test_group)

        # test_group's own slot for that same Friday is still free -
        # only other_group's user is on call - so it must NOT be
        # reported as unavailable just because *a* on-call exists for
        # that instant.
        assert status_a["next_available_oncall_date"] is not None
