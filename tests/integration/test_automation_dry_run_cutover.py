"""Phase 6 tests: AutomationAdminService.generate_full(dry_run=True)
routes through the new pure planner (app/utils/automation/planner)
instead of the legacy engine, via a presentation shim
(_generate_result_from_plan) that must produce a GenerateResult
full_dry_run.html can render with zero template changes."""

from datetime import date, datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, Shift, User
from app.services.automation_admin_service import AutomationAdminService


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


class TestGenerateFullDryRunUsesNewEngine:
    def test_dry_run_never_persists_and_exposes_working_relationships(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)

        result = AutomationAdminService.generate_full(
            date(2026, 9, 4), date(2026, 9, 17), rotation_order_ids=[], dry_run=True
        )

        assert result.dry_run is True
        assert result.oncalls
        assert result.shifts
        # .user/.shift_type must resolve to real data (not None) for
        # the template's oncall.user.name/shift.shift_type.label reads.
        for oncall in result.oncalls:
            assert oncall.user is not None
            assert oncall.user.name.startswith("U")
        for shift in result.shifts:
            assert shift.user is not None
            assert shift.shift_type is not None
            assert shift.shift_type.label

        assert OnCall.query.count() == 0
        assert Shift.query.count() == 0

    def test_preview_objects_never_pollute_real_user_relationships(self, test_app):
        """The fix for a real bug found while building this: assigning
        the relationship directly on a transient ORM instance
        (`oncall.user = user`) does not risk persistence, but DOES
        silently append the fake preview object into the real user's
        own in-memory .shifts/.on_calls collection via the bidirectional
        backref - anything else reading that collection later in the
        same request would see it. The shim uses plain SimpleNamespace
        objects instead, which have no relationships to pollute."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        user = _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)

        AutomationAdminService.generate_full(
            date(2026, 9, 4), date(2026, 9, 10), rotation_order_ids=[], dry_run=True
        )

        assert len(user.shifts) == 0
        assert len(user.on_calls) == 0

    def test_generate_full_legacy_still_directly_callable(self, test_app):
        """scripts/compare_automation_engines.py needs the actual
        legacy algorithm reachable even though generate_full() itself
        no longer routes dry_run=True there - this is the seam that
        keeps the comparison tool meaningful post-cutover."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)

        legacy_result = AutomationAdminService._generate_full_legacy(
            date(2026, 9, 4), date(2026, 9, 17), rotation_order_ids=[], dry_run=True
        )
        assert legacy_result.dry_run is True
        # Legacy dry_run never persists either.
        assert OnCall.query.count() == 0
        assert Shift.query.count() == 0


class TestGenerateFullPersistsRotationOrder:
    """Real production bug: the new engine's rotation order is only
    ever read from AutomationConfig, never from whatever the admin
    currently has checked/ordered on the generation form itself - so
    clicking "Générer"/"Prévisualiser" without a separate, easy-to-miss
    prior "Sauvegarder l'ordre" click silently fell back to alphabetical
    order, and AutomationConfig could stay empty forever. generate_full()
    must now persist rotation_order_ids itself on every call."""

    def test_dry_run_persists_the_submitted_order_without_a_separate_save(
        self, test_app
    ):
        from app.models import AutomationConfig

        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]

        assert AutomationConfig.get_rotation_order() == []

        AutomationAdminService.generate_full(
            date(2026, 9, 4),
            date(2026, 9, 17),
            rotation_order_ids=[u.id for u in users],
            dry_run=True,
        )

        assert AutomationConfig.get_rotation_order() == [u.id for u in users]

    def test_dry_run_first_on_call_matches_rotation_order_first_entry(self, test_app):
        """The exact scenario reported by QA: with a fresh rotation (no
        prior on-call history), the first user in the configured order
        must be the first one actually put on-call - previously an
        arbitrary position, unrelated to the configured order, because
        AutomationConfig never actually got the submitted order."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(4)]

        result = AutomationAdminService.generate_full(
            date(2026, 8, 28),
            date(2026, 9, 4),
            rotation_order_ids=[u.id for u in users],
            dry_run=True,
        )

        first_oncall = min(result.oncalls, key=lambda o: o.start_time)
        assert first_oncall.user.id == users[0].id


class TestGenerateFullDryRunMessages:
    def test_unfilled_oncall_week_produces_warning_message(self, test_app):
        """2 users, min_spacing_weeks default 2: a 3-week window forces
        one week unfillable (both users already used, neither can
        legally repeat within the window) - same scenario as
        test_planner_oncall_scenarios.py's own spacing test."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)

        result = AutomationAdminService.generate_full(
            date(2026, 1, 2), date(2026, 1, 16), rotation_order_ids=[], dry_run=True
        )

        assert result.oncall_unfilled_dates
        assert any("[WARN]" in m for m in result.oncall_messages)

    def test_oncall_role_slot_on_transition_friday_is_never_a_rest_violation(
        self, test_app
    ):
        """Real production bug, fixed in shift_planner.py: the departing
        on-call holder is still assigned the mandatory on-call coverage
        shift (role_slot "oncall") on the very Friday their own on-call
        ends - that slot must never be treated as a rest_after_oncall
        violation (see shift_planner.py's `role_slot != "oncall"`
        guard), or the mandatory slot goes unfilled every single week
        for any org with this rule configured."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        from app.models import AutomationRule

        AutomationRule.set("rest_after_oncall", {"min_rest_hours": 12})
        user = _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)
        _make_user("U2", "u2@x.com", group)

        db.session.add(
            OnCall(
                user_id=user.id,
                start_time=datetime(2025, 12, 26, 21, 0),
                end_time=datetime(2026, 1, 2, 7, 0),
                group_id=group.id,
            )
        )
        db.session.commit()

        result = AutomationAdminService.generate_full(
            date(2026, 1, 2), date(2026, 1, 2), rotation_order_ids=[], dry_run=True
        )

        assert not any("Repos insuffisant" in m for m in result.shift_messages)
        assert not result.shift_unfilled_dates

    def test_rest_after_oncall_violation_produces_shift_message(self, test_app):
        """Same rule, but for a "default"/"rotation" role slot (an
        unrelated regular shift, not the on-call coverage slot itself)
        - this is rest_after_oncall's actual remaining target, still a
        hard exclusion. Org-wide (no group=), not per-group: scheduling
        mode defaults to "shared", under which a per-group rule
        override has no effect anywhere (documented app behavior) -
        this test is about message generation, not group-scoping
        semantics."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        from app.models import AutomationRule

        AutomationRule.set("rest_after_oncall", {"min_rest_hours": 240})
        user = _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)
        _make_user("U2", "u2@x.com", group)

        # On-call ending Friday 07:00 - the following Monday's regular
        # shift is still within a 240h (10-day) rest requirement.
        db.session.add(
            OnCall(
                user_id=user.id,
                start_time=datetime(2025, 12, 26, 21, 0),
                end_time=datetime(2026, 1, 2, 7, 0),
                group_id=group.id,
            )
        )
        db.session.commit()

        result = AutomationAdminService.generate_full(
            date(2026, 1, 5), date(2026, 1, 5), rotation_order_ids=[], dry_run=True
        )

        assert any("Repos insuffisant" in m for m in result.shift_messages)
