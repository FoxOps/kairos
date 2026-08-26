"""Non-pure adapter layer: turns real DB state into a `PlanningRequest`
for the pure planner core. Alongside `rule_resolution.py`, this is one
of the two files in the planner package allowed to touch the DB/ORM -
`plan_schedule()` and everything it calls stay pure and never resolve
anything themselves.

Every field is derived by reusing existing, already-tested functions
verbatim (`OnCallAutomation.get_eligible_users`/`get_rotation_order`,
`AdvancedShiftAutomation.get_users_in_schedule_groups`,
`SettingsService`'s scheduling-mode getters, `rule_resolution.py`) -
this module contains no new business logic, only translation into the
planner's own data shapes.
"""

from datetime import date

from app import db
from app.models import AutomationConfig, Group, Leave, OnCall
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.settings_service import SettingsService
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation
from app.utils.automation.planner.rule_resolution import (
    resolve_rotation_epoch,
    resolve_rules_for_groups,
)
from app.utils.automation.planner.types import (
    LeaveSpan,
    OnCallSnapshot,
    PlanningRequest,
    UserRef,
)


def _scoped_group_ids(is_per_group: bool, filter_field: str) -> tuple[int | None, ...]:
    """(None,) for "shared" mode (one pooled scope), else every Group id
    eligible for that scope - mirrors AutomationAdminService.generate_full's/
    refresh_shifts's own identical computation."""
    if not is_per_group:
        return (None,)
    groups = Group.query.filter_by(**{filter_field: True}).all()
    return tuple(g.id for g in groups)


def _user_refs(users) -> tuple[UserRef, ...]:
    return tuple(UserRef(id=u.id, name=u.name, group_id=u.group_id) for u in users)


def _group_or_none(group_id: int | None) -> Group | None:
    return db.session.get(Group, group_id) if group_id is not None else None


