"""Pure shift planning - the portion of the automation planner that
proposes shift assignments for one scope (one group, or the shared/
org-wide scope) at a time.

Replaces AdvancedShiftAutomation.generate_daily_shifts()'s three
count-based special-case branches (1 available user, 2 available
users, 3+ available users - see its class docstring, rules 1/2/3/4/6/7)
with one uniform algorithm (assign_shift_slots_for_day() below) that
produces the same result for the same inputs regardless of headcount -
fixing audit defect #10 (fixed special-case branching instead of
requirements-driven assignment) along with defect #3 (automation never
enforcing staffing_limits/rest_after_oncall the way manual creation
does - see rules/predicates.py, used here too) and defect #8/#9
(weekend definition and every other rule value always resolved through
ResolvedRules, never hardcoded).

Deliberately narrower than the legacy determine_shift_for_user() in one
respect: only *today's* and *last week's* on-call feed the rotation
slot (rules 1/2 as actually implemented and tested). A "next week's
on-call also gets the rotation slot" idea exists in the legacy module
(get_upcoming_oncall_user()) but is dead code with zero callers and zero
test coverage anywhere in this codebase - not a real behavior to carry
forward, and not something audit defect #10 asked to change.

No DB access anywhere in this module - every input arrives as
already-loaded snapshot data via PlanningRequest.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.utils.automation.planner.types import (
    LeaveSpan,
    ProposedShift,
    ResolvedRules,
    RuleViolation,
    UnfilledRequirement,
    UserRef,
)
from app.utils.automation.rules.predicates import shift_violates_rest_after_oncall

# Undesirability rank used only for this module's own fairness
# weighting (FairnessMetrics.undesirable_shift_count_by_user) and to
# break ties among otherwise-equally-eligible rotation-slot candidates -
# an internal solver detail, not a business rule, so it is not exposed
# as a setting (same category as the branch-and-bound search's own
# node cap in oncall_automation.py).
_SLOT_RANK = {"default": 0, "rotation": 1, "oncall": 2}


@dataclass(frozen=True)
class ShiftPlanFragment:
    proposed: tuple[ProposedShift, ...]
    unfilled: tuple[UnfilledRequirement, ...]
    violations: tuple[RuleViolation, ...]


def _is_on_leave(user_id: int, day: date, leaves: tuple[LeaveSpan, ...]) -> bool:
    return any(
        leave.user_id == user_id and leave.start_date <= day <= leave.end_date
        for leave in leaves
    )


def assign_shift_slots_for_day(
    available_users: tuple[UserRef, ...],
    oncall_user_id_today: int | None,
    oncall_user_id_last_week: int | None,
    rotation_order: tuple[UserRef, ...],
    published_slot_by_user: dict[int, str],
) -> dict[int, str]:
    """Assigns a role slot ("oncall"/"rotation"/"default") to each of
    `available_users` - one algorithm for any headcount, not a
    count-based special case:

    1. The on-call-today user (if among available_users) gets "oncall".
    2. Any remaining available user who was on-call last week gets
       "rotation".
    3. If nobody has "rotation" yet, the configured rotation order picks
       one remaining available user for it (rule 7: at least one
       rotation-slot person every day) - preferring whoever already had
       it in the published schedule (minimal perturbation), else the
       first rotation_order member still available, else the first
       remaining available user.
    4. Everyone else gets "default".

    A single available user with no on-call today/last week still ends
    up with "rotation" via step 3 (nothing else to prefer, they're the
    only remaining candidate) - this is what step 6 of the old rules
    ("minimum headcount: 1 person covers 7am-3pm alone") reduces to
    under this general algorithm, without a dedicated 1-user branch.
    """
    slot_by_user: dict[int, str] = {}
    available_by_id = {user.id: user for user in available_users}

    if oncall_user_id_today is not None and oncall_user_id_today in available_by_id:
        slot_by_user[oncall_user_id_today] = "oncall"

    if (
        oncall_user_id_last_week is not None
        and oncall_user_id_last_week in available_by_id
        and oncall_user_id_last_week not in slot_by_user
    ):
        slot_by_user[oncall_user_id_last_week] = "rotation"

    if not any(slot == "rotation" for slot in slot_by_user.values()):
        remaining = [u for u in available_users if u.id not in slot_by_user]
        if remaining:
            remaining_ids = {u.id for u in remaining}
            fallback_id = next(
                (
                    uid
                    for uid, slot in published_slot_by_user.items()
                    if slot == "rotation" and uid in remaining_ids
                ),
                None,
            )
            if fallback_id is None:
                fallback_id = next(
                    (u.id for u in rotation_order if u.id in remaining_ids),
                    remaining[0].id,
                )
            slot_by_user[fallback_id] = "rotation"

    for user in available_users:
        slot_by_user.setdefault(user.id, "default")

    return slot_by_user


def plan_shifts_for_scope(
    start_date: date,
    end_date: date,
    group_id: int | None,
    eligible_users: tuple[UserRef, ...],
    proposed_oncalls: dict[tuple[date, int | None], int],
    existing_oncalls: tuple,
    existing_leaves: tuple[LeaveSpan, ...],
    locked: frozenset[tuple[date, int]],
    published: dict[tuple[date, int], int],
    rotation_order: tuple[UserRef, ...],
    rules: ResolvedRules,
) -> ShiftPlanFragment:
    """Plans shift assignments for one scope over [start_date, end_date].
    `proposed_oncalls` is the in-memory (friday, group_id) -> user_id map
    produced by oncall_planner.merge_oncall_fragments() - shift planning
    NEVER reads on-calls from the database, which is the structural fix
    for audit defect #1 (preview computing shifts from real on-calls in
    the DB while the on-call preview itself was only ever in-memory)."""
    proposed: list[ProposedShift] = []
    unfilled: list[UnfilledRequirement] = []
    violations: list[RuleViolation] = []

    slot_shift_type = {
        "oncall": (rules.oncall_shift_type_id, rules.oncall_slot_hours),
        "rotation": (rules.rotation_shift_type_id, rules.rotation_slot_hours),
        "default": (rules.default_shift_type_id, rules.default_slot_hours),
    }

    # Most recent on-call end time per user, from both real history and
    # this same plan's own proposed on-calls (never a DB read) - used
    # for the rest_after_oncall hard constraint below.
    last_oncall_end_by_user: dict[int, datetime] = {}
    for oncall in existing_oncalls:
        current = last_oncall_end_by_user.get(oncall.user_id)
        if current is None or oncall.end_time > current:
            last_oncall_end_by_user[oncall.user_id] = oncall.end_time
    for (friday, oc_group_id), user_id in proposed_oncalls.items():
        if oc_group_id != group_id:
            continue
        end_time = datetime.combine(
            friday + timedelta(days=7), datetime.min.time()
        ).replace(hour=rules.oncall_anchor_end_hour)
        current = last_oncall_end_by_user.get(user_id)
        if current is None or end_time > current:
            last_oncall_end_by_user[user_id] = end_time

    day = start_date
    while day <= end_date:
        if day.weekday() in rules.weekend_days:
            day += timedelta(days=1)
            continue

        available_today = tuple(
            user
            for user in eligible_users
            if not _is_on_leave(user.id, day, existing_leaves)
        )

        oncall_user_id_today = proposed_oncalls.get(
            (_covering_friday(day, rules), group_id)
        )
        last_week_friday = _covering_friday(day - timedelta(days=7), rules)
        oncall_user_id_last_week = proposed_oncalls.get((last_week_friday, group_id))

        published_slot_by_user = {
            user_id: _role_slot_for_shift_type(shift_type_id, rules)
            for (pub_date, user_id), shift_type_id in published.items()
            if pub_date == day
        }

        slot_by_user = assign_shift_slots_for_day(
            available_today,
            oncall_user_id_today,
            oncall_user_id_last_week,
            rotation_order,
            published_slot_by_user,
        )

        for user in available_today:
            if (day, user.id) in locked:
                published_shift_type_id = published.get((day, user.id))
                if published_shift_type_id is None:
                    unfilled.append(
                        UnfilledRequirement(
                            kind="staffing_min",
                            date=day,
                            group_id=group_id,
                            reason_code="locked_but_no_published_assignment",
                            detail="",
                        )
                    )
                    continue
                role_slot = _role_slot_for_shift_type(published_shift_type_id, rules)
                start_hour, end_hour = slot_shift_type[role_slot][1]
                proposed.append(
                    _build_proposed_shift(
                        day,
                        user.id,
                        published_shift_type_id,
                        start_hour,
                        end_hour,
                        group_id,
                        role_slot,
                        "unchanged",
                        ("locked - carried through unchanged",),
                    )
                )
                continue

            role_slot = slot_by_user[user.id]
            shift_type_id, (start_hour, end_hour) = slot_shift_type[role_slot]
            shift_start = datetime.combine(day, datetime.min.time()).replace(
                hour=start_hour
            )

            if shift_violates_rest_after_oncall(
                shift_start,
                last_oncall_end_by_user.get(user.id),
                rules.rest_after_oncall_hours,
            ):
                violations.append(
                    RuleViolation(
                        severity="hard_blocked",
                        rule_type="rest_after_oncall",
                        group_id=group_id,
                        date=day,
                        user_id=user.id,
                        message="rest_after_oncall violated - user excluded from this day",
                    )
                )
                continue

            max_limit = rules.staffing_limits.get(shift_type_id, {}).get("max")
            if max_limit is not None:
                current_count = sum(
                    1
                    for s in proposed
                    if s.date == day and s.shift_type_id == shift_type_id
                )
                if current_count >= max_limit:
                    unfilled.append(
                        UnfilledRequirement(
                            kind="staffing_min",
                            date=day,
                            group_id=group_id,
                            reason_code="staffing_max_reached",
                            detail=str(shift_type_id),
                        )
                    )
                    continue

            published_shift_type_id = published.get((day, user.id))
            change_type = (
                "unchanged"
                if published_shift_type_id == shift_type_id
                else ("reassigned" if published_shift_type_id is not None else "added")
            )

            proposed.append(
                _build_proposed_shift(
                    day,
                    user.id,
                    shift_type_id,
                    start_hour,
                    end_hour,
                    group_id,
                    role_slot,
                    change_type,
                    (f"role slot: {role_slot}",),
                )
            )

        unfilled.extend(
            _mandatory_and_staffing_min_gaps(proposed, day, group_id, rules)
        )

        day += timedelta(days=1)

    return ShiftPlanFragment(
        proposed=tuple(proposed), unfilled=tuple(unfilled), violations=tuple(violations)
    )


def _covering_friday(day: date, rules: ResolvedRules) -> date:
    """The anchor date of the on-call week covering `day`, generalizing
    AdvancedShiftAutomation.get_oncall_for_date()'s "Monday minus N
    days" computation to any configured anchor weekday."""
    days_before_monday = (0 - rules.oncall_anchor_weekday) % 7
    week_monday = day - timedelta(days=day.weekday())
    return week_monday - timedelta(days=days_before_monday)


