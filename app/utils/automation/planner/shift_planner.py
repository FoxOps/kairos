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

Rule 2 (rotation slot) is symmetric - both last week's AND next week's
on-call get it, matching AdvancedShiftAutomation.determine_shift_for_user()/
get_upcoming_oncall_user() (fixed on this same branch, see commit
b2a225c: without the forward-looking half, a group whose on-call turns
are sparse relative to other groups sharing the same rotation pool
would fall through to the static default slot every week, never
varying). The rule 7 fallback (guaranteeing at least one rotation-slot
person when neither half of rule 2 matches anyone present) also rotates
the narrowed-to-present candidate list by the day's absolute week index
(rotation.rotate(), the same date-derived mechanism used for on-call
rotation - see rotation.py) rather than always picking the same
present candidate - the identical staleness bug that commit's own
_ensure_minimum_07_15_coverage fix addressed in the legacy engine
(confirmed there by direct reproduction: 60 weeks, one of 3 group
members never once selected).

No DB access anywhere in this module - every input arrives as
already-loaded snapshot data via PlanningRequest.
"""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.utils.automation.planner.rotation import rotate
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
    day: date,
    available_users: tuple[UserRef, ...],
    oncall_user_id_today: int | None,
    oncall_user_id_last_week: int | None,
    oncall_user_id_next_week: int | None,
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    published_slot_by_user: dict[int, str],
) -> dict[int, str]:
    """Assigns a role slot ("oncall"/"rotation"/"default") to each of
    `available_users` - one algorithm for any headcount, not a
    count-based special case:

    1. The on-call-today user (if among available_users) gets "oncall".
    2. Any remaining available user who was on-call last week OR will be
       on-call next week gets "rotation" (symmetric - see module
       docstring for why the forward-looking half matters).
    3. If nobody has "rotation" yet, one remaining available user is
       picked for it (rule 7: at least one rotation-slot person every
       day) - preferring whoever already had it in the published
       schedule (minimal perturbation), else the configured rotation
       order narrowed to today's remaining candidates and rotated by
       the day's absolute week index (never a fixed "first present"
       pick - see module docstring for the staleness bug that would
       otherwise reintroduce).
    4. Everyone else gets "default".

    A single available user with no on-call today/last/next week still
    ends up with "rotation" via step 3 (nothing else to prefer, they're
    the only remaining candidate) - this is what step 6 of the old
    rules ("minimum headcount: 1 person covers 7am-3pm alone") reduces
    to under this general algorithm, without a dedicated 1-user branch.
    """
    slot_by_user: dict[int, str] = {}
    available_by_id = {user.id: user for user in available_users}

    if oncall_user_id_today is not None and oncall_user_id_today in available_by_id:
        slot_by_user[oncall_user_id_today] = "oncall"

    for candidate_id in (oncall_user_id_last_week, oncall_user_id_next_week):
        if (
            candidate_id is not None
            and candidate_id in available_by_id
            and candidate_id not in slot_by_user
        ):
            slot_by_user[candidate_id] = "rotation"

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
                rotated_order = rotate(rotation_order, day, rotation_anchor_epoch)
                fallback_id = next(
                    (u.id for u in rotated_order if u.id in remaining_ids),
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
    oncall_group_id: int | None,
    eligible_users: tuple[UserRef, ...],
    proposed_oncalls: dict[tuple[date, int | None], int],
    existing_oncalls: tuple,
    existing_leaves: tuple[LeaveSpan, ...],
    locked: frozenset[tuple[date, int]],
    published: dict[tuple[date, int], int],
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    rules: ResolvedRules,
) -> ShiftPlanFragment:
    """Plans shift assignments for one scope over [start_date, end_date].
    `proposed_oncalls` is the in-memory (friday, group_id) -> user_id map
    produced by oncall_planner.merge_oncall_fragments() - shift planning
    NEVER reads on-calls from the database, which is the structural fix
    for audit defect #1 (preview computing shifts from real on-calls in
    the DB while the on-call preview itself was only ever in-memory).

    `group_id` (this shift scope's own identity, used to tag
    ProposedShift.group_id and for staffing-limit bookkeeping) and
    `oncall_group_id` (which key in `proposed_oncalls` holds THIS
    scope's on-call info) are deliberately two separate parameters, NOT
    one - they only happen to be equal when shift_scheduling_mode and
    oncall_scheduling_mode are both "per_group". When they differ (e.g.
    shifts "per_group" but on-calls "shared" - an explicitly supported,
    documented combination), on-calls are proposed under scope `None`
    while shift planning runs once per real group id - looking up
    `(friday, group_id)` in that case would never match anything
    (`group_id` is never `None`), silently blinding every rule-1/rule-2
    on-call-aware slot assignment below for that entire scope. Real bug
    found in production (v1.1.1, "shift per_group + oncall shared"):
    every day's shift got the exact same slot assignment every week,
    and the on-call person never received their own "oncall" slot
    during their own on-call week, because these lookups always missed.
    Caller (plan_schedule.py) computes the correct value: `None` when
    oncall_scheduling_mode is "shared", else this scope's own
    `group_id` when oncall_scheduling_mode is "per_group"."""
    proposed: list[ProposedShift] = []
    unfilled: list[UnfilledRequirement] = []
    violations: list[RuleViolation] = []

    slot_shift_type = {
        "oncall": (rules.oncall_shift_type_id, rules.oncall_slot_hours),
        "rotation": (rules.rotation_shift_type_id, rules.rotation_slot_hours),
        "default": (rules.default_shift_type_id, rules.default_slot_hours),
    }

    # Every on-call end time per user, from both real history and this
    # same plan's own proposed on-calls (never a DB read) - used for the
    # rest_after_oncall hard constraint below. Kept as a sorted list per
    # user (not a single "most recent" value) because "most recent" is
    # relative to the shift day being evaluated: a user's on-call later
    # in the planning window must not count as already-ended for a shift
    # earlier in the window - see _last_oncall_end_before().
    oncall_ends_by_user: dict[int, list[datetime]] = {}
    for oncall in existing_oncalls:
        oncall_ends_by_user.setdefault(oncall.user_id, []).append(oncall.end_time)
    for (friday, oc_group_id), user_id in proposed_oncalls.items():
        if oc_group_id != oncall_group_id:
            continue
        end_time = datetime.combine(
            friday + timedelta(days=7), datetime.min.time()
        ).replace(hour=rules.oncall_anchor_end_hour)
        oncall_ends_by_user.setdefault(user_id, []).append(end_time)
    for ends in oncall_ends_by_user.values():
        ends.sort()

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
            (_covering_friday(day, rules), oncall_group_id)
        )
        last_week_friday = _covering_friday(day - timedelta(days=7), rules)
        oncall_user_id_last_week = proposed_oncalls.get(
            (last_week_friday, oncall_group_id)
        )

        # Symmetric forward-looking half of rule 2 - only credited if
        # that on-call genuinely starts after `day` (mirrors
        # AdvancedShiftAutomation.get_upcoming_oncall_user()'s own
        # guard): on a transition Friday, `day + 7 days` can land on
        # the tail end of an on-call that started that same evening,
        # which is not a genuinely future one.
        next_week_friday = _covering_friday(day + timedelta(days=7), rules)
        oncall_user_id_next_week = (
            proposed_oncalls.get((next_week_friday, oncall_group_id))
            if next_week_friday > day
            else None
        )

        published_slot_by_user = {
            user_id: _role_slot_for_shift_type(shift_type_id, rules)
            for (pub_date, user_id), shift_type_id in published.items()
            if pub_date == day
        }

        slot_by_user = assign_shift_slots_for_day(
            day,
            available_today,
            oncall_user_id_today,
            oncall_user_id_last_week,
            oncall_user_id_next_week,
            rotation_order,
            rotation_anchor_epoch,
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

            if role_slot != "oncall" and shift_violates_rest_after_oncall(
                shift_start,
                _last_oncall_end_before(user.id, shift_start, oncall_ends_by_user),
                rules.rest_after_oncall_hours,
            ):
                # role_slot == "oncall" is deliberately exempt: that
                # slot IS the on-call user's own coverage shift for the
                # day their on-call starts/ends (see
                # AdvancedShiftAutomation.get_oncall_for_date()'s
                # docstring - the departing holder is still "this
                # week's on-call for shift purposes" on the transition
                # Friday) - not a second, independent assignment that
                # rest could meaningfully apply to. Real bug found in
                # production: with rest_after_oncall configured (any
                # legally-required rest value, e.g. 11h), the gap
                # between an on-call ending 07:00 and this same slot
                # starting 13:00 (6h) tripped the check on literally
                # every single transition Friday, forever, leaving the
                # mandatory on-call shift permanently unfilled - shift
                # and on-call for the SAME user are meant to coexist,
                # only shift-shift and on-call-on-call conflicts are
                # meant to block (rest_after_oncall still applies below
                # to "rotation"/"default" slots, its actual intended
                # target: an unrelated regular shift assigned too soon
                # after an on-call week).
                # "warning", not "hard_blocked": this user is already
                # excluded from this one day right below (continue) -
                # same non-fatal, self-mitigated shape as an unfilled
                # staffing_min slot, expected to fire routinely (every
                # transition Friday where the departing on-call holder
                # would otherwise get the same-day rotation slot - see
                # test_rest_after_oncall_violation_produces_shift_message).
                # "hard_blocked" is reserved for _evaluate_safety's own
                # defense-in-depth cases (plan_schedule.py) - it aborts
                # the ENTIRE apply, which a single routine per-day
                # exclusion must never do (real bug: it used to, making
                # any org with rest_after_oncall configured unable to
                # ever apply a multi-month generation).
                violations.append(
                    RuleViolation(
                        severity="warning",
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


def _last_oncall_end_before(
    user_id: int, before: datetime, ends_by_user: dict[int, list[datetime]]
) -> datetime | None:
    """The most recent on-call end time for `user_id` that is not later
    than `before` (an already-sorted list per user) - a future on-call
    (relative to `before`) must never count as "already ended"."""
    ends = ends_by_user.get(user_id)
    if not ends:
        return None
    idx = bisect_right(ends, before)
    return ends[idx - 1] if idx > 0 else None


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
