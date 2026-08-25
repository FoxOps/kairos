"""Computes fairness metrics for a proposed plan - descriptive only,
never blocking (safe_to_apply is computed separately in
plan_schedule.py from violations/locked-slot integrity, not from
fairness). Surfaced on SchedulePlan so an admin reviewing a preview can
see whether an equal-coverage plan is also a balanced one, per the
audit's "equal-coverage plans with different fairness" scenario."""

from app.utils.automation.planner.types import (
    FairnessMetrics,
    ProposedOnCall,
    ProposedShift,
)

# Same undesirability rank used by shift_planner.py's own fallback tie
# break - kept in one place conceptually, duplicated as a constant here
# only because importing it would create a needless cross-module
# coupling for a single dict literal.
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
) -> FairnessMetrics:
    oncall_count_by_user: dict[int, int] = {}
    for o in oncalls:
        oncall_count_by_user[o.user_id] = oncall_count_by_user.get(o.user_id, 0) + 1

    undesirable_shift_count_by_user: dict[int, int] = {}
    for s in shifts:
        weight = _SLOT_RANK.get(s.role_slot, 0)
        if weight:
            undesirable_shift_count_by_user[s.user_id] = (
                undesirable_shift_count_by_user.get(s.user_id, 0) + weight
            )

    # "Adherence" here means how much of the on-call plan matches what
    # was already published (unchanged/added, i.e. not a reassignment
    # of an existing published slot) - a proxy for schedule stability,
    # not a literal check against the configured rotation order (that
    # would require re-deriving rotate() with the same epoch here,
    # which this metric deliberately avoids to stay a pure post-hoc
    # summary of the plan's own already-computed change_type values).
    if oncalls:
        stable = sum(1 for o in oncalls if o.change_type in ("unchanged", "added"))
        rotation_adherence_ratio = stable / len(oncalls)
    else:
        rotation_adherence_ratio = 1.0

    return FairnessMetrics(
        oncall_count_by_user=oncall_count_by_user,
        oncall_count_stddev=_stddev(list(oncall_count_by_user.values())),
        undesirable_shift_count_by_user=undesirable_shift_count_by_user,
        undesirable_shift_stddev=_stddev(
            list(undesirable_shift_count_by_user.values())
        ),
        rotation_adherence_ratio=rotation_adherence_ratio,
    )
