"""Regression tests for the 1.2.0 production report "the new scheduling
system generates bad schedules" (screenshots in report/1.2.0/BUG_HUNT_1.2.0.md).

Production config reproduced here: shifts "per_group", on-call "shared",
group RUN = pierre/benjamin/morgan, group SOCLE = julien (on-call only),
on-call rotation julien -> pierre -> benjamin -> morgan, and RUN's
staffing_limits capping the rotation slot (07h-15h) and the on-call slot
(13h-21h) at 1 person each.

Two defects, both in shift_planner.py:
- The rotation slot went to BOTH last week's and next week's on-call
  holder. With the rotation slot capped at 1, the second one hit
  staffing_max and was dropped for the whole day (no shift at all) -
  Mon-Thu of every other week.
- "Last week's on-call" was only looked up among this plan's own
  proposed on-calls, never the already-published on-call right before
  the window, so the window's first week could not see its real
  predecessor.

Expected assignments are the admin's own manual correction ("good"
screenshots), confirmed rule: rotation slot = last week's on-call holder
if in scope, else next week's, else the rotation-order fallback; a user
who would exceed a slot's max falls back to the default slot."""

from datetime import date, datetime, timedelta

from app.utils.automation.planner.shift_planner import (
    assign_shift_slots_for_day,
    plan_shifts_for_scope,
)
from app.utils.automation.planner.types import OnCallSnapshot, ResolvedRules, UserRef

ONCALL_TYPE, ROTATION_TYPE, DEFAULT_TYPE = 100, 200, 300
RUN, SOCLE = 1, 2

JULIEN = UserRef(1, "julien", SOCLE)
PIERRE = UserRef(2, "pierre", RUN)
BENJAMIN = UserRef(3, "benjamin", RUN)
MORGAN = UserRef(4, "morgan", RUN)
RUN_USERS = (PIERRE, BENJAMIN, MORGAN)

RUN_RULES = ResolvedRules(
    oncall_anchor_weekday=4,
    oncall_anchor_start_hour=21,
    oncall_anchor_end_hour=7,
    oncall_spacing_weeks=2,
    weekend_days=frozenset({5, 6}),
    staffing_limits={DEFAULT_TYPE: 10, ONCALL_TYPE: 1, ROTATION_TYPE: 1},
    rest_after_oncall_hours=11,
    oncall_shift_overlap_block=False,
    oncall_shift_type_id=ONCALL_TYPE,
    oncall_slot_hours=(13, 21),
    rotation_shift_type_id=ROTATION_TYPE,
    rotation_slot_hours=(7, 15),
    default_shift_type_id=DEFAULT_TYPE,
    default_slot_hours=(9, 17),
)
EPOCH = date(2026, 11, 13)

# Shared on-call rotation as generated in production, from Nov 13 2026.
PROPOSED_ONCALLS = {
    (date(2026, 11, 13), None): JULIEN.id,
    (date(2026, 11, 20), None): PIERRE.id,
    (date(2026, 11, 27), None): BENJAMIN.id,
    (date(2026, 12, 4), None): MORGAN.id,
    (date(2026, 12, 11), None): JULIEN.id,
    (date(2026, 12, 18), None): PIERRE.id,
    (date(2026, 12, 25), None): BENJAMIN.id,
    (date(2027, 1, 1), None): MORGAN.id,
}

# The already-published on-call right before the window.
PRE_WINDOW_ONCALL = OnCallSnapshot(
    user_id=MORGAN.id,
    group_id=RUN,
    start_time=datetime(2026, 11, 6, 21, 0),
    end_time=datetime(2026, 11, 13, 7, 0),
)

