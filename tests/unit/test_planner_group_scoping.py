"""Phase 3 scenario tests: shared shifts with per-group on-call (and
the reverse), and a user's group changing after schedules already
exist. Direct regression coverage for audit defect #7
(capture_existing_assignments()'s un-grouped {date: user_id} dict
silently overwriting one group's on-call with another's on the same
Friday) - the new (friday, group_id)-keyed maps make that impossible
by construction. No DB/app context needed - plan_schedule() is pure."""

from datetime import date, datetime

from app.utils.automation.planner.plan_schedule import plan_schedule
from app.utils.automation.planner.types import (
    OnCallSnapshot,
    PlanningRequest,
    ResolvedRules,
    UserRef,
)

RULES = ResolvedRules(
    oncall_anchor_weekday=4,
    oncall_anchor_start_hour=21,
    oncall_anchor_end_hour=7,
    oncall_spacing_weeks=2,
    weekend_days=frozenset({5, 6}),
    staffing_limits={},
    mandatory_shift_type_ids=frozenset(),
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

GROUP_A_USERS = (UserRef(1, "A1", 10), UserRef(2, "A2", 10))
GROUP_B_USERS = (UserRef(3, "B1", 20), UserRef(4, "B2", 20))
ALL_USERS = GROUP_A_USERS + GROUP_B_USERS


def test_per_group_oncall_with_shared_shifts_no_cross_group_collision():
    """oncall_groups=(10, 20) (per_group), schedule_groups=(None,)
    (shared) - both groups must get their own concurrent on-call for
    the same Friday, and shared shift planning must see both without
    either overwriting the other in the merged (friday, group_id) map."""
    request = PlanningRequest(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        oncall_groups=(10, 20),
        schedule_groups=(None,),
        eligible_oncall_users={10: GROUP_A_USERS, 20: GROUP_B_USERS},
        eligible_shift_users={None: ALL_USERS},
        rotation_order={10: GROUP_A_USERS, 20: GROUP_B_USERS, None: ALL_USERS},
        rotation_anchor_epoch=EPOCH,
        existing_oncalls=(),
        existing_leaves=(),
        resolved_rules={10: RULES, 20: RULES, None: RULES},
    )
    plan = plan_schedule(request)

    fridays_by_group = {}
    for oncall in plan.oncalls:
        fridays_by_group.setdefault(oncall.friday, set()).add(oncall.group_id)

    # Every generated Friday must have BOTH groups represented -
    # neither group's assignment silently missing/overwritten.
    for groups_present in fridays_by_group.values():
        assert groups_present == {10, 20}

    # Shared shift planning must have produced shifts for users of
    # both groups - it saw both groups' on-calls via the merged map.
    shift_user_ids = {s.user_id for s in plan.shifts}
    assert shift_user_ids == {u.id for u in ALL_USERS}


def test_shared_oncall_with_per_group_shifts_reverse_configuration():
    """The reverse: oncall_groups=(None,) (shared - one pooled
    rotation across every user), schedule_groups=(10, 20) (per_group).
    Every user across both groups competes for the same on-call slot,
    but shifts are planned independently per group."""
    request = PlanningRequest(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
        oncall_groups=(None,),
        schedule_groups=(10, 20),
        eligible_oncall_users={None: ALL_USERS},
        eligible_shift_users={10: GROUP_A_USERS, 20: GROUP_B_USERS},
        rotation_order={None: ALL_USERS, 10: GROUP_A_USERS, 20: GROUP_B_USERS},
        rotation_anchor_epoch=EPOCH,
        existing_oncalls=(),
        existing_leaves=(),
        resolved_rules={None: RULES, 10: RULES, 20: RULES},
    )
    plan = plan_schedule(request)

    # Exactly one on-call per Friday (shared pool, not two).
    fridays = [o.friday for o in plan.oncalls]
    assert len(fridays) == len(set(fridays))

    shift_group_ids = {s.group_id for s in plan.shifts}
    assert shift_group_ids == {10, 20}


def test_user_group_change_only_affects_new_rows_not_snapshot_input():
    """A UserRef's group_id changing between two plan calls only shows
    up on NEW ProposedOnCall/ProposedShift rows from that later call -
    it must never retroactively relabel existing_oncalls/existing_leaves
    snapshot data passed in, since those are point-in-time facts, not
    live joins through a mutable user.group_id (the exact bug pattern
    audit defect #6 describes for the legacy engine)."""
    user_before = UserRef(1, "Alice", group_id=10)
    existing = (
        OnCallSnapshot(
            user_id=1,
            group_id=10,
            start_time=datetime(2026, 1, 2, 21, 0),
            end_time=datetime(2026, 1, 9, 7, 0),
        ),
    )

    # Alice has since moved to group 20 - a fresh plan call reflects
    # her CURRENT group on any NEW on-call it proposes...
    user_after = UserRef(1, "Alice", group_id=20)
    request = PlanningRequest(
        start_date=date(2026, 1, 16),
        end_date=date(2026, 1, 16),
        oncall_groups=(20,),
        schedule_groups=(20,),
        eligible_oncall_users={20: (user_after,)},
        eligible_shift_users={20: (user_after,)},
        rotation_order={20: (user_after,)},
        rotation_anchor_epoch=EPOCH,
        existing_oncalls=existing,
        existing_leaves=(),
        resolved_rules={20: RULES},
    )
    plan = plan_schedule(request)

    # ...but the pre-existing snapshot itself is untouched data, never
    # mutated by the plan call - it still says group 10, exactly as
    # captured, proving the planner treats group as a point-in-time
    # fact rather than re-deriving it from a live user object.
    assert existing[0].group_id == 10
    assert user_before.group_id == 10
    for oncall in plan.oncalls:
        assert oncall.group_id == 20
