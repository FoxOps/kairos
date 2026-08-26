"""Phase 5 tests: AutomationApplyService.apply_plan()'s atomic apply
and its interaction with the rest of the planner pipeline.

Not wired into any route yet - these tests exercise the service
directly, matching how the rest of this rework's phases were verified
before route wiring lands."""

from datetime import date, datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import GenerationRun, Group, OnCall, Shift, ShiftType, User
from app.services.automation_apply_service import AutomationApplyService
from app.utils.automation.planner import adapters, plan_schedule
from app.utils.automation.planner.types import (
    FairnessMetrics,
    ProposedShift,
    ScheduleDiffEntry,
    SchedulePlan,
)


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


class TestApplyPlanEndToEnd:
    def test_apply_then_reapply_is_idempotent(self, test_app):
        """Re-planning and re-applying an already-applied window must
        be a no-op - the direct regression test for the self-conflict
        bug found while building this: existing_oncalls used to include
        the window's own just-applied on-calls, making the solver treat
        a user's own on-call as a conflict against itself on the next
        plan, forcing a spurious reassignment."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)

        start, end = date(2026, 9, 4), date(2026, 9, 17)
        plan = plan_schedule(adapters.build_planning_request(start, end))
        first = AutomationApplyService.apply_plan(plan)
        assert first.success is True
        assert first.oncalls_created > 0
        assert first.shifts_created > 0

        oncall_count = OnCall.query.count()
        shift_count = Shift.query.count()

        plan2 = plan_schedule(adapters.build_planning_request(start, end))
        assert all(o.change_type == "unchanged" for o in plan2.oncalls)
        assert all(s.change_type == "unchanged" for s in plan2.shifts)

        second = AutomationApplyService.apply_plan(plan2)
        assert second.success is True
        assert second.oncalls_created == 0
        assert second.oncalls_deleted == 0
        assert second.oncalls_reassigned == 0
        assert second.shifts_created == 0
        assert second.shifts_deleted == 0
        assert second.shifts_reassigned == 0
        assert OnCall.query.count() == oncall_count
        assert Shift.query.count() == shift_count

    def test_created_rows_snapshot_the_assigned_users_real_group(self, test_app):
        """OnCall.group_id/Shift.group_id must be the assigned user's
        actual group (matching the legacy engine's own convention and
        the phase-2 migration's stated intent), NOT
        ProposedOnCall/ProposedShift.group_id, which is the generation
        SCOPE (None in "shared" mode)."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)

        plan = plan_schedule(
            adapters.build_planning_request(date(2026, 9, 4), date(2026, 9, 10))
        )
        assert plan.oncalls  # sanity: something was actually proposed
        result = AutomationApplyService.apply_plan(plan)
        assert result.success is True

        for oncall in OnCall.query.all():
            assert oncall.group_id == group.id
        for shift in Shift.query.all():
            assert shift.group_id == group.id

    def test_locked_oncall_is_never_touched_by_apply(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        u0 = _make_user("U0", "u0@x.com", group)
        _make_user("U1", "u1@x.com", group)

        locked = OnCall(
            user_id=u0.id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group.id,
            locked=True,
        )
        db.session.add(locked)
        db.session.commit()
        locked_id = locked.id

        plan = plan_schedule(
            adapters.build_planning_request(date(2026, 9, 4), date(2026, 9, 10))
        )
        assert plan.safe_to_apply is True
        result = AutomationApplyService.apply_plan(plan)
        assert result.success is True

        still_there = db.session.get(OnCall, locked_id)
        assert still_there is not None
        assert still_there.user_id == u0.id


class TestApplyPlanRollback:
    def test_refuses_unsafe_plan_with_zero_writes(self, test_app):
        bad_plan = SchedulePlan(
            start_date=date(2026, 9, 4),
            end_date=date(2026, 9, 4),
            generated_at=datetime.now(),
            oncalls=(),
            shifts=(),
            unfilled=(),
            violations=(),
            fairness=FairnessMetrics(),
            diff=(),
            safe_to_apply=False,
            safe_to_apply_reasons=("simulated unsafe plan",),
            input_fingerprint="deadbeef",
        )
        result = AutomationApplyService.apply_plan(bad_plan)
        assert result.success is False
        assert result.generation_run_id is None
        assert GenerationRun.query.count() == 0

    def test_mid_apply_failure_rolls_back_the_whole_transaction(self, test_app):
        """Forces a real uq_shift_user_date IntegrityError partway
        through a hand-built plan's diff walk (two "added" entries for
        the identical (user_id, date)) - deterministic and engine-
        agnostic, unlike simulating a killed connection. Asserts the
        first (otherwise legitimate) insert from the same transaction
        is rolled back too, not just the failing second one, and an
        unrelated pre-existing row is untouched."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        user = _make_user("U0", "u0@x.com", group)
        shift_type = ShiftType(name="t1", label="T1", start_hour=9, end_hour=17)
        db.session.add(shift_type)
        db.session.commit()

        control_date = date(2026, 9, 1)
        control = Shift(
            user_id=user.id,
            shift_type_id=shift_type.id,
            date=control_date,
            start_time=datetime(2026, 9, 1, 9, 0),
            end_time=datetime(2026, 9, 1, 17, 0),
        )
        db.session.add(control)
        db.session.commit()

        target_date = date(2026, 9, 8)
        proposed = ProposedShift(
            date=target_date,
            user_id=user.id,
            shift_type_id=shift_type.id,
            start_time=datetime(2026, 9, 8, 9, 0),
            end_time=datetime(2026, 9, 8, 17, 0),
            group_id=None,
            role_slot="default",
            change_type="added",
        )
        diff = (
            ScheduleDiffEntry(
                kind="shift",
                date=target_date,
                group_id=None,
                published_user_id=None,
                proposed_user_id=user.id,
                change_type="added",
            ),
            ScheduleDiffEntry(
                kind="shift",
                date=target_date,
                group_id=None,
                published_user_id=None,
                proposed_user_id=user.id,
                change_type="added",
            ),
        )
        plan = SchedulePlan(
            start_date=target_date,
            end_date=target_date,
            generated_at=datetime.now(),
            oncalls=(),
            shifts=(proposed,),
            unfilled=(),
            violations=(),
            fairness=FairnessMetrics(),
            diff=diff,
            safe_to_apply=True,
            safe_to_apply_reasons=(),
            input_fingerprint="deadbeef",
        )

        result = AutomationApplyService.apply_plan(plan)

        assert result.success is False
        assert result.error is not None
        run = db.session.get(GenerationRun, result.generation_run_id)
        assert run is not None
        assert run.outcome == "failed"
        assert Shift.query.filter_by(date=target_date).count() == 0
        assert Shift.query.filter_by(date=control_date).count() == 1
