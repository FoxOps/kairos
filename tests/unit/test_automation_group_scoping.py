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
from app.models import AutomationRule, Group, OnCall, ShiftType, User
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation


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

        eligible = OnCallAutomation.get_eligible_users()
        assert {u.id for u in eligible} == {u1.id, u2.id}

    def test_group_given_restricts_to_that_group(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        eligible = OnCallAutomation.get_eligible_users(group=test_group)
        assert {u.id for u in eligible} == {u1.id}


class TestGetUsersInScheduleGroupsGroupScoping:
    def test_group_given_restricts_to_that_group(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", other_group)

        users = AdvancedShiftAutomation.get_users_in_schedule_groups(group=test_group)
        assert {u.id for u in users} == {u1.id}


class TestGenerateOnCallScheduleGroupScoping:
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
        next_friday = friday + timedelta(days=7)

        oncalls_a, _msgs_a, _unfilled_a = OnCallAutomation.generate_oncall_schedule(
            friday, next_friday, dry_run=False, group=test_group
        )
        oncalls_b, _msgs_b, _unfilled_b = OnCallAutomation.generate_oncall_schedule(
            friday, next_friday, dry_run=False, group=other_group
        )

        assert len(oncalls_a) == 1
        assert oncalls_a[0].user_id == u1.id
        assert len(oncalls_b) == 1
        assert oncalls_b[0].user_id == u2.id

    def test_rotation_order_ids_outside_group_are_ignored(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        oncalls, _msgs, _unfilled = OnCallAutomation.generate_oncall_schedule(
            friday,
            friday,
            rotation_order_ids=[u2.id, u1.id],
            dry_run=False,
            group=test_group,
        )

        assert len(oncalls) == 1
        assert oncalls[0].user_id == u1.id


class TestGetOnCallForDateGroupScoping:
    def test_does_not_return_a_different_groups_concurrent_oncall(
        self, test_app, test_group
    ):
        """Regression test: in per_group mode, two groups can have a
        concurrent on-call for the same anchor week - get_oncall_for_date()
        must not let group A's shift-role determination (rule 1, the
        13h-21h slot) pick up group B's on-call by an unscoped
        `.first()`, which would misattribute the slot within group A's
        own generation."""
        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        anchor_start = datetime(2023, 12, 1, 21, 0)  # Friday 21:00
        anchor_end = anchor_start + timedelta(days=7, hours=-14)
        db.session.add(
            OnCall(user_id=user_a.id, start_time=anchor_start, end_time=anchor_end)
        )
        db.session.add(
            OnCall(user_id=user_b.id, start_time=anchor_start, end_time=anchor_end)
        )
        db.session.commit()

        monday = date(2023, 12, 4)
        oncall_for_a = AdvancedShiftAutomation.get_oncall_for_date(
            monday, group=test_group
        )
        oncall_for_b = AdvancedShiftAutomation.get_oncall_for_date(
            monday, group=other_group
        )

        assert oncall_for_a.user_id == user_a.id
        assert oncall_for_b.user_id == user_b.id


class TestGenerateFullScheduleGroupScoping:
    def test_two_groups_get_independent_shift_generation(self, test_app, test_group):
        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        u1 = _make_user("A", "a@test.com", test_group)
        u2 = _make_user("B", "b@test.com", other_group)

        monday = date(2023, 12, 4)

        shifts_a, _msgs_a, _unfilled_a = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=test_group
        )
        shifts_b, _msgs_b, _unfilled_b = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=other_group
        )

        assert {s.user_id for s in shifts_a} == {u1.id}
        assert {s.user_id for s in shifts_b} == {u2.id}


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

        shifts_a, _msgs_a, _unfilled_a = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=test_group
        )
        shifts_b, _msgs_b, _unfilled_b = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=other_group
        )

        assert shifts_a == []
        assert len(shifts_b) == 1


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
        # Only 1 user available per group -> the "sole user" path, which
        # always resolves the rotation-slot role (SHIFT_07_15).
        shifts_a, _msgs_a, _unfilled_a = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=test_group
        )
        shifts_b, _msgs_b, _unfilled_b = AdvancedShiftAutomation.generate_full_schedule(
            monday, monday, dry_run=False, group=other_group
        )

        assert shifts_a[0].shift_type_id == custom_type.id
        assert shifts_b[0].shift_type_id != custom_type.id


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

        monday = date(2023, 12, 4)
        friday = date(2023, 12, 1)

        oncalls_a, _msgs_a, _unfilled_a = OnCallAutomation.generate_oncall_schedule(
            monday, monday, dry_run=False, group=test_group
        )
        oncalls_b, _msgs_b, _unfilled_b = OnCallAutomation.generate_oncall_schedule(
            friday, friday, dry_run=False, group=other_group
        )

        assert len(oncalls_a) == 1
        assert oncalls_a[0].user_id == u1.id
        assert oncalls_a[0].start_time == datetime(2023, 12, 4, 21, 0)
        assert len(oncalls_b) == 1
        assert oncalls_b[0].user_id == u2.id
        assert oncalls_b[0].start_time == datetime(2023, 12, 1, 21, 0)


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
        next_friday = friday + timedelta(days=7)

        oncalls_a, _msgs_a, unfilled_a = OnCallAutomation.generate_oncall_schedule(
            friday, next_friday, dry_run=False, group=test_group
        )

        assert len(oncalls_a) == 2
        assert unfilled_a == []
        assert {o.user_id for o in oncalls_a} == {u1.id}


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
