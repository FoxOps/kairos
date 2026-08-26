"""Phase 7 tests: with SettingsService.get_new_automation_engine_enabled()
on, AutomationAdminService.generate_full(dry_run=False) and
refresh_shifts() route real writes through the new planner +
AutomationApplyService.apply_plan() instead of the legacy engine. Off
(the default), both keep using the legacy engine unchanged - this is a
rollback-without-a-code-revert toggle, not a one-way migration.

Also covers a real bug found while building this: PlanningRequest's
single start_date used to drive both on-call Friday search (which
legitimately needs widening to the covering Friday) and the shift
day-loop start (which must NOT widen, or real generation would touch/
delete shift rows before the caller's literal requested start) - see
PlanningRequest.shift_start_date.

AdvancedShiftAutomation.rebalance_after_leave() (the automatic
leave-triggered rebalance) is ALSO gated by this same toggle, as of the
phase 7 follow-up - see test_leave_rebalance_new_engine.py for its own
dedicated coverage (it needed a non-atomic, per-entry-isolated
apply_plan() mode, since its legacy per-day/per-section SAVEPOINT
isolation has no equivalent in apply_plan()'s default all-or-nothing
transaction model)."""

from datetime import date, datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, Shift, User
from app.models.generation_run import GenerationRun
from app.services.automation_admin_service import AutomationAdminService
from app.services.leave_service import LeaveService
from app.services.settings_service import SettingsService


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


class TestGenerateFullRealGenerationCutover:
    def test_toggle_off_keeps_using_legacy_engine(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)

        AutomationAdminService.generate_full(
            date(2026, 9, 7), date(2026, 9, 18), rotation_order_ids=[], dry_run=False
        )

        # The legacy engine never writes a GenerationRun row - only
        # AutomationApplyService.apply_plan() does.
        assert GenerationRun.query.count() == 0
        assert OnCall.query.count() > 0
        assert Shift.query.count() > 0

    def test_toggle_on_applies_via_new_engine_and_records_generation_run(
        self, test_app
    ):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)
        SettingsService.set_new_automation_engine_enabled(True)

        result = AutomationAdminService.generate_full(
            date(2026, 9, 7), date(2026, 9, 18), rotation_order_ids=[], dry_run=False
        )

        assert result.dry_run is False
        assert OnCall.query.count() > 0
        assert Shift.query.count() > 0
        run = GenerationRun.query.one()
        assert run.outcome == "applied"

    def test_shift_start_date_not_widened_for_real_generation(self, test_app):
        """start_date is a Wednesday, deliberately mid-on-call-week -
        align_regeneration_start() widens the on-call side back to the
        covering Friday (up to 5 days earlier). Before the
        shift_start_date fix, shift planning inherited that same
        widened start, so real generation would create/touch Shift rows
        on those extra days the caller never asked to regenerate."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)
        SettingsService.set_new_automation_engine_enabled(True)

        wednesday = date(2026, 9, 9)
        assert wednesday.weekday() == 2

        AutomationAdminService.generate_full(
            wednesday, date(2026, 9, 18), rotation_order_ids=[], dry_run=False
        )

        assert Shift.query.filter(Shift.date < wednesday).count() == 0

    def test_boundary_oncall_not_spuriously_removed_when_start_falls_mid_week(
        self, test_app
    ):
        """A published on-call already covers the boundary week (Friday
        before `start_date` through the next Friday). Real generation
        starting mid-week must not misdiff this as "removed" just
        because the on-call Friday search had to widen backward to see
        it - the diff/apply must still treat it as unchanged."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        boundary_oncall = OnCall(
            user_id=users[0].id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group.id,
        )
        db.session.add(boundary_oncall)
        db.session.commit()
        boundary_id = boundary_oncall.id

        AutomationAdminService.generate_full(
            date(2026, 9, 9), date(2026, 9, 18), rotation_order_ids=[], dry_run=False
        )

        assert db.session.get(OnCall, boundary_id) is not None

    def test_apply_failure_raises_instead_of_returning_a_result(
        self, test_app, monkeypatch
    ):
        """apply_plan() converts a failure into ApplyResult(success=False)
        rather than raising (see test_automation_apply_service.py for
        how a real failure - e.g. a forced IntegrityError - is produced
        there) - _generate_full_new_engine() must itself raise on that
        so admin_automation_routes.py's existing
        `except Exception as e: flash(...)` handling surfaces it without
        any route changes. Forcing a real apply failure through a full
        plan→apply cycle here would duplicate that other test file's
        own coverage; monkeypatching apply_plan's return value isolates
        exactly the one thing this test is actually about: the wiring
        between an unsuccessful ApplyResult and generate_full()'s own
        exception-based contract."""
        from app.services import automation_apply_service

        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)
        SettingsService.set_new_automation_engine_enabled(True)

        monkeypatch.setattr(
            automation_apply_service.AutomationApplyService,
            "apply_plan",
            staticmethod(
                lambda plan, actor=None: automation_apply_service.ApplyResult(
                    success=False, error="forced failure for this test"
                )
            ),
        )

        try:
            AutomationAdminService.generate_full(
                date(2026, 9, 7),
                date(2026, 9, 18),
                rotation_order_ids=[],
                dry_run=False,
            )
            raise AssertionError("expected generate_full() to raise")
        except RuntimeError as e:
            assert "forced failure for this test" in str(e)

        # Nothing was written - the raise happens before any GenerateResult
        # is returned, and apply_plan itself was monkeypatched to a no-op.
        assert OnCall.query.count() == 0
        assert Shift.query.count() == 0


