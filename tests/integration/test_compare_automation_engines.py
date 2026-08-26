"""Phase 4 tests: scripts/compare_automation_engines.py's report builder
correctly distinguishes "legacy_dry_run_self_inconsistency" (defect #1
- legacy's shift preview reads real on-calls from the DB while its own
on-call preview, computed moments earlier in the same call, was never
persisted) from genuine "algorithm_difference" disagreements, and never
manufactures false on-call disagreements from the two engines' differing
(but each intentional) group_id semantics.

Exercises AutomationAdminService._generate_full_legacy() directly, NOT
generate_full() - phase 6 retargeted generate_full(dry_run=True) itself
to the new engine, so it can no longer demonstrate defect #1 (that's
the point of phase 6); _generate_full_legacy() keeps the actual legacy
algorithm reachable for this comparison until phase 8 deletes it."""

from datetime import date, datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, OnCall, User
from app.services.automation_admin_service import AutomationAdminService
from app.services.settings_service import SettingsService
from app.utils.automation.planner import adapters, plan_schedule
from scripts.compare_automation_engines import build_comparison_report


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


def _run_comparison(start_date, end_date):
    # _generate_full_legacy, not generate_full: phase 6 retargeted
    # generate_full(dry_run=True) itself to the new engine, so calling
    # it here would compare the new engine against itself.
    legacy = AutomationAdminService._generate_full_legacy(
        start_date, end_date, rotation_order_ids=[], dry_run=True
    )
    db.session.rollback()
    request = adapters.build_planning_request(start_date, end_date)
    new_plan = plan_schedule(request)
    published_oncall_dates = {
        friday for (friday, _group_id) in request.published_oncalls
    }
    return build_comparison_report(legacy, new_plan, published_oncall_dates)


class TestCompareAutomationEnginesReproducesDefect1:
    def test_empty_window_flags_legacy_dry_run_self_inconsistency(self, test_app):
        """No existing on-calls in the target window at all - the exact
        condition that triggers defect #1 in the legacy engine's own
        dry-run preview."""
        group_a = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        group_b = _make_group("B", is_part_of_schedule=True, is_part_of_oncall=True)
        SettingsService.set_oncall_scheduling_mode("per_group")
        for i in range(2):
            _make_user(f"A{i}", f"a{i}@x.com", group_a)
            _make_user(f"B{i}", f"b{i}@x.com", group_b)

        report = _run_comparison(date(2026, 9, 4), date(2026, 9, 30))

        assert report["oncall"]["disagree"] == {}
        assert report["oncall"]["only_in_legacy"] == {}
        assert report["oncall"]["only_in_new"] == {}
        assert len(report["likely_defect_1"]) > 0
        assert all(
            entry["category"] == "legacy_dry_run_self_inconsistency"
            for entry in report["likely_defect_1"]
        )

    def test_pre_existing_oncalls_do_not_flag_self_inconsistency(self, test_app):
        """When on-calls already exist for the window, legacy's own
        dry-run shift preview reads the SAME on-calls its own dry-run
        on-call preview would (re)produce - internally consistent, so
        the classifier must not flag it as the defect-1 pattern (any
        remaining shift disagreement here is a genuine algorithm
        difference, not this specific known inconsistency)."""
        group = _make_group("A", is_part_of_schedule=True, is_part_of_oncall=True)
        users = [_make_user(f"U{i}", f"u{i}@x.com", group) for i in range(3)]

        fridays = [
            (datetime(2026, 9, 4, 21, 0), datetime(2026, 9, 11, 7, 0)),
            (datetime(2026, 9, 11, 21, 0), datetime(2026, 9, 18, 7, 0)),
            (datetime(2026, 9, 18, 21, 0), datetime(2026, 9, 25, 7, 0)),
            (datetime(2026, 9, 25, 21, 0), datetime(2026, 10, 2, 7, 0)),
        ]
        for i, (start, end) in enumerate(fridays):
            db.session.add(
                OnCall(
                    user_id=users[i % len(users)].id,
                    start_time=start,
                    end_time=end,
                    group_id=group.id,
                )
            )
        db.session.commit()

        report = _run_comparison(date(2026, 9, 4), date(2026, 9, 30))

        assert report["oncall"]["disagree"] == {}
        assert len(report["likely_defect_1"]) == 0
