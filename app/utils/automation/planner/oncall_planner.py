"""Pure on-call planning - the portion of the automation planner that
proposes on-call assignments for one scope (one group, or the shared/
org-wide scope) at a time.

Ports the week-construction and candidate-filtering logic from
oncall_automation.py's _fridays_in_range()/_generate_for_fridays(),
with two deliberate behavior changes:

- The rotation offset for a given Friday is rotation.rotate()'s
  absolute_week_index(), not an enumerate() position local to this
  call's own week list - fixes defect #4 (rotation resetting every
  generation call, so the same Friday could get a different user
  depending on what date range happened to be requested).
- Preferred/published/locked assignments are keyed by
  (friday, group_id), not friday alone - fixes defect #7
  (OnCallAutomation.capture_existing_assignments() returning a single
  {date: user_id} dict, so two groups with concurrent on-calls on the
  same Friday would silently overwrite each other).

No DB access anywhere in this module - every input arrives as
already-loaded snapshot data via PlanningRequest.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.utils.automation.oncall_automation import (
    AvailabilityIndex,
    _solve_max_filled_weeks,
)
from app.utils.automation.planner.rotation import rotate
from app.utils.automation.planner.types import (
    ChangeType,
    LeaveSpan,
    OnCallSnapshot,
    ProposedOnCall,
    ResolvedRules,
    UnfilledRequirement,
    UserRef,
)


def _fridays_in_range(
    start_date: date, end_date: date, anchor_weekday: int
) -> list[date]:
    """Every on-call anchor weekday from the first one on/after
    start_date through end_date, inclusive - pure port of
    oncall_automation.py's module-level function of the same name,
    minus its DB-touching rule resolution (anchor_weekday is passed in
    already resolved)."""
    days_ahead = (anchor_weekday - start_date.weekday()) % 7
    current = start_date + timedelta(days=days_ahead)
    fridays = []
    while current <= end_date:
        fridays.append(current)
        current += timedelta(days=7)
    return fridays


@dataclass(frozen=True)
class OnCallPlanFragment:
    """Result of planning one scope - internal to the planner package,
    merged across scopes by merge_oncall_fragments() below."""

    proposed: tuple[ProposedOnCall, ...]
    unfilled: tuple[UnfilledRequirement, ...]


def _fairness_key_factory(
    prior_counts: dict[int, int],
    rotation_order: tuple[UserRef, ...],
):
    """Builds the tie-break key used when two candidate plans fill the
    same number of weeks - evaluated by _solve_max_filled_weeks only
    when coverage already ties: balance total on-call counts, then
    follow rotation order. Lower key wins (same convention as
    sorted(key=...)). Deliberately does NOT bias toward the previously
    published schedule - the configured rotation order must always be
    authoritative for non-locked weeks, never sticky to old state (see
    plan_oncalls_for_scope()'s own docstring)."""
    rotation_position = {user.id: i for i, user in enumerate(rotation_order)}

    def fairness_key(assignment: dict[int, UserRef]) -> tuple[float, int]:
        counts = dict(prior_counts)
        for user in assignment.values():
            counts[user.id] = counts.get(user.id, 0) + 1
        if counts:
            mean = sum(counts.values()) / len(counts)
            variance = sum((c - mean) ** 2 for c in counts.values()) / len(counts)
        else:
            variance = 0.0

        rotation_deviation = sum(
            rotation_position.get(user.id, 0) for user in assignment.values()
        )

        return (variance, rotation_deviation)

    return fairness_key


def plan_oncalls_for_scope(
    start_date: date,
    end_date: date,
    group_id: int | None,
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    existing_oncalls: tuple[OnCallSnapshot, ...],
    existing_leaves: tuple[LeaveSpan, ...],
    locked: frozenset[tuple[date, int | None]],
    published: dict[tuple[date, int | None], int],
    rules: ResolvedRules,
) -> OnCallPlanFragment:
    """Plans on-call assignments for one scope over [start_date, end_date].
    `rotation_order` is this scope's eligible-user rotation order - an
    empty tuple means no eligible users, every week comes back unfilled.

    Non-locked weeks always follow `rotation_order` (rotated by
    absolute week index, see rotation.py) - deliberately no bias
    toward whatever is already published for that week. The configured
    order must always be authoritative; only an explicitly `locked`
    week is carried through unchanged (see the second loop below)."""
    fridays = _fridays_in_range(start_date, end_date, rules.oncall_anchor_weekday)
    if not fridays:
        return OnCallPlanFragment(proposed=(), unfilled=())

    index = AvailabilityIndex.from_snapshots(
        existing_oncalls, existing_leaves, min_spacing_weeks=rules.oncall_spacing_weeks
    )

    weeks: list[tuple[date, datetime, datetime]] = []
    for friday in fridays:
        start_time = datetime.combine(friday, datetime.min.time()).replace(
            hour=rules.oncall_anchor_start_hour
        )
        end_time = datetime.combine(
            friday + timedelta(days=7), datetime.min.time()
        ).replace(hour=rules.oncall_anchor_end_hour)
        weeks.append((friday, start_time, end_time))

    locked_week_indices: set[int] = set()
    week_candidates: list[list[UserRef]] = []
    for week_index, (friday, start_time, end_time) in enumerate(weeks):
        if (friday, group_id) in locked:
            locked_week_indices.add(week_index)
            week_candidates.append([])
            continue

        candidate_order = rotate(rotation_order, friday, rotation_anchor_epoch)

        week_candidates.append(
            [
                user
                for user in candidate_order
                if not index.has_oncall_conflict(user.id, start_time, end_time)
                and not index.has_leave_conflict(
                    user.id, start_time.date(), end_time.date()
                )
            ]
        )

    relevant_user_ids = {user.id for user in rotation_order}
    prior_counts = {user.id: 0 for user in rotation_order}
    for snapshot in existing_oncalls:
        if snapshot.user_id in relevant_user_ids:
            prior_counts[snapshot.user_id] = prior_counts.get(snapshot.user_id, 0) + 1

    fairness_key = _fairness_key_factory(prior_counts, rotation_order)

    assignment = (
        _solve_max_filled_weeks(
            weeks,
            week_candidates,
            index,
            min_spacing_weeks=rules.oncall_spacing_weeks,
            fairness_key=fairness_key,
        )
        if rotation_order
        else {}
    )

    proposed: list[ProposedOnCall] = []
    unfilled: list[UnfilledRequirement] = []

    for week_index, (friday, start_time, end_time) in enumerate(weeks):
        if week_index in locked_week_indices:
            published_user_id = published.get((friday, group_id))
            if published_user_id is None:
                unfilled.append(
                    UnfilledRequirement(
                        kind="oncall_week",
                        date=friday,
                        group_id=group_id,
                        reason_code="locked_but_no_published_assignment",
                        detail="",
                    )
                )
                continue
            proposed.append(
                ProposedOnCall(
                    friday=friday,
                    start_time=start_time,
                    end_time=end_time,
                    user_id=published_user_id,
                    group_id=group_id,
                    change_type="unchanged",
                    explanation=("locked - carried through unchanged",),
                )
            )
            continue

        assigned_user = assignment.get(week_index)
        if assigned_user is None:
            reason_code = (
                "no_available_user"
                if not week_candidates[week_index]
                else "no_candidate_meets_spacing"
            )
            unfilled.append(
                UnfilledRequirement(
                    kind="oncall_week",
                    date=friday,
                    group_id=group_id,
                    reason_code=reason_code,
                    detail="",
                )
            )
            continue

        published_user_id = published.get((friday, group_id))
        change_type: ChangeType
        if published_user_id == assigned_user.id:
            change_type = "unchanged"
        elif published_user_id is not None:
            change_type = "reassigned"
        else:
            change_type = "added"
        explanation = ["rotation order"]

        proposed.append(
            ProposedOnCall(
                friday=friday,
                start_time=start_time,
                end_time=end_time,
                user_id=assigned_user.id,
                group_id=group_id,
                change_type=change_type,
                explanation=tuple(explanation),
            )
        )

    return OnCallPlanFragment(proposed=tuple(proposed), unfilled=tuple(unfilled))


def merge_oncall_fragments(
    fragments: dict[int | None, OnCallPlanFragment],
) -> dict[tuple[date, int | None], int]:
    """Merges every scope's proposed on-calls into one
    (friday, group_id) -> user_id map, fed DIRECTLY into shift planning
    - never through the database (see plan_schedule.py). Keying by
    group_id here (not just friday) is what lets two groups have
    concurrent on-calls on the same Friday without one overwriting the
    other - the exact defect a single un-grouped {date: user_id} dict
    used to have (OnCallAutomation.capture_existing_assignments)."""
    merged: dict[tuple[date, int | None], int] = {}
    for group_id, fragment in fragments.items():
        for proposed in fragment.proposed:
            merged[(proposed.friday, group_id)] = proposed.user_id
    return merged
