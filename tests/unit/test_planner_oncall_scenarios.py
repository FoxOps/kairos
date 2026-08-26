"""Phase 3 scenario tests: subrange regeneration, insufficient users
for the spacing constraint, leave positioned before/during/after an
on-call week, and a non-default (non-Friday) on-call anchor. No DB/app
context needed - plan_oncalls_for_scope() is pure."""

from datetime import date

from app.utils.automation.planner.oncall_planner import plan_oncalls_for_scope
from app.utils.automation.planner.types import LeaveSpan, ResolvedRules, UserRef

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


def _plan(rotation_order, start, end, rules=BASE_RULES, **kwargs):
    defaults = {
        "group_id": None,
        "rotation_anchor_epoch": EPOCH,
        "existing_oncalls": (),
        "existing_leaves": (),
        "locked": frozenset(),
        "published": {},
        "preferred": {},
    }
    defaults.update(kwargs)
    return plan_oncalls_for_scope(
        start_date=start,
        end_date=end,
        rotation_order=rotation_order,
        rules=rules,
        **defaults,
    )


def test_subrange_regeneration_preserves_published_assignments():
    """Regenerating a subrange of an already-published schedule, with
    the currently published assignments fed forward as `published`/
    `preferred` (the real production usage - see
    OnCallAutomation.capture_existing_assignments(), which this
    mirrors), must reproduce those exact assignments rather than
    reshuffling them.

    Note: two *independent, blind* generations (no shared
    published/preferred state) over a subrange vs. the equivalent slice
    of a full range are NOT guaranteed to agree once a fairness_key is
    involved - the whole-range search optimizes fairness (e.g. minimal
    on-call count variance) over its own larger set of weeks, which can
    legitimately pick a different, equally-valid tie-broken solution
    than a narrower search with less context ever would. What IS
    guaranteed (and fixes audit defect #4) is that the *rotation
    offset* for a given date is date-derived and absolute - see
    test_planner_rotation_anchor.py - and that explicitly threading
    forward prior state (as below) reproduces it exactly."""
    users = tuple(UserRef(id=i, name=f"U{i}", group_id=None) for i in (1, 2, 3))
    full = _plan(users, date(2026, 1, 1), date(2026, 3, 31))

    published = {(p.friday, None): p.user_id for p in full.proposed}
    subrange = _plan(
        users,
        date(2026, 2, 1),
        date(2026, 2, 28),
        published=published,
        preferred=published,
    )
    full_by_friday = {p.friday: p.user_id for p in full.proposed}
    for proposed in subrange.proposed:
        assert full_by_friday[proposed.friday] == proposed.user_id


def test_insufficient_users_for_spacing_reports_unfilled():
    # 2 users, min_spacing_weeks=2: week 3 (2 weeks after week 1 for
    # each of them) is the earliest either could return - a 3-week
    # window forces week 2 unfillable (both already used weeks 1 and
    # would-be 3, and are 1 week too soon after either).
    users = (UserRef(1, "A", None), UserRef(2, "B", None))
    fragment = _plan(users, date(2026, 1, 2), date(2026, 1, 16))
    assert len(fragment.proposed) == 2
    assert len(fragment.unfilled) == 1
    assert fragment.unfilled[0].reason_code == "no_candidate_meets_spacing"


def test_leave_overlapping_oncall_week_excludes_candidate():
    users = (UserRef(1, "A", None), UserRef(2, "B", None), UserRef(3, "C", None))
    # Friday 2026-01-02 21:00 -> 2026-01-09 07:00. User 1 (first in
    # rotation) is on leave squarely inside that window.
    leave = LeaveSpan(user_id=1, start_date=date(2026, 1, 3), end_date=date(2026, 1, 5))
    fragment = plan_oncalls_for_scope(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        group_id=None,
        rotation_order=users,
        rotation_anchor_epoch=EPOCH,
        existing_oncalls=(),
        existing_leaves=(leave,),
        locked=frozenset(),
        published={},
        preferred={},
        rules=BASE_RULES,
    )
    assert len(fragment.proposed) == 1
    assert fragment.proposed[0].user_id != 1


def test_leave_before_and_after_oncall_week_does_not_exclude_candidate():
    users = (UserRef(1, "A", None), UserRef(2, "B", None))
    # Leave ends the day before the on-call window starts, and a
    # second one starts the day after it ends - neither overlaps.
    before = LeaveSpan(
        user_id=1, start_date=date(2025, 12, 30), end_date=date(2026, 1, 1)
    )
    after = LeaveSpan(
        user_id=1, start_date=date(2026, 1, 10), end_date=date(2026, 1, 12)
    )
    fragment = plan_oncalls_for_scope(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 2),
        group_id=None,
        rotation_order=users,
        rotation_anchor_epoch=EPOCH,
        existing_oncalls=(),
        existing_leaves=(before, after),
        locked=frozenset(),
        published={},
        preferred={},
        rules=BASE_RULES,
    )
    assert len(fragment.proposed) == 1
    assert fragment.proposed[0].user_id == 1


def test_custom_anchor_weekday_produces_weeks_on_that_weekday():
    users = (UserRef(1, "A", None), UserRef(2, "B", None))
    wednesday_rules = ResolvedRules(
        **{**BASE_RULES.__dict__, "oncall_anchor_weekday": 2}
    )
    fragment = _plan(users, date(2026, 1, 1), date(2026, 1, 31), rules=wednesday_rules)
    assert fragment.proposed
    for proposed in fragment.proposed:
        assert proposed.friday.weekday() == 2
