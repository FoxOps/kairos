#!/usr/bin/env python3
"""
Kairos - Compare the legacy automation engine against the new planner
=======================================================================

Diagnostic-only tool (phase 4 of the automation engine rework, see the
audit that motivated it). Runs the legacy
AutomationAdminService.generate_full(dry_run=True) preview and the new
pure planner (app/utils/automation/planner) over the SAME period and
DB state, then prints a structured JSON diff report.

DISAGREEMENT IS THE POINT OF THIS TOOL, NOT A FAILURE. The legacy
engine's own dry-run preview is known to diverge from what real
generation would produce (defect #1: the shift preview reads real
on-calls from the DB, not the in-memory on-call preview computed
moments earlier in the same call) - this script exists to make that
divergence visible and measurable, not to assert the two engines agree.
The report tags disagreements it can attribute specifically to that
known inconsistency as "legacy_dry_run_self_inconsistency", separate
from genuine algorithm differences ("algorithm_difference"). Exit code
is always 0 regardless of what the report contains - this is never
meant to gate CI.

Usage:
    python scripts/compare_automation_engines.py --start-date 2026-09-01 --end-date 2026-12-31

Read-only: rolls back any session state the legacy dry-run pass may
have flushed before building the new engine's request, and never
commits anything.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db  # noqa: E402


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_comparison_report(legacy, new_plan, published_oncall_dates: set) -> dict:
    """`legacy` is a GenerateResult (app/services/automation_admin_service.py),
    `new_plan` is a SchedulePlan (app/utils/automation/planner/types.py),
    `published_oncall_dates` is the set of Fridays that ACTUALLY have an
    on-call persisted in the DB right now (derived from the same
    `PlanningRequest.published_oncalls` the new engine's request used) -
    passed in separately because it must reflect real DB state, not
    either engine's own (possibly in-memory-only) preview output.
    Returns a JSON-serializable dict with independent "oncall"/"shift"
    diffs plus a "likely_defect_1" bucket.

    On-call rows are compared by date alone (user_id), NOT by
    (date, group_id): legacy's OnCall.group_id snapshots the assigned
    user's own current group, while the new planner's
    ProposedOnCall.group_id records the generation SCOPE the row was
    planned under (None in "shared" mode, regardless of the assigned
    user's real group) - these are different, both-intentional
    semantics, not a comparable identity. Keying on group_id here would
    manufacture false only_in_legacy/only_in_new noise for the exact
    same (date, user) assignment whenever scheduling mode is "shared".
    """
    legacy_oncalls = {o.start_time.date(): o.user_id for o in legacy.oncalls}
    new_oncalls = {
        o.friday: o.user_id for o in new_plan.oncalls if o.change_type != "unchanged"
    }

    legacy_shifts = {(s.date, s.user_id): s.shift_type_id for s in legacy.shifts}
    new_shifts = {
        (s.date, s.user_id): s.shift_type_id
        for s in new_plan.shifts
        if s.change_type != "unchanged"
    }

    oncall_diff = _diff_maps(legacy_oncalls, new_oncalls)
    shift_diff = _diff_maps(legacy_shifts, new_shifts)

    # A shift disagreement whose own week has NO on-call actually
    # persisted in the DB, but DOES have a new-engine on-call covering
    # it (computed purely in-memory, exactly like legacy's own dry-run
    # on-call preview would be), is the concrete fingerprint of defect
    # #1: legacy's shift preview reads real (absent) on-calls from the
    # DB - not the in-memory on-call preview computed moments earlier
    # in the very same call - while the new engine's shift planning
    # correctly sees its own in-memory on-call output instead.
    likely_defect_1 = []
    for (shift_date, user_id), entry in shift_diff["disagree"].items():
        week_has_published_oncall = any(
            friday <= shift_date < friday + timedelta(days=7)
            for friday in published_oncall_dates
        )
        week_has_new_oncall = any(
            friday <= shift_date < friday + timedelta(days=7) for friday in new_oncalls
        )
        if not week_has_published_oncall and week_has_new_oncall:
            entry["category"] = "legacy_dry_run_self_inconsistency"
            likely_defect_1.append({"date": shift_date, "user_id": user_id, **entry})
        else:
            entry["category"] = "algorithm_difference"

    return {
        "oncall": oncall_diff,
        "shift": shift_diff,
        "likely_defect_1": likely_defect_1,
    }


def _diff_maps(legacy: dict, new: dict) -> dict:
    only_in_legacy = {k: v for k, v in legacy.items() if k not in new}
    only_in_new = {k: v for k, v in new.items() if k not in legacy}
    disagree = {
        k: {"legacy": legacy[k], "new": new[k]}
        for k in legacy.keys() & new.keys()
        if legacy[k] != new[k]
    }
    return {
        "only_in_legacy": only_in_legacy,
        "only_in_new": only_in_new,
        "disagree": disagree,
    }


def _jsonable(obj):
    """Recursively converts tuple dict keys (e.g. `(date, group_id)`) to
    a JSON-safe string form - `build_comparison_report`'s own return
    value keeps real tuple keys throughout (so tests can assert against
    it directly); this conversion only happens at print time."""
    if isinstance(obj, dict):
        return {
            (str(k) if not isinstance(k, str) else k): _jsonable(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare the legacy automation engine against the new planner (diagnostic only)."
    )
    parser.add_argument("--start-date", required=True, type=_parse_date)
    parser.add_argument("--end-date", required=True, type=_parse_date)
    args = parser.parse_args()

    with app.app_context():
        from app.services.automation_admin_service import AutomationAdminService
        from app.utils.automation.planner import adapters, plan_schedule

        # Empty list, not None: get_rotation_order() only checks
        # truthiness (`if rotation_order_ids:`), so both fall through
        # identically to the saved AutomationConfig.get_rotation_order()
        # - matching build_planning_request's own rotation_order
        # derivation without passing it explicitly twice.
        legacy = AutomationAdminService.generate_full(
            args.start_date, args.end_date, rotation_order_ids=[], dry_run=True
        )
        # dry_run never persists, but be defensive: undo anything
        # flushed by the legacy pass before building the new request.
        db.session.rollback()

        request = adapters.build_planning_request(args.start_date, args.end_date)
        new_plan = plan_schedule(request)

        published_oncall_dates = {
            friday for (friday, _group_id) in request.published_oncalls
        }
        report = build_comparison_report(legacy, new_plan, published_oncall_dates)
        print(json.dumps(_jsonable(report), indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
