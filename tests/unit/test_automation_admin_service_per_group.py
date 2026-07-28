"""
Tests for AutomationAdminService.generate_full()'s shift/oncall
scheduling_mode branching: "shared" (default) keeps pooling every
eligible group into one generation pass, "per_group" runs one
independent pass per eligible Group instead (see
app/utils/automation/*'s new `group` parameter and its docstrings for
what "independent" means in practice - e.g. concurrent on-calls, one
per group, for the same week). Shift and on-call modes are
independent settings - each test below only flips the one relevant
to what it's asserting.
"""

from datetime import date

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, User


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


class TestGenerateFullSchedulingMode:
    def test_shared_mode_pools_every_group(self, test_app, test_group):
        from app.services.automation_admin_service import AutomationAdminService

        other_group = Group(
            name="Other", is_part_of_oncall=True, is_part_of_schedule=True
        )
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        result = AutomationAdminService.generate_full(friday, friday, [], dry_run=False)

        # Pooled: exactly one on-call for the single Friday, drawn from
        # both groups' users combined.
        assert len(result.oncalls) == 1
        assert result.oncalls[0].user_id in {user_a.id, user_b.id}

    def test_per_group_mode_runs_independent_generation_per_group(
        self, test_app, test_group
    ):
        from app.services import SettingsService
        from app.services.automation_admin_service import AutomationAdminService

        SettingsService.set_oncall_scheduling_mode("per_group")

        other_group = Group(
            name="Other", is_part_of_oncall=True, is_part_of_schedule=True
        )
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        result = AutomationAdminService.generate_full(friday, friday, [], dry_run=False)

        # Independent: each group ran its own solve for the same
        # Friday, so both users end up on-call concurrently.
        assert {o.user_id for o in result.oncalls} == {user_a.id, user_b.id}
        assert len(result.oncalls) == 2

    def test_shift_mode_does_not_affect_oncall_pooling(self, test_app, test_group):
        """Flipping shift_scheduling_mode alone must not make on-call
        generation per_group too - the two settings are independent,
        not a single combined switch."""
        from app.services import SettingsService
        from app.services.automation_admin_service import AutomationAdminService

        SettingsService.set_shift_scheduling_mode("per_group")

        other_group = Group(
            name="Other", is_part_of_oncall=True, is_part_of_schedule=True
        )
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        result = AutomationAdminService.generate_full(friday, friday, [], dry_run=False)

        # On-call mode is still "shared" (default): pooled, one on-call
        # for the Friday, despite shift mode being "per_group".
        assert len(result.oncalls) == 1
        assert result.oncalls[0].user_id in {user_a.id, user_b.id}


class TestRefreshShiftsSchedulingMode:
    """AutomationAdminService.refresh_shifts() ("Rafraîchir") used to
    always pool every eligible user org-wide regardless of
    shift_scheduling_mode/oncall_scheduling_mode, unlike generate_full()
    above - same discriminator style: a pooled pass vs one independent
    pass per group produces observably different results for the exact
    same input, proving the loop actually ran independently rather than
    just not crashing."""

    def test_fill_gaps_shared_mode_pools_oncall(self, test_app, test_group):
        from app.services.automation_admin_service import AutomationAdminService

        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        result = AutomationAdminService.refresh_shifts(
            friday, friday, oncall_mode="fill_gaps"
        )

        oncalls = OnCall.query.all()
        assert len(oncalls) == 1
        assert oncalls[0].user_id in {user_a.id, user_b.id}
        assert result.oncall_unfilled_dates == []

    def test_fill_gaps_per_group_mode_fills_independently(self, test_app, test_group):
        from app.services import SettingsService
        from app.services.automation_admin_service import AutomationAdminService

        SettingsService.set_oncall_scheduling_mode("per_group")

        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        AutomationAdminService.refresh_shifts(friday, friday, oncall_mode="fill_gaps")

        oncalls = OnCall.query.all()
        assert {o.user_id for o in oncalls} == {user_a.id, user_b.id}
        assert len(oncalls) == 2

    def test_regenerate_shared_mode_pools_oncall(self, test_app, test_group):
        from app.services.automation_admin_service import AutomationAdminService

        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        AutomationAdminService.refresh_shifts(friday, friday, oncall_mode="regenerate")

        oncalls = OnCall.query.all()
        assert len(oncalls) == 1
        assert oncalls[0].user_id in {user_a.id, user_b.id}

    def test_regenerate_per_group_mode_regenerates_independently(
        self, test_app, test_group
    ):
        from app.services import SettingsService
        from app.services.automation_admin_service import AutomationAdminService

        SettingsService.set_oncall_scheduling_mode("per_group")

        other_group = Group(name="Other", is_part_of_oncall=True)
        db.session.add(other_group)
        db.session.commit()
        user_a = _make_user("A", "a@test.com", test_group)
        user_b = _make_user("B", "b@test.com", other_group)

        friday = date(2023, 12, 1)
        AutomationAdminService.refresh_shifts(friday, friday, oncall_mode="regenerate")

        oncalls = OnCall.query.all()
        assert {o.user_id for o in oncalls} == {user_a.id, user_b.id}
        assert len(oncalls) == 2

    def test_shift_recompute_per_group_mode_runs_independently(
        self, test_app, test_group
    ):
        """With no on-call context, the 2-person special case forces
        SHIFT_07_15 for both people (see handle_two_users_case()); the
        3+ pooled branch instead defaults everyone to SHIFT_09_17
        (determine_shift_for_user() rule 3) except one person bumped to
        07h-15h for minimum coverage (rule 7). 2 groups of 2 users each:
        under "per_group", each pair independently hits the 2-person
        branch -> all 4 end up on 07h-15h. Under "shared", the pooled
        4-person pass hits the 3+ branch instead -> only 1 of the 4 is
        on 07h-15h. This difference is the proof the loop actually ran
        once per group instead of pooling everyone into one pass."""
        from app.models import Shift
        from app.services import SettingsService
        from app.services.automation_admin_service import AutomationAdminService

        SettingsService.set_shift_scheduling_mode("per_group")

        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", test_group)
        _make_user("C", "c@test.com", other_group)
        _make_user("D", "d@test.com", other_group)

        monday = date(2023, 12, 4)
        AutomationAdminService.refresh_shifts(monday, monday, oncall_mode="none")

        shifts = Shift.query.all()
        assert len(shifts) == 4
        assert all(s.start_time.hour == 7 for s in shifts)

    def test_shift_recompute_shared_mode_pools(self, test_app, test_group):
        from app.models import Shift
        from app.services.automation_admin_service import AutomationAdminService

        other_group = Group(name="Other", is_part_of_schedule=True)
        db.session.add(other_group)
        db.session.commit()
        _make_user("A", "a@test.com", test_group)
        _make_user("B", "b@test.com", test_group)
        _make_user("C", "c@test.com", other_group)
        _make_user("D", "d@test.com", other_group)

        monday = date(2023, 12, 4)
        AutomationAdminService.refresh_shifts(monday, monday, oncall_mode="none")

        shifts = Shift.query.all()
        assert len(shifts) == 4
        assert sum(1 for s in shifts if s.start_time.hour == 7) == 1
        assert sum(1 for s in shifts if s.start_time.hour == 9) == 3
