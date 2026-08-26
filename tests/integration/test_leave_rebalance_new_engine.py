"""Phase 7 follow-up: with SettingsService.get_new_automation_engine_enabled()
on, AdvancedShiftAutomation.rebalance_after_leave() (the automatic,
Leave-creation-triggered rebalance) routes through the new planner +
AutomationApplyService.apply_plan(atomic=False) instead of its own
legacy per-day/per-section SAVEPOINT code. dry_run=True (never used by
LeaveService in production, only by direct test/inspection callers)
always stays on the legacy path regardless of the toggle - see
rebalance_after_leave()'s own docstring."""

from datetime import date, datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, Shift, User
from app.models.generation_run import GenerationRun
from app.repositories.leave_repository import LeaveRepository
from app.services.leave_service import LeaveService
from app.services.settings_service import SettingsService
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation


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


class TestRebalanceWithoutOverlappingOnCall:
    def test_shifts_recomputed_oncalls_untouched(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        leave, regenerated_shifts = LeaveService.add_leave(
            users[0], date(2026, 9, 8), date(2026, 9, 10)
        )

        assert leave is not None
        assert regenerated_shifts is not None
        assert OnCall.query.count() == 0
        run = GenerationRun.query.one()
        assert run.outcome == "applied"


class TestRebalanceWithOverlappingOnCall:
    def test_oncall_regenerated_and_shifts_recomputed(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        overlapping = OnCall(
            user_id=users[0].id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group.id,
        )
        db.session.add(overlapping)
        db.session.commit()
        overlapping_id = overlapping.id

        leave, regenerated_shifts = LeaveService.add_leave(
            users[0], date(2026, 9, 8), date(2026, 9, 10)
        )

        assert leave is not None
        assert regenerated_shifts is not None
        # The leave's own overlapping on-call must be gone (either
        # reassigned to someone else or removed - either way, no longer
        # this exact row) - the whole point of the rebalance.
        assert db.session.get(OnCall, overlapping_id) is None
        assert OnCall.query.count() >= 1
        run = GenerationRun.query.one()
        assert run.outcome == "applied"


class TestRebalanceScopedToLeaveOwnersGroupUnderPerGroupMode:
    def test_other_groups_schedule_is_never_touched(self, test_app):
        group_a = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        group_b = _make_group("B", is_part_of_schedule=True, is_part_of_oncall=True)
        users_a = [_make_user(f"A{i}", f"a{i}@x.com", group_a) for i in range(3)]
        users_b = [_make_user(f"B{i}", f"b{i}@x.com", group_b) for i in range(3)]
        SettingsService.set_oncall_scheduling_mode("per_group")
        SettingsService.set_shift_scheduling_mode("per_group")
        SettingsService.set_new_automation_engine_enabled(True)

        b_oncall = OnCall(
            user_id=users_b[0].id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group_b.id,
        )
        db.session.add(b_oncall)
        db.session.commit()
        b_oncall_id = b_oncall.id

        b_shift_count_before = Shift.query.filter(
            Shift.user_id.in_([u.id for u in users_b])
        ).count()

        leave, regenerated_shifts = LeaveService.add_leave(
            users_a[0], date(2026, 9, 8), date(2026, 9, 10)
        )

        assert leave is not None
        assert regenerated_shifts is not None
        # Group B's own on-call and shifts must be completely untouched
        # by group A's leave-triggered rebalance under "per_group" mode.
        assert db.session.get(OnCall, b_oncall_id) is not None
        assert (
            Shift.query.filter(Shift.user_id.in_([u.id for u in users_b])).count()
            == b_shift_count_before
        )


class TestDryRunAlwaysStaysOnLegacyRegardlessOfToggle:
    def test_dry_run_true_ignores_the_toggle(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        leave = LeaveRepository.create(users[0].id, date(2026, 9, 8), date(2026, 9, 10))
        db.session.commit()

        AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=True)

        # dry_run never persists on either path, but the real signal
        # here is that no GenerationRun row exists - proof the
        # new-engine (apply_plan-based) path was never reached.
        assert GenerationRun.query.count() == 0
        assert OnCall.query.count() == 0
        assert Shift.query.count() == 0
