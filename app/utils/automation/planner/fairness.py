"""Computes fairness metrics for a proposed plan - descriptive only,
never blocking (safe_to_apply is computed separately in
plan_schedule.py from violations/locked-slot integrity, not from
fairness). Surfaced on SchedulePlan so an admin reviewing a preview can
see whether an equal-coverage plan is also a balanced one, per the
audit's "equal-coverage plans with different fairness" scenario.

Scope of what is measured (audit F17): counts over *this plan's window
only* (no history horizon), across every eligible user passed in -
including those who receive nothing, so a lopsided plan can't hide
behind a stddev computed over its assignees alone. The shift weights
below are role-slot labels, not user preference or legal burden."""

from collections.abc import Iterable

from app.utils.automation.planner.types import (
    FairnessMetrics,
    ProposedOnCall,
    ProposedShift,
)

# Undesirability weight per role slot - an internal descriptive heuristic,
# not a business rule (not exposed as a setting).
_SLOT_RANK = {"default": 0, "rotation": 1, "oncall": 2}


def _stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance**0.5


def compute_fairness_metrics(
    oncalls: tuple[ProposedOnCall, ...],
    shifts: tuple[ProposedShift, ...],
    eligible_oncall_user_ids: Iterable[int] = (),
    eligible_shift_user_ids: Iterable[int] = (),
) -> FairnessMetrics:
    """`eligible_*_user_ids`: the population the counts are measured
    over - every one of them appears in the result, with 0 when the plan
    gives them nothing. Users absent from it but present in the plan
    (e.g. a locked row) are still counted."""
    oncall_count_by_user: dict[int, int] = dict.fromkeys(eligible_oncall_user_ids, 0)
    for o in oncalls:
        oncall_count_by_user[o.user_id] = oncall_count_by_user.get(o.user_id, 0) + 1

    undesirable_shift_count_by_user: dict[int, int] = dict.fromkeys(
        eligible_shift_user_ids, 0
    )
    for s in shifts:
        weight = _SLOT_RANK.get(s.role_slot, 0)
        if weight:
            undesirable_shift_count_by_user[s.user_id] = (
                undesirable_shift_count_by_user.get(s.user_id, 0) + weight
            )

    # Share of the on-call plan that doesn't reassign an already-published
    # slot (unchanged/added) - schedule *stability*, deliberately not
    # called "rotation adherence": a wholly new plan scores 1.0 whatever
    # order it follows.
    if oncalls:
        stable = sum(1 for o in oncalls if o.change_type in ("unchanged", "added"))
        assignment_stability_ratio = stable / len(oncalls)
    else:
        assignment_stability_ratio = 1.0

    return FairnessMetrics(
        oncall_count_by_user=oncall_count_by_user,
        oncall_count_stddev=_stddev(list(oncall_count_by_user.values())),
        undesirable_shift_count_by_user=undesirable_shift_count_by_user,
        undesirable_shift_stddev=_stddev(
            list(undesirable_shift_count_by_user.values())
        ),
        assignment_stability_ratio=assignment_stability_ratio,
    )
