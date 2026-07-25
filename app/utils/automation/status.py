"""
Automation status utilities for Kairos.

This module provides functions to check the current status of automation.
"""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.models import OnCall, Shift
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation
from app.utils.automation.rules import OnCallAnchorRule

if TYPE_CHECKING:
    from app.models import Group


def get_automation_status(
    group: "Group | None" = None, include_next_available: bool = True
) -> dict[str, Any]:
    """
    Return the current automation status.

    `group`: when given, every number is scoped to that Group's own
    members instead of pooling the whole organization - used by
    `/admin/automation`'s per-group statistics section. `group=None`
    (the default) preserves the original org-wide behavior exactly.

    `include_next_available`: the next-available-date search below is
    the most expensive part of this function (repeated existence
    queries, worst case one per already-filled week) - callers that
    don't need it (e.g. computing stats for a group whose scheduling
    mode isn't currently "per_group", where a per-group "next
    available" number wouldn't mean anything anyway) can skip it by
    passing False; `next_available_oncall_date` is then always None.

    Returns:
        Dictionary containing:
        - Number of existing on-calls
        - Number of existing shifts
        - Number of users eligible for on-calls
        - Number of users eligible for shifts
        - Next available date for generation
    """
    if group is None:
        oncall_count = OnCall.query.count()
        shift_count = Shift.query.count()
    else:
        oncall_count = OnCallRepository.count_for_group(group.id)
        shift_count = ShiftRepository.count_for_group(group.id)

    # Count eligible users
    oncall_eligible = len(OnCallAutomation.get_eligible_users(group=group))
    shift_eligible = len(
        AdvancedShiftAutomation.get_users_in_schedule_groups(group=group)
    )

    next_oncall_date = None
    if include_next_available:
        # Find the next available date (the first on-call anchor weekday
        # in the future with no on-call) - see OnCallAnchorRule for the
        # configurable weekday/start_hour (defaults to Friday 21:00, or
        # a Group's own override when `group` is given).
        anchor = OnCallAnchorRule.resolve(group=group)
        today = date.today()
        current_date = today
        while current_date.weekday() != anchor["weekday"]:
            current_date += timedelta(days=1)

        # Check whether an on-call already exists for this anchor date
        group_id = group.id if group is not None else None
        while next_oncall_date is None:
            start_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=anchor["start_hour"]
            )

            has_oncall = OnCallRepository.get_starting_at(start_time, group_id=group_id)

            if not has_oncall:
                next_oncall_date = current_date
            else:
                current_date += timedelta(days=7)

    return {
        "oncall_count": oncall_count,
        "shift_count": shift_count,
        "oncall_eligible_users": oncall_eligible,
        "shift_eligible_users": shift_eligible,
        "next_available_oncall_date": (
            next_oncall_date.strftime("%Y-%m-%d") if next_oncall_date else None
        ),
    }
