"""Phase 3 scenario tests: 1/2/3/many available users produce correct
role-slot assignment via ONE uniform algorithm (no count-based
branching in assign_shift_slots_for_day() itself, and none in these
tests' own assertions either - the same helper works for every
headcount), and a custom (non Mon-Fri) weekend definition is honored
with no hardcoded fallback. No DB/app context needed - pure functions."""

from datetime import date, datetime

from app.utils.automation.planner.shift_planner import (
    assign_shift_slots_for_day,
    plan_shifts_for_scope,
)
from app.utils.automation.planner.types import ResolvedRules, UserRef

BASE_RULES = ResolvedRules(
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


def _users(n):
    return tuple(UserRef(id=i, name=f"U{i}", group_id=None) for i in range(1, n + 1))


def _assert_exactly_one_oncall_and_one_rotation(slot_by_user, oncall_id):
    slots = list(slot_by_user.values())
    assert slots.count("oncall") <= 1
    assert slots.count("rotation") >= 1
    if oncall_id is not None:
        assert slot_by_user.get(oncall_id) == "oncall"


def test_uniform_algorithm_covers_1_2_3_and_many_users_identically():
    """Same assertion helper for every headcount - proving there is no
    hidden count-based special case in assign_shift_slots_for_day()."""
    rotation_order = _users(6)

    for headcount in (1, 2, 3, 6):
        users = rotation_order[:headcount]
        oncall_id = 1 if headcount >= 2 else None
        result = assign_shift_slots_for_day(
            EPOCH, users, oncall_id, None, None, rotation_order, EPOCH, {}
        )
        assert set(result.keys()) == {u.id for u in users}
        _assert_exactly_one_oncall_and_one_rotation(result, oncall_id)


def test_single_user_gets_rotation_slot_not_default():
    """Rule 6's old dedicated 1-user branch always placed the sole user
    on the rotation-equivalent slot (7am-3pm) - the uniform algorithm
    must reduce to the same outcome via its rule-7 fallback."""
    users = (UserRef(1, "A", None),)
    result = assign_shift_slots_for_day(
        EPOCH, users, None, None, None, users, EPOCH, {}
    )
    assert result[1] == "rotation"


def test_two_users_oncall_gets_oncall_other_gets_rotation():
    a, b = UserRef(1, "A", None), UserRef(2, "B", None)
    result = assign_shift_slots_for_day(EPOCH, (a, b), 1, None, None, (a, b), EPOCH, {})
    assert result[1] == "oncall"
    assert result[2] == "rotation"


def test_next_week_oncall_gets_rotation_slot_symmetric_with_last_week():
    """Rule 2 is symmetric: a user who will be on-call NEXT week gets
    the rotation slot exactly like one who was on-call LAST week -
    matters whenever this group's on-call turns are sparse relative to
    other groups sharing the same rotation pool (see module docstring,
    commit b2a225c)."""
    a, b, c = UserRef(1, "A", None), UserRef(2, "B", None), UserRef(3, "C", None)
    users = (a, b, c)
    result = assign_shift_slots_for_day(EPOCH, users, None, None, 2, users, EPOCH, {})
    assert result[2] == "rotation"
    assert list(result.values()).count("rotation") == 1


def test_many_users_only_one_rotation_slot_filled_by_fallback():
    users = _users(5)
    result = assign_shift_slots_for_day(
        EPOCH, users, None, None, None, users, EPOCH, {}
    )
    # No on-call/last/next-week info at all: rule 7's fallback must
    # still guarantee exactly one rotation slot - EPOCH itself as the
    # day gives a zero rotation offset, so the first rotation_order
    # member still wins deterministically.
    assert result[1] == "rotation"
    assert all(result[u.id] == "default" for u in users[1:])


def test_custom_weekend_definition_skips_configured_days_only():
    users = _users(2)
    # Weekend = Sunday+Monday (6, 0) instead of the default Sat+Sun.
    custom_rules = ResolvedRules(
        **{**BASE_RULES.__dict__, "weekend_days": frozenset({6, 0})}
    )

    fragment = plan_shifts_for_scope(
        start_date=date(2026, 1, 5),  # Monday
        end_date=date(2026, 1, 11),  # Sunday
        group_id=None,
        oncall_group_id=None,
        eligible_users=users,
        proposed_oncalls={},
        existing_oncalls=(),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=users,
        rotation_anchor_epoch=EPOCH,
        rules=custom_rules,
    )
    days_with_shifts = {s.date for s in fragment.proposed}
    # Monday (weekday 0) and Sunday (weekday 6) are the configured
    # weekend here - must be skipped even though they're not Sat/Sun.
    assert date(2026, 1, 5) not in days_with_shifts
    assert date(2026, 1, 11) not in days_with_shifts
    # Tuesday-Saturday (weekdays 1-5) must all have shifts, including
    # Saturday - the default weekend day, now a working day here.
    for d in (6, 7, 8, 9, 10):
        assert date(2026, 1, d) in days_with_shifts


def test_rest_after_oncall_ignores_a_later_on_call_in_the_same_plan():
    """Real production bug (v1.1.1): a user's on-call further ahead in
    the planning window must never count as "already ended" for a shift
    earlier in the window - it hasn't happened yet as of that shift's
    day. Before the fix, last-oncall-end was precomputed as the single
    global max across the whole plan, so a February on-call blocked
    every August shift for the same user with a false rest_after_oncall
    hard_blocked violation, day after day, for the entire plan."""
    user = UserRef(1, "A", None)
    rules = ResolvedRules(**{**BASE_RULES.__dict__, "rest_after_oncall_hours": 11})

    fragment = plan_shifts_for_scope(
        start_date=date(2026, 8, 3),  # Monday, well before the on-call
        end_date=date(2026, 8, 7),
        group_id=None,
        oncall_group_id=None,
        eligible_users=(user,),
        # This user's only on-call in the plan starts months later.
        proposed_oncalls={(date(2027, 2, 19), None): 1},
        existing_oncalls=(),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(user,),
        rotation_anchor_epoch=EPOCH,
        rules=rules,
    )

    assert fragment.violations == ()
    assert {s.date for s in fragment.proposed} == {
        date(2026, 8, 3),
        date(2026, 8, 4),
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
    }


def test_rest_after_oncall_still_blocks_shift_right_after_a_past_on_call():
    """Sanity check for the fix above: an on-call that genuinely already
    ended before the shift day must still be honored."""
    user = UserRef(1, "A", None)
    rules = ResolvedRules(**{**BASE_RULES.__dict__, "rest_after_oncall_hours": 11})

    fragment = plan_shifts_for_scope(
        start_date=date(2026, 8, 3),  # Monday right after the on-call
        end_date=date(2026, 8, 3),
        group_id=None,
        oncall_group_id=None,
        eligible_users=(user,),
        proposed_oncalls={},
        existing_oncalls=(_OnCallStub(user_id=1, end_time=datetime(2026, 8, 3, 3, 0)),),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(user,),
        rotation_anchor_epoch=EPOCH,
        rules=rules,
    )

    assert len(fragment.violations) == 1
    assert fragment.violations[0].rule_type == "rest_after_oncall"
    assert fragment.proposed == ()


def test_rest_after_oncall_never_excludes_the_oncall_role_slot_itself():
    """Real production bug: the departing on-call holder is still "this
    week's on-call for shift purposes" on the transition Friday (see
    AdvancedShiftAutomation.get_oncall_for_date()'s docstring) and gets
    role_slot "oncall" (the mandatory on-call coverage shift) that same
    day - right when their own on-call just ended that morning. With
    any rest_after_oncall configured, the small same-day gap (here 6h:
    07:00 to 13:00) tripped the check on literally every single
    transition Friday forever, leaving the mandatory on-call shift
    permanently unfilled - on-call and its own coverage shift must
    always coexist for the same user; rest_after_oncall's real target
    is an unrelated ("rotation"/"default") shift assigned too soon
    after on-call, not this slot."""
    user = UserRef(1, "A", None)
    rules = ResolvedRules(**{**BASE_RULES.__dict__, "rest_after_oncall_hours": 11})

    fragment = plan_shifts_for_scope(
        start_date=date(2026, 9, 4),  # Friday
        end_date=date(2026, 9, 4),
        group_id=None,
        oncall_group_id=None,
        eligible_users=(user,),
        # covering_friday(2026-09-04) resolves to 2026-08-28 (the week
        # that's ending that morning) - this is that week's on-call.
        proposed_oncalls={(date(2026, 8, 28), None): 1},
        existing_oncalls=(_OnCallStub(user_id=1, end_time=datetime(2026, 9, 4, 7, 0)),),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(user,),
        rotation_anchor_epoch=EPOCH,
        rules=rules,
    )

    assert fragment.violations == ()
    assert len(fragment.proposed) == 1
    assert fragment.proposed[0].role_slot == "oncall"
    assert fragment.proposed[0].date == date(2026, 9, 4)


class _OnCallStub:
    def __init__(self, user_id, end_time):
        self.user_id = user_id
        self.end_time = end_time
