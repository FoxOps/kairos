"""
Tests for optional per-Group scoping of the automation generation
entry points - the piece of "per_group" scheduling mode
(SettingsService.get_scheduling_mode()) that partitions the eligible-
user pool so two groups don't compete for the same on-call/staffing
budget. Rule *values* (weekend/slots/spacing/anchor) stay org-wide in
this increment - only WHO is eligible is partitioned. group=None
(the default everywhere) must keep today's pooled behavior unchanged.
"""

from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, User
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