def build_planning_request(
    start_date: date,
    end_date: date,
    shift_start_date: date | None = None,
    restrict_to_group_id: int | None = None,
) -> PlanningRequest:
    """The DB-to-PlanningRequest boundary. Read-only - never writes
    anything. Reproduces the exact scoping/eligibility/rotation logic
    `AutomationAdminService.generate_full()`/`refresh_shifts()` already
    use, so a `PlanningRequest` built here plans over the same
    population the legacy engine would.

    `shift_start_date`: pass the caller's literal (unwidened) requested
    start when `start_date` itself has been widened to a covering Friday
    (see OnCallAutomation.align_regeneration_start) for on-call boundary
    correctness - see PlanningRequest.shift_start_date's own docstring
    for why shift planning must not inherit that widening. `None` (every
    call site through phase 6) means "no widening happened, use
    start_date for shifts too" - published_shifts/locked_shifts are then
    fetched over the same [start_date, end_date] range as before,
    unchanged behavior.

    `restrict_to_group_id`: narrows oncall_groups/schedule_groups to at
    most that one group id, mirroring how
    AdvancedShiftAutomation.rebalance_after_leave()'s legacy code scopes
    itself to the leave owner's own Group under "per_group" mode instead
    of replanning every other group's schedule too. Only has an effect
    when the relevant scheduling mode is "per_group" (oncall_groups/
    schedule_groups is otherwise always `(None,)`, "shared" mode's one
    pooled scope, which a single group id cannot meaningfully narrow -
    same reasoning the legacy code already applies via its own
    `... if mode == "per_group" else None` fallback). Expressed as an
    intersection with the normal eligible-groups computation, not a
    separate lookup - a group ineligible for that scope still narrows to
    an empty tuple, exactly like today's behavior when no groups are
    eligible at all."""
    effective_shift_start = shift_start_date or start_date
    oncall_groups = _scoped_group_ids(
        SettingsService.get_oncall_scheduling_mode() == "per_group",
        "is_part_of_oncall",
    )
    schedule_groups = _scoped_group_ids(
        SettingsService.get_shift_scheduling_mode() == "per_group",
        "is_part_of_schedule",
    )
    if restrict_to_group_id is not None:
        # (None,) is the "shared" mode sentinel, not a real group id -
        # `None == restrict_to_group_id` is always False, so filtering
        # it unconditionally would wrongly collapse shared mode's one
        # pooled scope to an empty tuple instead of leaving it alone.
        if oncall_groups != (None,):
            oncall_groups = tuple(g for g in oncall_groups if g == restrict_to_group_id)
        if schedule_groups != (None,):
            schedule_groups = tuple(
                g for g in schedule_groups if g == restrict_to_group_id
            )

    eligible_oncall_users = {
        group_id: _user_refs(
            OnCallAutomation.get_eligible_users(group=_group_or_none(group_id))
        )
        for group_id in oncall_groups
    }
    eligible_shift_users = {
        group_id: _user_refs(
            AdvancedShiftAutomation.get_users_in_schedule_groups(
                group=_group_or_none(group_id)
            )
        )
        for group_id in schedule_groups
    }

    # Rotation order is read for the union of both scope sets - shift
    # planning's own rule-7 fallback (assign_shift_slots_for_day) reads
    # PlanningRequest.rotation_order.get(group_id, ()) too, not just
    # the on-call solver.
    rotation_order_ids = AutomationConfig.get_rotation_order()
    all_group_ids = tuple(dict.fromkeys((*oncall_groups, *schedule_groups)))
    rotation_order = {
        group_id: _user_refs(
            OnCallAutomation.get_rotation_order(
                rotation_order_ids=rotation_order_ids,
                group=_group_or_none(group_id),
            )
        )
        for group_id in all_group_ids
    }

    # Every user appearing anywhere in this request's population -
    # existing_oncalls/existing_leaves must be fetched for exactly this
    # set, unclipped by date, to reproduce AvailabilityIndex.__init__'s
    # own (unclipped-by-date, clipped-by-user) query shape.
    all_user_ids: set[int] = set()
    for users in (
        *eligible_oncall_users.values(),
        *eligible_shift_users.values(),
        *rotation_order.values(),
    ):
        all_user_ids.update(u.id for u in users)

    # Excludes on-calls whose own anchor date falls INSIDE
    # [start_date, end_date] - those are exactly the assignments this
    # same request is (re)planning, not fixed external history. Without
    # this exclusion, re-planning an already-applied window would see a
    # user's own just-applied on-call for that same week as a self-
    # conflict (identical interval overlaps itself) via
    # AvailabilityIndex.has_oncall_conflict(), forcing a spurious
    # reassignment on every subsequent plan of the same window - the
    # exact "delete before regenerate" problem this rework's apply_plan
    # (never deletes before planning) was designed to avoid, resurfacing
    # here if not filtered. Spacing/conflict checks against on-calls
    # OUTSIDE the window (before start_date or after end_date) are still
    # needed and kept - inter-week spacing WITHIN the window is already
    # enforced by the solver's own backtracking search state, not by
    # this snapshot list.
    existing_oncalls = tuple(
        OnCallSnapshot(
            user_id=o.user_id,
            group_id=o.group_id,
            start_time=o.start_time,
            end_time=o.end_time,
        )
        for o in OnCall.query.filter(OnCall.user_id.in_(all_user_ids)).all()
        if not (start_date <= o.start_time.date() <= end_date)
    )
    existing_leaves = tuple(
        LeaveSpan(
            user_id=leave.user_id,
            start_date=leave.start_date,
            end_date=leave.end_date,
        )
        for leave in Leave.query.filter(Leave.user_id.in_(all_user_ids)).all()
    )

    # Keyed by SCOPE group_id (matching oncall_groups/what
    # plan_oncalls_for_scope actually looks up), NOT the row's own
    # group_id column - in "shared" mode oncall_groups is always
    # (None,), but an OnCall row's own group_id is still the assigned
    # user's real (snapshotted) group, never None. Keying by the row's
    # own group_id here would make every existing on-call invisible to
    # published_oncalls/locked_oncalls lookups whenever mode is shared
    # (the common case), since plan_oncalls_for_scope only ever queries
    # (friday, None) in that mode. In "per_group" mode the row's own
    # group_id already equals the scope it was generated under, so
    # this is a no-op there.
    oncall_mode_is_shared = oncall_groups == (None,)
    overlapping_oncalls = OnCallRepository.list_overlapping_range(start_date, end_date)
    if restrict_to_group_id is not None:
        # Without this, an on-call belonging to a group OUTSIDE the
        # restriction (never planned by this request at all, since
        # oncall_groups was narrowed above) would still show up in
        # published_oncalls unfiltered - compute_diff() would then see
        # it published but never re-proposed (this request's
        # oncall_groups never included that group's scope) and mark it
        # "removed", and apply_plan would delete another group's
        # on-call nobody asked to touch. Restricting to `all_user_ids`
        # (this request's own real population, already computed above)
        # is the same principle existing_oncalls/existing_leaves
        # already apply a few lines up - published_oncalls/published_shifts
        # were the one place that had forgotten to.
        overlapping_oncalls = [
            o for o in overlapping_oncalls if o.user_id in all_user_ids
        ]
    published_oncalls = {
        (
            o.start_time.date(),
            None if oncall_mode_is_shared else o.group_id,
        ): o.user_id
        for o in overlapping_oncalls
    }
    locked_oncalls = frozenset(
        (o.start_time.date(), None if oncall_mode_is_shared else o.group_id)
        for o in overlapping_oncalls
        if o.locked
    )

    # Fetched over [effective_shift_start, end_date], NOT the (possibly
    # widened) [start_date, end_date] - shift planning's own day-loop
    # starts at effective_shift_start too (see plan_schedule.py), so
    # published_shifts must match that exact range. Fetching the wider
    # range here would include shifts on days the day-loop never visits,
    # which compute_diff() would then misdiff as "removed" (published
    # but never re-proposed) - apply_plan would delete them despite
    # nobody ever asking to regenerate that far back.
    shifts_in_range = ShiftRepository.list_in_date_range_with_user(
        effective_shift_start, end_date
    )
    if restrict_to_group_id is not None:
        # Same reasoning as overlapping_oncalls above: a shift belonging
        # to a user outside this request's own restricted population
        # would otherwise be misdiffed as "removed" (published, but
        # eligible_shift_users never includes that user under the
        # restriction, so no scope ever re-proposes it) and deleted.
        shifts_in_range = [s for s in shifts_in_range if s.user_id in all_user_ids]
    published_shifts = {(s.date, s.user_id): s.shift_type_id for s in shifts_in_range}
    locked_shifts = frozenset((s.date, s.user_id) for s in shifts_in_range if s.locked)

    return PlanningRequest(
        start_date=start_date,
        end_date=end_date,
        oncall_groups=oncall_groups,
        schedule_groups=schedule_groups,
        eligible_oncall_users=eligible_oncall_users,
        eligible_shift_users=eligible_shift_users,
        rotation_order=rotation_order,
        rotation_anchor_epoch=resolve_rotation_epoch(),
        existing_oncalls=existing_oncalls,
        existing_leaves=existing_leaves,
        published_oncalls=published_oncalls,
        published_shifts=published_shifts,
        # Reflects the real `locked` column - this adapter is the sole
        # source of truth for "what does DB state say is locked." No
        # admin UI sets `locked=True` yet (phase 5 ships the column and
        # this read-side only), so both are empty until one exists.
        locked_oncalls=locked_oncalls,
        locked_shifts=locked_shifts,
        # Seeded from published state - the long-term replacement for
        # OnCallAutomation.capture_existing_assignments() (see phase 8):
        # the new pipeline never deletes before planning, so "preferred"
        # is simply "whatever is currently published."
        preferred_oncall_assignments=dict(published_oncalls),
        resolved_rules=resolve_rules_for_groups(all_group_ids),
        shift_start_date=shift_start_date,
    )
