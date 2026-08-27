"""Phase 3 scenario tests: preview-then-apply with no intervening data
change, manual locked assignments inside a regenerated range, and the
safe_to_apply defense-in-depth circuit breaker. No DB/app context
needed - plan_schedule() is pure."""

from datetime import date

from app.utils.automation.planner.plan_schedule import plan_schedule
from app.utils.automation.planner.types import PlanningRequest, ResolvedRules, UserRef

RULES = ResolvedRules(
    oncall_anchor_weekday=4,
    oncall_anchor_start_hour=21,
    oncall_anchor_end_hour=7,
    oncall_spacing_weeks=2,
    weekend_days=frozenset({5, 6}),
    staffing_limits={},
    rest_after_oncall_hours=0,
    oncall_shift_overlap_block=False,
    oncall_shift_type_id=100,
    oncall_slot_hours=(13, 21),
    rotation_shift_type_id=200,
    rotation_slot_hours=(7, 15),
    default_shift_type_id=300,
    default_slot_hours=(9, 17),
)
EPOCH = date(2000, 1, 3)
USERS = (UserRef(1, "A", None), UserRef(2, "B", None), UserRef(3, "C", None))


def _base_request(**overrides):
    defaults = {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 31),
        "oncall_groups": (None,),
        "schedule_groups": (None,),
        "eligible_oncall_users": {None: USERS},
        "eligible_shift_users": {None: USERS},
        "rotation_order": {None: USERS},
        "rotation_anchor_epoch": EPOCH,
        "existing_oncalls": (),
        "existing_leaves": (),
        "resolved_rules": {None: RULES},
    }
    defaults.update(overrides)
    return PlanningRequest(**defaults)


def test_preview_then_apply_with_no_data_change_is_all_unchanged_and_safe():
    first_plan = plan_schedule(_base_request())

    published_oncalls = {(o.friday, o.group_id): o.user_id for o in first_plan.oncalls}
    published_shifts = {(s.date, s.user_id): s.shift_type_id for s in first_plan.shifts}

    second_plan = plan_schedule(
        _base_request(
            published_oncalls=published_oncalls, published_shifts=published_shifts
        )
    )

    assert second_plan.safe_to_apply is True
    assert second_plan.safe_to_apply_reasons == ()
    assert all(entry.change_type == "unchanged" for entry in second_plan.diff)
    # Re-planning identical published data must reproduce the identical
    # *assignments* (first_plan's own entries are correctly tagged
    # "added" - there was no published data yet when it ran - only
    # second_plan's are expected to be "unchanged", so compare the
    # underlying user_id/shift_type_id assignments, not the tagged
    # objects themselves).
    assert {(o.friday, o.group_id): o.user_id for o in first_plan.oncalls} == {
        (o.friday, o.group_id): o.user_id for o in second_plan.oncalls
    }
    assert {(s.date, s.user_id): s.shift_type_id for s in first_plan.shifts} == {
        (s.date, s.user_id): s.shift_type_id for s in second_plan.shifts
    }


def test_locked_oncall_slot_never_appears_reassigned_or_removed():
    first_plan = plan_schedule(_base_request())
    published_oncalls = {(o.friday, o.group_id): o.user_id for o in first_plan.oncalls}
    locked_friday, locked_group_id = next(iter(published_oncalls))

    second_plan = plan_schedule(
        _base_request(
            published_oncalls=published_oncalls,
            locked_oncalls=frozenset({(locked_friday, locked_group_id)}),
        )
    )

    locked_entry = next(
        e
        for e in second_plan.diff
        if e.kind == "oncall"
        and e.date == locked_friday
        and e.group_id == locked_group_id
    )
    assert locked_entry.change_type == "unchanged"
    assert (
        locked_entry.proposed_user_id
        == published_oncalls[(locked_friday, locked_group_id)]
    )
    assert second_plan.safe_to_apply is True


def test_locked_shift_never_appears_reassigned_or_removed():
    first_plan = plan_schedule(_base_request())
    published_shifts = {(s.date, s.user_id): s.shift_type_id for s in first_plan.shifts}
    locked_date, locked_user_id = next(iter(published_shifts))

    second_plan = plan_schedule(
        _base_request(
            published_shifts=published_shifts,
            locked_shifts=frozenset({(locked_date, locked_user_id)}),
        )
    )

    locked_entry = next(
        e
        for e in second_plan.diff
        if e.kind == "shift"
        and e.date == locked_date
        and e.proposed_user_id == locked_user_id
    )
    assert locked_entry.change_type == "unchanged"
    assert second_plan.safe_to_apply is True


def test_safe_to_apply_flips_false_when_a_locked_slot_is_reassigned():
    """Defensive circuit-breaker path: if a diff entry ever shows a
    locked slot as reassigned/removed (should be structurally
    impossible when the planner excludes locked slots from the
    candidate pool correctly), safe_to_apply must flip to False with a
    populated reason - simulated here directly against
    _evaluate_safety() since deliberately mis-wiring the real planner
    isn't something a black-box scenario test can do from outside."""
    from app.utils.automation.planner.plan_schedule import _evaluate_safety
    from app.utils.automation.planner.types import ScheduleDiffEntry

    bad_diff = (
        ScheduleDiffEntry(
            kind="oncall",
            date=date(2026, 1, 2),
            group_id=None,
            published_user_id=1,
            proposed_user_id=2,
            change_type="reassigned",
        ),
    )
    safe, reasons = _evaluate_safety(
        violations=(),
        diff=bad_diff,
        locked_oncalls=frozenset({(date(2026, 1, 2), None)}),
        locked_shifts=frozenset(),
    )
    assert safe is False
    assert len(reasons) == 1
    assert "locked oncall slot changed" in reasons[0]


def test_rest_after_oncall_exclusions_never_flip_safe_to_apply():
    """Real production bug: a rest_after_oncall exclusion is expected,
    already self-mitigated by shift_planner.py itself (the user is
    simply skipped for that one day, "continue") - not a plan-breaking
    defect. It must never make safe_to_apply False, or a whole
    multi-month generation run becomes impossible to apply for any org
    that configures this rule at all. Exercised directly against
    _evaluate_safety() (same pattern as the locked-slot test below)
    since shift_planner.py's own role_slot != "oncall" guard (see its
    module) now makes this violation genuinely rare in a plain rotation
    scenario - this test must keep passing regardless of how often the
    planner actually produces one."""
    from app.utils.automation.planner.plan_schedule import _evaluate_safety
    from app.utils.automation.planner.types import RuleViolation

    warning_violation = (
        RuleViolation(
            severity="warning",
            rule_type="rest_after_oncall",
            group_id=None,
            date=date(2026, 1, 2),
            user_id=1,
            message="rest_after_oncall violated - user excluded from this day",
        ),
    )

    safe, reasons = _evaluate_safety(
        violations=warning_violation,
        diff=(),
        locked_oncalls=frozenset(),
        locked_shifts=frozenset(),
    )

    assert safe is True
    assert reasons == ()
