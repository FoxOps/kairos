"""Absolute-week rotation anchoring for the automation planner.

Replaces oncall_automation.py's _generate_for_fridays week_index, which
is the enumerate() position over that specific call's own local `weeks`
list - so two different generation calls covering the same Friday (a
6-month generation vs. six successive monthly ones, or two adjacent
"Rafraichir" calls) could compute a different rotation offset for it,
producing unfair repetition or unexpected reassignment.

absolute_week_index() depends only on the calendar date and the
rotation order's length, never on how many other weeks happen to be in
the current request - the same Friday always maps to the same offset
regardless of what range it was computed within.
"""

from datetime import date

from app.utils.automation.planner.types import UserRef


def absolute_week_index(anchor_date: date, epoch: date) -> int:
    """Number of whole 7-day periods between `epoch` and `anchor_date`.
    Advances by exactly 1 for every successive weekly anchor date
    (Friday, Wednesday, whatever OnCallAnchorRule resolves to for a
    given group) regardless of which weekday that is - integer division
    by 7 of a sequence spaced exactly 7 days apart is consistent no
    matter the additive offset from `epoch`."""
    return (anchor_date - epoch).days // 7


def rotate(
    order: tuple[UserRef, ...], anchor_date: date, epoch: date
) -> tuple[UserRef, ...]:
    """`order` rotated so the user at the computed absolute offset comes
    first - the same anchor_date always yields the same rotation
    regardless of what other dates are being planned in the same call."""
    if not order:
        return order
    offset = absolute_week_index(anchor_date, epoch) % len(order)
    return order[offset:] + order[:offset]
