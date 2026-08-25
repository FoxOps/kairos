"""Diffs a proposed plan against the currently published schedule.

Oncall and shift diff entries have a genuinely different "slot"
identity, both represented by the same ScheduleDiffEntry shape:
- An on-call slot is (friday, group_id) - two groups can hold
  concurrent on-calls on the same Friday, so group_id is part of the
  slot's identity.
- A shift "slot" is really just the user themselves (Shift is unique
  per (user_id, date) - see uq_shift_user_date) - what actually changes
  between published and proposed is the shift_type_id (which role slot
  they hold), not who the row belongs to. For a shift diff entry,
  published_user_id/proposed_user_id are both just that row's user_id
  when the row exists on that side, and group_id is informational only
  (PlanningRequest.published_shifts doesn't carry group_id, so a
  "removed" shift entry - the user had a published shift but the plan
  proposes none - always reports group_id=None; this never affects
  correctness, since the locked-shift safety check in plan_schedule.py
  keys off (date, user_id), not group_id).
"""

from datetime import date

from app.utils.automation.planner.types import (
    ProposedOnCall,
    ProposedShift,
    ScheduleDiffEntry,
)


def compute_diff(
    oncalls: tuple[ProposedOnCall, ...],
    shifts: tuple[ProposedShift, ...],
    published_oncalls: dict[tuple[date, int | None], int],
    published_shifts: dict[tuple[date, int], int],
) -> tuple[ScheduleDiffEntry, ...]:
    entries: list[ScheduleDiffEntry] = []

    proposed_oncall_keys = {(o.friday, o.group_id) for o in oncalls}
    for o in oncalls:
        entries.append(
            ScheduleDiffEntry(
                kind="oncall",
                date=o.friday,
                group_id=o.group_id,
                published_user_id=published_oncalls.get((o.friday, o.group_id)),
                proposed_user_id=o.user_id,
                change_type=o.change_type,
            )
        )
    for (friday, group_id), user_id in published_oncalls.items():
        if (friday, group_id) not in proposed_oncall_keys:
            entries.append(
                ScheduleDiffEntry(
                    kind="oncall",
                    date=friday,
                    group_id=group_id,
                    published_user_id=user_id,
                    proposed_user_id=None,
                    change_type="removed",
                )
            )

    proposed_shift_keys = {(s.date, s.user_id) for s in shifts}
    for s in shifts:
        was_published = (s.date, s.user_id) in published_shifts
        entries.append(
            ScheduleDiffEntry(
                kind="shift",
                date=s.date,
                group_id=s.group_id,
                published_user_id=s.user_id if was_published else None,
                proposed_user_id=s.user_id,
                change_type=s.change_type,
            )
        )
    for pub_date, user_id in published_shifts:
        if (pub_date, user_id) not in proposed_shift_keys:
            entries.append(
                ScheduleDiffEntry(
                    kind="shift",
                    date=pub_date,
                    group_id=None,
                    published_user_id=user_id,
                    proposed_user_id=None,
                    change_type="removed",
                )
            )

    return tuple(entries)
