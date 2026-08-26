"""Pure hard-constraint predicates shared by the manual creation/move
path (app/utils/helpers/common_helpers.py) and the automation planner
(app/utils/automation/planner/). Extracted so both paths make the exact
same accept/reject decision instead of duplicating - and potentially
diverging on - the same logic: automatic generation used to construct
Shift/OnCall objects directly without ever calling the manual path's
checks, so the same assignment could be rejected when entered manually
but created successfully by automation. No DB access, no Flask
context - callers gather the raw counts/intervals/flags themselves."""

from datetime import datetime, timedelta


def intervals_overlap(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> bool:
    """True if [start_a, end_a) and [start_b, end_b) overlap at all."""
    return start_a < end_b and start_b < end_a


def shift_violates_staffing_max(current_count: int, max_limit: int | None) -> bool:
    """True if `current_count` already-assigned shifts for the same
    slot/day meet or exceed `max_limit` (staffing_limits.max) - None
    means unconfigured/unlimited, never a violation."""
    return max_limit is not None and current_count >= max_limit


def shift_violates_rest_after_oncall(
    shift_start: datetime, last_oncall_end: datetime | None, min_rest_hours: int
) -> bool:
    """True if `shift_start` falls within `min_rest_hours` of the end of
    the user's most recent on-call (rest_after_oncall) - 0 (unconfigured)
    or no prior on-call means the rule can't be violated."""
    if min_rest_hours <= 0 or last_oncall_end is None:
        return False
    return (shift_start - last_oncall_end) < timedelta(hours=min_rest_hours)


def shift_violates_oncall_overlap(has_overlapping_oncall: bool, block: bool) -> bool:
    """True if `block` (oncall_shift_overlap) is enabled and the shift's
    period overlaps an existing on-call for the same user. `block`
    defaults to False - on-call duty coexists with normal shifts unless
    a group explicitly opts into the stricter behavior."""
    return block and has_overlapping_oncall


def oncall_violates_shift_overlap(has_overlapping_shift: bool, block: bool) -> bool:
    """Symmetric to shift_violates_oncall_overlap, for the on-call
    creation/move path."""
    return block and has_overlapping_shift