# Week (Monday) -> {user_id: shift_type_id}, read off the admin's
# corrected nov26_good.png/dec26_good.png. Every day Mon-Fri of a week
# shares the same covering on-call week, so one row per week.
EXPECTED_BY_WEEK = {
    date(2026, 11, 16): {
        MORGAN.id: ROTATION_TYPE,
        BENJAMIN.id: DEFAULT_TYPE,
        PIERRE.id: DEFAULT_TYPE,
    },
    date(2026, 11, 23): {
        BENJAMIN.id: ROTATION_TYPE,
        MORGAN.id: DEFAULT_TYPE,
        PIERRE.id: ONCALL_TYPE,
    },
    date(2026, 11, 30): {
        PIERRE.id: ROTATION_TYPE,
        MORGAN.id: DEFAULT_TYPE,
        BENJAMIN.id: ONCALL_TYPE,
    },
    date(2026, 12, 7): {
        BENJAMIN.id: ROTATION_TYPE,
        PIERRE.id: DEFAULT_TYPE,
        MORGAN.id: ONCALL_TYPE,
    },
    date(2026, 12, 14): {
        MORGAN.id: ROTATION_TYPE,
        BENJAMIN.id: DEFAULT_TYPE,
        PIERRE.id: DEFAULT_TYPE,
    },
    date(2026, 12, 21): {
        BENJAMIN.id: ROTATION_TYPE,
        MORGAN.id: DEFAULT_TYPE,
        PIERRE.id: ONCALL_TYPE,
    },
    date(2026, 12, 28): {
        PIERRE.id: ROTATION_TYPE,
        MORGAN.id: DEFAULT_TYPE,
        BENJAMIN.id: ONCALL_TYPE,
    },
    date(2027, 1, 4): {
        BENJAMIN.id: ROTATION_TYPE,
        PIERRE.id: DEFAULT_TYPE,
        MORGAN.id: ONCALL_TYPE,
    },
}


def _plan_run_group(existing_oncalls=(PRE_WINDOW_ONCALL,)):
    return plan_shifts_for_scope(
        start_date=date(2026, 11, 16),
        end_date=date(2027, 1, 8),
        group_id=RUN,
        oncall_group_ids=(None,),
        eligible_users=RUN_USERS,
        proposed_oncalls=PROPOSED_ONCALLS,
        existing_oncalls=existing_oncalls,
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(JULIEN, PIERRE, BENJAMIN, MORGAN),
        rotation_anchor_epoch=EPOCH,
        rules=RUN_RULES,
    )


def test_production_schedule_matches_admin_manual_correction():
    fragment = _plan_run_group()
    by_day: dict[date, dict[int, int]] = {}
    for shift in fragment.proposed:
        by_day.setdefault(shift.date, {})[shift.user_id] = shift.shift_type_id

    for monday, expected in EXPECTED_BY_WEEK.items():
        for offset in range(5):
            day = monday + timedelta(days=offset)
            assert by_day.get(day) == expected, day


def test_every_run_user_gets_a_shift_every_weekday():
    """The visible symptom: a user silently got no shift at all."""
    fragment = _plan_run_group()
    assert fragment.unfilled == ()
    days = {s.date for s in fragment.proposed}
    for day in days:
        users_that_day = sorted(s.user_id for s in fragment.proposed if s.date == day)
        assert users_that_day == sorted(u.id for u in RUN_USERS), day


def test_pre_window_oncall_counts_as_last_week():
    """Without the already-published Nov 6 on-call, the first week has
    no "last week" holder - next week's (pierre) would be picked."""
    with_history = _plan_run_group()
    without_history = _plan_run_group(existing_oncalls=())

    def rotation_user(fragment, day):
        return next(
            s.user_id
            for s in fragment.proposed
            if s.date == day and s.shift_type_id == ROTATION_TYPE
        )

    assert rotation_user(with_history, date(2026, 11, 16)) == MORGAN.id
    assert rotation_user(without_history, date(2026, 11, 16)) == PIERRE.id


def test_last_week_holder_wins_over_next_week_holder():
    users = RUN_USERS
    result = assign_shift_slots_for_day(
        date(2026, 12, 14),
        users,
        frozenset(),
        frozenset({MORGAN.id}),
        frozenset({PIERRE.id}),
        users,
        EPOCH,
        {},
    )
    assert result == {
        MORGAN.id: "rotation",
        PIERRE.id: "default",
        BENJAMIN.id: "default",
    }


def test_next_week_holder_used_when_last_week_holder_out_of_scope():
    """Last week's holder (julien, SOCLE) isn't among RUN's users."""
    users = RUN_USERS
    result = assign_shift_slots_for_day(
        date(2026, 12, 21),
        users,
        frozenset({PIERRE.id}),
        frozenset({JULIEN.id}),
        frozenset({BENJAMIN.id}),
        users,
        EPOCH,
        {},
    )
    assert result == {
        PIERRE.id: "oncall",
        BENJAMIN.id: "rotation",
        MORGAN.id: "default",
    }