class TestRefreshShiftsRealGenerationCutover:
    def test_none_mode_leaves_oncalls_completely_untouched(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        existing_oncall = OnCall(
            user_id=users[0].id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group.id,
        )
        db.session.add(existing_oncall)
        db.session.commit()
        existing_id = existing_oncall.id

        result = AutomationAdminService.refresh_shifts(
            date(2026, 9, 7), date(2026, 9, 11), oncall_mode="none"
        )

        assert db.session.get(OnCall, existing_id) is not None
        assert OnCall.query.count() == 1
        assert result.oncall_messages == []
        assert result.oncall_unfilled_dates == []
        assert Shift.query.count() > 0

    def test_fill_gaps_mode_preserves_existing_and_fills_missing_friday(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]
        SettingsService.set_new_automation_engine_enabled(True)

        existing_oncall = OnCall(
            user_id=users[0].id,
            start_time=datetime(2026, 9, 4, 21, 0),
            end_time=datetime(2026, 9, 11, 7, 0),
            group_id=group.id,
        )
        db.session.add(existing_oncall)
        db.session.commit()
        existing_id = existing_oncall.id

        # 2026-09-11 through 2026-09-25 covers 3 Fridays (11/18/25), none
        # of them published yet - fill_gaps should fill all 3 without
        # touching the pre-existing one above (a 4th, already-published
        # on-call from 2026-09-04).
        AutomationAdminService.refresh_shifts(
            date(2026, 9, 11), date(2026, 9, 25), oncall_mode="fill_gaps"
        )

        assert db.session.get(OnCall, existing_id) is not None
        assert OnCall.query.count() == 4

    def test_regenerate_mode_allows_full_resolve(self, test_app):
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        for i in range(3):
            _make_user(f"U{i}", f"u{i}@x.com", group)
        SettingsService.set_new_automation_engine_enabled(True)

        result = AutomationAdminService.refresh_shifts(
            date(2026, 9, 7), date(2026, 9, 18), oncall_mode="regenerate"
        )

        assert OnCall.query.count() > 0
        assert result.oncall_messages_category == "danger"


class TestRebalanceAfterLeaveToggleGating:
    def test_toggle_off_never_uses_apply_plan(self, test_app):
        """Default (off): rebalance_after_leave() stays on its legacy
        per-day/per-section SAVEPOINT code - see
        test_leave_rebalance_new_engine.py for the toggle-on path."""
        group = _make_group("G", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]

        leave, regenerated_shifts = LeaveService.add_leave(
            users[0], date(2026, 9, 8), date(2026, 9, 10)
        )

        assert leave is not None
        assert regenerated_shifts is not None
        assert GenerationRun.query.count() == 0
