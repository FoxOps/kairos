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


def build_planning_request(start_date: date, end_date: date) -> PlanningRequest:
    """The DB-to-PlanningRequest boundary. Read-only - never writes
    anything. Reproduces the exact scoping/eligibility/rotation logic
    `AutomationAdminService.generate_full()`/`refresh_shifts()` already
    use, so a `PlanningRequest` built here plans over the same
    population the legacy engine would."""
    oncall_groups = _scoped_group_ids(
        SettingsService.get_oncall_scheduling_mode() == "per_group",
        "is_part_of_oncall",
    )
    schedule_groups = _scoped_group_ids(
        SettingsService.get_shift_scheduling_mode() == "per_group",
        "is_part_of_schedule",
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

    existing_oncalls = tuple(
        OnCallSnapshot(
            user_id=o.user_id,
            group_id=o.group_id,
            start_time=o.start_time,
            end_time=o.end_time,
        )
        for o in OnCall.query.filter(OnCall.user_id.in_(all_user_ids)).all()
    )
    existing_leaves = tuple(
        LeaveSpan(
            user_id=leave.user_id,
            start_date=leave.start_date,
            end_date=leave.end_date,
        )
        for leave in Leave.query.filter(Leave.user_id.in_(all_user_ids)).all()
    )

    published_oncalls = {
        (o.start_time.date(), o.group_id): o.user_id
        for o in OnCallRepository.list_overlapping_range(start_date, end_date)
    }
    published_shifts = {
        (s.date, s.user_id): s.shift_type_id
        for s in ShiftRepository.list_in_date_range_with_user(start_date, end_date)
    }

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
        # No `locked` column exists yet (added in phase 5) - nothing is
        # locked today, matching that this adapter is the sole source
        # of truth for "what does DB state say is locked."
        locked_oncalls=frozenset(),
        locked_shifts=frozenset(),
        # Seeded from published state - the long-term replacement for
        # OnCallAutomation.capture_existing_assignments() (see phase 8):
        # the new pipeline never deletes before planning, so "preferred"
        # is simply "whatever is currently published."
        preferred_oncall_assignments=dict(published_oncalls),
        resolved_rules=resolve_rules_for_groups(all_group_ids),
    )
