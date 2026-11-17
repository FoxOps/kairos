"""Pure shift planning - the portion of the automation planner that
proposes shift assignments for one scope (one group, or the shared/
org-wide scope) at a time.

Replaced the legacy engine's generate_daily_shifts() three
count-based special-case branches (1 available user, 2 available
users, 3+ available users; legacy engine removed in 1.2.0)
with one uniform algorithm (assign_shift_slots_for_day() below) that
produces the same result for the same inputs regardless of headcount -
fixing audit defect #10 (fixed special-case branching instead of
requirements-driven assignment) along with defect #3 (automation never
enforcing staffing_limits/rest_after_oncall the way manual creation
does - see rules/predicates.py, used here too) and defect #8/#9
(weekend definition and every other rule value always resolved through
ResolvedRules, never hardcoded).

Rule 2 (rotation slot) is a priority, not a symmetric union: last
week's on-call holder gets it; only when nobody from last week is in
this scope does next week's holder get it instead. The forward-looking
half exists so a group whose on-call turns are sparse relative to other
groups sharing the same rotation pool doesn't fall through to the
static default slot every week (commit b2a225c) - but it used to apply
*in addition to* last week's holder, giving the rotation slot to two
people at once. Real production bug (1.2.0, report/1.2.0/BUG_HUNT_1.2.0.md):
with that slot capped at 1 via staffing_limits, the second one was
dropped for the whole day - no shift at all, Mon-Thu of every other
week. The rule 7 fallback (guaranteeing at least one rotation-slot
person when neither half of rule 2 matches anyone present) also rotates
the narrowed-to-present candidate list by the day's absolute week index
(rotation.rotate(), the same date-derived mechanism used for on-call
rotation - see rotation.py) rather than always picking the same
present candidate - the identical staleness bug that commit's own
_ensure_minimum_07_15_coverage fix addressed in the former legacy engine
(confirmed there by direct reproduction: 60 weeks, one of 3 group
members never once selected).

No DB access anywhere in this module - every input arrives as
already-loaded snapshot data via PlanningRequest.
"""

from bisect import bisect_right
from collections.abc import Callable
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
from app.utils.automation.rules.predicates import (
    intervals_overlap,
    shift_violates_rest_after_oncall,
)

