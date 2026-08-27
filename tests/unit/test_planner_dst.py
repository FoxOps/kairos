"""Phase 3 scenario test: DST transitions must not miscompute on-call
week boundaries. Shift/OnCall datetimes in this codebase are naive
wall-clock values meaning "local time in the org's configured
timezone" (see OnCall.is_active()'s own docstring) - the planner
follows the exact same convention, so a DST transition weekend is just
two calendar dates 7 days apart, never a real elapsed-hours computation
that DST would perturb. This test proves the planner doesn't
accidentally introduce timezone-aware arithmetic anywhere in the
on-call week construction path."""

from datetime import date

from app.utils.automation.planner.oncall_planner import plan_oncalls_for_scope
from app.utils.automation.planner.types import ResolvedRules, UserRef

RULES = ResolvedRules(
    oncall_anchor_weekday=4,
    oncall_anchor_start_hour=21,
    oncall_anchor_end_hour=7,
    oncall_spacing_weeks=2,
    weekend_days=frozenset({5, 6}),
    staffing_limits={},
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
USERS = (UserRef(1, "A", None), UserRef(2, "B", None), UserRef(3, "C", None))


def test_oncall_week_spans_exactly_seven_naive_calendar_days_across_dst():
    # France's spring-forward (last Sunday of March) and fall-back
    # (last Sunday of October) both fall inside these ranges.
    for start, end in (
        (date(2026, 3, 20), date(2026, 4, 3)),
        (date(2026, 10, 23), date(2026, 11, 6)),
    ):
        fragment = plan_oncalls_for_scope(
            start_date=start,
            end_date=end,
            group_id=None,
            rotation_order=USERS,
            rotation_anchor_epoch=EPOCH,
            existing_oncalls=(),
            existing_leaves=(),
            locked=frozenset(),
            published={},
            rules=RULES,
        )
        for proposed in fragment.proposed:
            # Naive wall-clock arithmetic: exactly 7*24h between start
            # and end, regardless of any real DST transition inside
            # the window - a tz-aware computation would show 167h or
            # 169h instead on a transition week.
            elapsed_hours = (
                proposed.end_time - proposed.start_time
            ).total_seconds() / 3600
            assert elapsed_hours == 7 * 24 - (
                RULES.oncall_anchor_start_hour - RULES.oncall_anchor_end_hour
            )
            assert proposed.friday.weekday() == RULES.oncall_anchor_weekday