def _role_slot_for_shift_type(shift_type_id: int, rules: ResolvedRules) -> str:
    if shift_type_id == rules.oncall_shift_type_id:
        return "oncall"
    if shift_type_id == rules.rotation_shift_type_id:
        return "rotation"
    return "default"


def _build_proposed_shift(
    day: date,
    user_id: int,
    shift_type_id: int,
    start_hour: int,
    end_hour: int,
    group_id: int | None,
    role_slot: str,
    change_type: str,
    explanation: tuple[str, ...],
) -> ProposedShift:
    start_time = datetime.combine(day, datetime.min.time()).replace(hour=start_hour)
    end_time = datetime.combine(day, datetime.min.time()).replace(hour=end_hour)
    return ProposedShift(
        date=day,
        user_id=user_id,
        shift_type_id=shift_type_id,
        start_time=start_time,
        end_time=end_time,
        group_id=group_id,
        role_slot=role_slot,  # type: ignore[arg-type]
        change_type=change_type,  # type: ignore[arg-type]
        explanation=explanation,
    )


def _mandatory_and_staffing_min_gaps(
    proposed: list[ProposedShift], day: date, group_id: int | None, rules: ResolvedRules
) -> list[UnfilledRequirement]:
    today_shift_type_ids = {s.shift_type_id for s in proposed if s.date == day}
    gaps: list[UnfilledRequirement] = []

    for shift_type_id in rules.mandatory_shift_type_ids:
        if shift_type_id not in today_shift_type_ids:
            gaps.append(
                UnfilledRequirement(
                    kind="mandatory_shift",
                    date=day,
                    group_id=group_id,
                    reason_code="mandatory_shift_type_unfilled",
                    detail=str(shift_type_id),
                )
            )

    for shift_type_id, limits in rules.staffing_limits.items():
        min_limit = limits.get("min")
        if min_limit is None:
            continue
        current_count = sum(
            1 for s in proposed if s.date == day and s.shift_type_id == shift_type_id
        )
        if current_count < min_limit:
            gaps.append(
                UnfilledRequirement(
                    kind="staffing_min",
                    date=day,
                    group_id=group_id,
                    reason_code="staffing_min_not_met",
                    detail=str(shift_type_id),
                )
            )

    return gaps