Interval = tuple[datetime, datetime]


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
    oncall_user_ids_today: frozenset[int],
    oncall_user_ids_last_week: frozenset[int],
    oncall_user_ids_next_week: frozenset[int],
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    published_slot_by_user: dict[int, str],
) -> dict[int, str]:
    """Assigns a role slot ("oncall"/"rotation"/"default") to each of
    `available_users` - one algorithm for any headcount, not a
    count-based special case:

    1. Every on-call-today user (if among available_users) gets
       "oncall" - a *set*, not a single optional id: when the shift
       pool is "shared" but on-call is "per_group", more than one
       group can have a concurrent on-call the same day, each with its
       own holder who must each get their own "oncall" slot (see
       plan_shifts_for_scope()'s own docstring for the real bug this
       fixes - a single-id parameter structurally cannot represent
       that).
    2. Any remaining available user who was on-call last week gets
       "rotation"; only if none of them is available, next week's
       on-call holder(s) get it instead (priority, not a union - see
       module docstring for the real bug a union caused).
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

    for candidate_id in oncall_user_ids_today:
        if candidate_id in available_by_id:
            slot_by_user[candidate_id] = "oncall"

    for candidates in (oncall_user_ids_last_week, oncall_user_ids_next_week):
        for candidate_id in sorted(candidates):
            if candidate_id in available_by_id and candidate_id not in slot_by_user:
                slot_by_user[candidate_id] = "rotation"
        if any(slot == "rotation" for slot in slot_by_user.values()):
            break

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
    oncall_group_ids: tuple[int | None, ...],
    eligible_users: tuple[UserRef, ...],
    proposed_oncalls: dict[tuple[date, int | None], int],
    existing_oncalls: tuple,
    existing_leaves: tuple[LeaveSpan, ...],
    locked: frozenset[tuple[date, int]],
    published: dict[tuple[date, int], int],
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    rules: ResolvedRules,
    proposed_oncall_intervals: dict[tuple[date, int | None], Interval] | None = None,
    published_intervals: dict[tuple[date, int], Interval] | None = None,
) -> ShiftPlanFragment:
    """Plans shift assignments for one scope over [start_date, end_date].
    `proposed_oncalls` is the in-memory (friday, group_id) -> user_id map
    produced by oncall_planner.merge_oncall_fragments() - shift planning
    NEVER reads on-calls from the database, which is the structural fix
    for audit defect #1 (preview computing shifts from real on-calls in
    the DB while the on-call preview itself was only ever in-memory).

    `group_id` (this shift scope's own identity, used to tag
    ProposedShift.group_id and for staffing-limit bookkeeping) and
    `oncall_group_ids` (which keys in `proposed_oncalls` hold THIS
    scope's on-call info) are deliberately two separate parameters, NOT
    one - they only happen to be a single matching id when
    shift_scheduling_mode and oncall_scheduling_mode are both
    "per_group". Two real production bugs, both fixed here:

    - shifts "per_group" + on-calls "shared": on-calls are proposed
      under scope `None` while shift planning runs once per real group
      id - looking up `(friday, group_id)` would never match anything
      (`group_id` is never `None`), silently blinding every on-call-
      aware slot assignment below for that entire scope. Every day's
      shift got the exact same slot assignment every week, and the
      on-call person never received their own "oncall" slot during
      their own on-call week.
    - shifts "shared" + on-calls "per_group" (the reverse combination):
      a *single* shift scope (`group_id=None`) can have several
      *different* groups each running their own concurrent on-call the
      same week - `oncall_group_ids` must carry every one of those
      group ids, not just one, or the lookup silently misses every
      group but (at most) one, again blinding rule 1/2 for everyone
      else. This is why `oncall_user_ids_*` below are sets, not single
      optional ids - a day can legitimately have more than one
      concurrent "today's on-call" holder when this combination is in
      effect. Mandatory on-call coverage shifts stayed permanently
      unfilled for every single week under this combination before
      this fix, regardless of any other rule (rest_after_oncall
      included - that exclusion never even got a chance to apply,
      "oncall" role_slot was never assigned to anyone in the first
      place).

    Caller (plan_schedule.py) computes the correct value: `(None,)`
    when oncall_scheduling_mode is "shared"; else `(group_id,)` when
    this shift scope is itself per-group; else (this shift scope is
    "shared" but on-call is "per_group") every oncall-eligible group id
    (`request.oncall_groups`).

    `proposed_oncall_intervals` carries the on-call phase's *actual*
    proposed start/end per key (audit F11: rebuilding them from this
    shift scope's own anchor rules disagrees with the on-call proposal
    whenever the on-call scope has different anchor/end-hour overrides);
    `published_intervals` the published shifts' real start/end, so a
    locked row is carried through with its real hours (audit F20/F12).
    Both optional - absent means "derive from rules" (pure-planner unit
    tests).

    Every hard constraint (rest_after_oncall, the optional
    oncall_shift_overlap block) is checked on the user's *final*
    interval, after any staffing-max fallback (audit F19), and a
    rotation slot lost to such an exclusion is re-covered by another
    feasible user when one exists (audit F10)."""
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
    # Full intervals too, for the optional oncall_shift_overlap block
    # (audit F06: the resolved flag used to have no consumer here).
    oncall_intervals_by_user: dict[int, list[Interval]] = {}
    for oncall in existing_oncalls:
        oncall_ends_by_user.setdefault(oncall.user_id, []).append(oncall.end_time)
        oncall_intervals_by_user.setdefault(oncall.user_id, []).append(
            (oncall.start_time, oncall.end_time)
        )

    # Every proposed on-call relevant to this shift scope, grouped by
    # its own anchor Friday - a plain dict lookup instead of an
    # `oc_group_id != oncall_group_id` scan per call site, and lets a
    # single Friday hold more than one concurrently on-call user (see
    # this function's own docstring for why that's required).
    oncall_user_ids_by_friday: dict[date, set[int]] = {}
    # Already-published on-calls outside the window (the adapter
    # excludes in-window ones - those are re-proposed) seed the same
    # anchor -> holders index, so the window's first week can see its
    # real "last week" holder. Proposed entries below override them for
    # the same anchor. Keyed by scope like proposed_oncalls: in shared
    # on-call mode (`(None,)`) every one counts, else only the ones
    # snapshotted under a relevant group.
    oncall_mode_is_shared = oncall_group_ids == (None,)
    for oncall in existing_oncalls:
        if not oncall_mode_is_shared and oncall.group_id not in oncall_group_ids:
            continue
        start_day = oncall.start_time.date()
        anchor = start_day - timedelta(
            days=(start_day.weekday() - rules.oncall_anchor_weekday) % 7
        )
        oncall_user_ids_by_friday.setdefault(anchor, set()).add(oncall.user_id)
    proposed_anchors = {
        friday
        for (friday, oc_group_id) in proposed_oncalls
        if oc_group_id in oncall_group_ids
    }
    for anchor in proposed_anchors:
        oncall_user_ids_by_friday.pop(anchor, None)

    for (friday, oc_group_id), user_id in proposed_oncalls.items():
        if oc_group_id not in oncall_group_ids:
            continue
        interval = (proposed_oncall_intervals or {}).get((friday, oc_group_id))
        if interval is None:
            interval = (
                datetime.combine(friday, datetime.min.time()).replace(
                    hour=rules.oncall_anchor_start_hour
                ),
                datetime.combine(
                    friday + timedelta(days=7), datetime.min.time()
                ).replace(hour=rules.oncall_anchor_end_hour),
            )
        oncall_ends_by_user.setdefault(user_id, []).append(interval[1])
        oncall_intervals_by_user.setdefault(user_id, []).append(interval)
        oncall_user_ids_by_friday.setdefault(friday, set()).add(user_id)
    for ends in oncall_ends_by_user.values():
        ends.sort()

    def _exclusion_rule(
        user_id: int, role_slot: str, shift_start: datetime, shift_end: datetime
    ) -> str | None:
        """The hard constraint `user_id`'s *final* interval breaks, if any.
        role_slot == "oncall" is exempt from rest_after_oncall: that slot
        IS the on-call user's own coverage shift for the day their
        on-call starts/ends (the departing holder is still "this week's
        on-call for shift purposes" on the transition Friday - see
        _covering_anchor()), not a second, independent assignment rest
        could meaningfully apply to. Real production bug: with any
        rest_after_oncall configured, the 07:00 -> 13:00 gap tripped the
        check on every transition Friday, leaving the on-call shift
        permanently unfilled. The exemption only holds while the final
        slot is still "oncall" - a fallback to "default" is an ordinary
        shift and gets rest-checked like any other (audit F19)."""
        if role_slot != "oncall" and shift_violates_rest_after_oncall(
            shift_start,
            _last_oncall_end_before(user_id, shift_start, oncall_ends_by_user),
            rules.rest_after_oncall_hours,
        ):
            return "rest_after_oncall"
        if rules.oncall_shift_overlap_block and any(
            intervals_overlap(shift_start, shift_end, oc_start, oc_end)
            for oc_start, oc_end in oncall_intervals_by_user.get(user_id, ())
        ):
            return "oncall_shift_overlap"
        return None

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
        if eligible_users and not available_today:
            unfilled.append(
                UnfilledRequirement(
                    kind="no_available_user",
                    date=day,
                    group_id=group_id,
                    reason_code="no_available_user",
                )
            )

        oncall_user_ids_today = frozenset(
            oncall_user_ids_by_friday.get(_covering_anchor(day, rules), ())
        )
        last_week_friday = _covering_anchor(day - timedelta(days=7), rules)
        oncall_user_ids_last_week = frozenset(
            oncall_user_ids_by_friday.get(last_week_friday, ())
        )

        # Forward-looking (second-choice) half of rule 2: the holder of
        # the on-call week after the covering one. On a transition
        # Friday that is the on-call starting that same evening - which
        # is exactly who the admin's own correction puts on the
        # rotation slot when last week's holder is out of scope (1.2.0
        # production report: a former "only if it starts after `day`"
        # guard excluded them, leaving that Friday to the rotation-order
        # fallback, which only matched by coincidence of its offset).
        next_week_friday = _covering_anchor(day + timedelta(days=7), rules)
        oncall_user_ids_next_week = frozenset(
            oncall_user_ids_by_friday.get(next_week_friday, ())
        )

        published_slot_by_user = {
            user_id: _role_slot_for_shift_type(shift_type_id, rules)
            for (pub_date, user_id), shift_type_id in published.items()
            if pub_date == day
        }

        slot_by_user = assign_shift_slots_for_day(
            day,
            available_today,
            oncall_user_ids_today,
            oncall_user_ids_last_week,
            oncall_user_ids_next_week,
            rotation_order,
            rotation_anchor_epoch,
            published_slot_by_user,
        )

        # Locked rows first (stable order otherwise): they occupy their
        # slot whatever happens, so they must count against staffing_max
        # before any unlocked user is placed (audit F20: a locked row met
        # late in the loop used to push its slot over the cap).
        ordered_today = sorted(available_today, key=lambda u: (day, u.id) not in locked)
        today_start_index = len(proposed)
        rotation_lost_to_rule = False

        for user in ordered_today:
            if (day, user.id) in locked:
                published_shift_type_id = published.get((day, user.id))
                if published_shift_type_id is None:
                    unfilled.append(
                        UnfilledRequirement(
                            kind="staffing_max",
                            date=day,
                            group_id=group_id,
                            reason_code="locked_but_no_published_assignment",
                            detail="",
                        )
                    )
                    continue
                role_slot = _role_slot_for_shift_type(published_shift_type_id, rules)
                locked_interval = (published_intervals or {}).get((day, user.id))
                if locked_interval is None:
                    locked_interval = _slot_interval(day, slot_shift_type[role_slot][1])
                proposed.append(
                    _build_proposed_shift(
                        day,
                        user.id,
                        published_shift_type_id,
                        locked_interval,
                        group_id,
                        role_slot,
                        "unchanged",
                        ("locked - carried through unchanged",),
                    )
                )
                continue

            selected_slot = slot_by_user[user.id]
            role_slot = selected_slot
            shift_type_id, hours = slot_shift_type[role_slot]

            explanation = (f"role slot: {role_slot}",)
            if _slot_is_full(proposed, day, shift_type_id, rules):
                # Over the slot's staffing max: fall back to the default
                # slot rather than dropping the user for the whole day
                # (real production bug, see module docstring) - only a
                # full default slot too leaves them genuinely unfilled.
                default_type_id, default_hours = slot_shift_type["default"]
                if role_slot == "default" or _slot_is_full(
                    proposed, day, default_type_id, rules
                ):
                    unfilled.append(
                        UnfilledRequirement(
                            kind="staffing_max",
                            date=day,
                            group_id=group_id,
                            reason_code="staffing_max_reached",
                            detail=str(shift_type_id),
                        )
                    )
                    continue
                explanation = (
                    f"role slot: {role_slot} full (staffing max) - default slot instead",
                )
                role_slot = "default"
                shift_type_id, hours = default_type_id, default_hours

            # Hard constraints run on the FINAL interval, after any
            # fallback above (audit F19: rest used to be checked on the
            # originally selected slot only, so a fallback to an earlier
            # default slot - or an on-call holder losing their exemption -
            # could persist an insufficient-rest shift).
            interval = _slot_interval(day, hours)
            broken_rule = _exclusion_rule(user.id, role_slot, *interval)
            if broken_rule is not None:
                # "warning", not "hard_blocked": this user is excluded
                # from this one day right here - a routine, self-
                # mitigated outcome. "hard_blocked" is reserved for
                # _evaluate_safety's own defense-in-depth cases
                # (plan_schedule.py) - it aborts the ENTIRE apply, which a
                # single per-day exclusion must never do (real bug: it
                # used to, making any org with rest_after_oncall
                # configured unable to apply a multi-month generation).
                violations.append(
                    RuleViolation(
                        severity="warning",
                        rule_type=broken_rule,
                        group_id=group_id,
                        date=day,
                        user_id=user.id,
                        message=f"{broken_rule} violated - user excluded from this day",
                    )
                )
                if selected_slot == "rotation":
                    rotation_lost_to_rule = True
                continue

            proposed.append(
                _build_proposed_shift(
                    day,
                    user.id,
                    shift_type_id,
                    interval,
                    group_id,
                    role_slot,
                    _change_type(published.get((day, user.id)), shift_type_id),
                    explanation,
                )
            )

        if rotation_lost_to_rule:
            _repair_rotation_coverage(
                day,
                proposed,
                today_start_index,
                unfilled,
                group_id,
                locked,
                published,
                rotation_order,
                rotation_anchor_epoch,
                rules,
                slot_shift_type["rotation"],
                _exclusion_rule,
            )

        day += timedelta(days=1)

    return ShiftPlanFragment(
        proposed=tuple(proposed), unfilled=tuple(unfilled), violations=tuple(violations)
    )


def _change_type(published_shift_type_id: int | None, shift_type_id: int) -> str:
    if published_shift_type_id == shift_type_id:
        return "unchanged"
    return "reassigned" if published_shift_type_id is not None else "added"


def _slot_interval(day: date, hours: tuple[int, int]) -> Interval:
    start_hour, end_hour = hours
    midnight = datetime.combine(day, datetime.min.time())
    return midnight.replace(hour=start_hour), midnight.replace(hour=end_hour)


def _repair_rotation_coverage(
    day: date,
    proposed: list[ProposedShift],
    today_start_index: int,
    unfilled: list[UnfilledRequirement],
    group_id: int | None,
    locked: frozenset[tuple[date, int]],
    published: dict[tuple[date, int], int],
    rotation_order: tuple[UserRef, ...],
    rotation_anchor_epoch: date,
    rules: ResolvedRules,
    rotation_slot: tuple[int, tuple[int, int]],
    exclusion_rule: Callable[[int, str, datetime, datetime], str | None],
) -> None:
    """The user picked for the rotation slot was excluded by a hard
    constraint (rest/overlap): promote another feasible user already on
    the default slot today instead of leaving rotation coverage missing
    while they sit on 09-17 (audit F10). Candidates follow the day's
    rotated order, the same priority rule 7 uses. Nobody feasible ->
    an explicit role_uncovered requirement, never a silent gap."""
    rotation_type_id, rotation_hours = rotation_slot
    if any(s.role_slot == "rotation" for s in proposed[today_start_index:]):
        return
    if _slot_is_full(proposed, day, rotation_type_id, rules):
        return  # The admin's own cap - not a coverage gap.

    rotated = rotate(rotation_order, day, rotation_anchor_epoch)
    rank = {u.id: i for i, u in enumerate(rotated)}
    candidates = sorted(
        (
            (index, s)
            for index, s in enumerate(proposed)
            if index >= today_start_index
            and s.role_slot == "default"
            and (day, s.user_id) not in locked
        ),
        key=lambda item: rank.get(item[1].user_id, len(rank)),
    )
    interval = _slot_interval(day, rotation_hours)
    for index, current in candidates:
        if exclusion_rule(current.user_id, "rotation", *interval) is not None:
            continue
        proposed[index] = _build_proposed_shift(
            day,
            current.user_id,
            rotation_type_id,
            interval,
            group_id,
            "rotation",
            _change_type(published.get((day, current.user_id)), rotation_type_id),
            ("role slot: rotation (re-covered after a rule exclusion)",),
        )
        return

    unfilled.append(
        UnfilledRequirement(
            kind="role_uncovered",
            date=day,
            group_id=group_id,
            reason_code="rotation_uncovered",
            detail=str(rotation_type_id),
        )
    )


def _slot_is_full(
    proposed: list[ProposedShift], day: date, shift_type_id: int, rules: ResolvedRules
) -> bool:
    max_limit = rules.staffing_limits.get(shift_type_id)
    if max_limit is None:
        return False
    current_count = sum(
        1 for s in proposed if s.date == day and s.shift_type_id == shift_type_id
    )
    return current_count >= max_limit


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


def _covering_anchor(day: date, rules: ResolvedRules) -> date:
    """The anchor date of the on-call week covering `day`: the latest
    configured anchor weekday strictly before `day`, so on a transition
    day (the anchor weekday itself) it is still the departing holder's
    week. Identical to the former Monday-relative formula for a Friday
    anchor on working days, but correct for any anchor weekday (audit
    F11: with a Wednesday anchor, Thursday used to resolve to the
    *previous* Wednesday, so the current holder never got the oncall
    role)."""
    days_back = (day.weekday() - rules.oncall_anchor_weekday) % 7 or 7
    return day - timedelta(days=days_back)


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
    interval: Interval,
    group_id: int | None,
    role_slot: str,
    change_type: str,
    explanation: tuple[str, ...],
) -> ProposedShift:
    start_time, end_time = interval
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