def test_slot_over_max_falls_back_to_default_slot():
    """Two concurrent last-week on-call holders (on-call "per_group",
    shift scope pooling both groups) both qualify for the rotation
    slot - the one over its cap gets the default slot instead of no
    shift at all."""
    rules = ResolvedRules(
        **{**RUN_RULES.__dict__, "staffing_limits": {ROTATION_TYPE: 1}}
    )
    fragment = plan_shifts_for_scope(
        start_date=date(2026, 12, 14),
        end_date=date(2026, 12, 14),
        group_id=None,
        oncall_group_ids=(RUN, SOCLE),
        eligible_users=(PIERRE, MORGAN),
        proposed_oncalls={
            (date(2026, 12, 4), RUN): PIERRE.id,
            (date(2026, 12, 4), SOCLE): MORGAN.id,
        },
        existing_oncalls=(),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(PIERRE, MORGAN),
        rotation_anchor_epoch=EPOCH,
        rules=rules,
    )
    assert sorted(s.shift_type_id for s in fragment.proposed) == [
        ROTATION_TYPE,
        DEFAULT_TYPE,
    ]
    assert fragment.unfilled == ()


def test_rotation_over_max_with_default_full_is_reported_unfilled():
    rules = ResolvedRules(
        **{
            **RUN_RULES.__dict__,
            "staffing_limits": {ROTATION_TYPE: 0, DEFAULT_TYPE: 0},
        }
    )
    fragment = plan_shifts_for_scope(
        start_date=date(2026, 12, 14),
        end_date=date(2026, 12, 14),
        group_id=RUN,
        oncall_group_ids=(None,),
        eligible_users=(PIERRE,),
        proposed_oncalls={},
        existing_oncalls=(),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(PIERRE,),
        rotation_anchor_epoch=EPOCH,
        rules=rules,
    )
    assert fragment.proposed == ()
    assert len(fragment.unfilled) == 1
    assert fragment.unfilled[0].reason_code == "staffing_max_reached"


def test_day_with_every_user_on_leave_is_reported_no_available_user():
    from app.utils.automation.planner.types import LeaveSpan

    day = date(2026, 12, 14)
    fragment = plan_shifts_for_scope(
        start_date=day,
        end_date=day,
        group_id=RUN,
        oncall_group_ids=(None,),
        eligible_users=RUN_USERS,
        proposed_oncalls={},
        existing_oncalls=(),
        existing_leaves=tuple(LeaveSpan(u.id, day, day) for u in RUN_USERS),
        locked=frozenset(),
        published={},
        rotation_order=RUN_USERS,
        rotation_anchor_epoch=EPOCH,
        rules=RUN_RULES,
    )
    assert fragment.proposed == ()
    assert [u.kind for u in fragment.unfilled] == ["no_available_user"]


def test_transition_friday_uses_incoming_holder_when_last_week_out_of_scope():
    """Friday Nov 27: pierre (covering week) holds the on-call slot,
    last week's holder julien is SOCLE (out of scope) - the admin's
    correction puts benjamin, whose on-call starts that same evening, on
    the rotation slot. The rotation-order fallback here would pick
    morgan (offset 0 at this epoch), so this can't pass by coincidence -
    the original nov26 run only matched on some Fridays because of the
    fallback's rotation offset."""
    friday = date(2026, 11, 27)
    fragment = plan_shifts_for_scope(
        start_date=friday,
        end_date=friday,
        group_id=RUN,
        oncall_group_ids=(None,),
        eligible_users=RUN_USERS,
        proposed_oncalls=PROPOSED_ONCALLS,
        existing_oncalls=(),
        existing_leaves=(),
        locked=frozenset(),
        published={},
        rotation_order=(MORGAN, PIERRE, BENJAMIN),
        rotation_anchor_epoch=friday,
        rules=RUN_RULES,
    )
    assert {s.user_id: s.shift_type_id for s in fragment.proposed} == {
        BENJAMIN.id: ROTATION_TYPE,
        MORGAN.id: DEFAULT_TYPE,
        PIERRE.id: ONCALL_TYPE,
    }
