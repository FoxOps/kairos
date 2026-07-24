"""
Tests for AutomationAdminService.generate_full()'s scheduling_mode
branching: "shared" (default) keeps pooling every eligible group into
one generation pass, "per_group" runs one independent pass per
eligible Group instead (see app/utils/automation/*'s new `group`
parameter and its docstrings for what "independent" means in
practice - e.g. concurrent on-calls, one per group, for the same
week).
"""

from datetime import date

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, User


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

        SettingsService.set_scheduling_mode("per_group")

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
