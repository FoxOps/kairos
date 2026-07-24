"""
Automation status utilities for Kairos.

This module provides functions to check the current status of automation.
"""

from datetime import date, datetime, timedelta
from typing import Any

from app.models import OnCall, Shift
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation
from app.utils.automation.rules import OnCallAnchorRule


def get_automation_status() -> dict[str, Any]:
    """
    Return the current automation status.

    Returns:
        Dictionary containing:
        - Number of existing on-calls
        - Number of existing shifts
        - Number of users eligible for on-calls
        - Number of users eligible for shifts
        - Next available date for generation
    """
    # Count existing on-calls
    oncall_count = OnCall.query.count()

    # Count existing shifts
    shift_count = Shift.query.count()

    # Count eligible users
    oncall_eligible = len(OnCallAutomation.get_eligible_users())
    shift_eligible = len(AdvancedShiftAutomation.get_users_in_schedule_groups())

    # Find the next available date (the first on-call anchor weekday in
    # the future with no on-call) - see OnCallAnchorRule for the
    # configurable weekday/start_hour (defaults to Friday 21:00).
    anchor = OnCallAnchorRule.resolve()
    today = date.today()
    current_date = today
    while current_date.weekday() != anchor["weekday"]:
        current_date += timedelta(days=1)

    # Check whether an on-call already exists for this anchor date
    next_oncall_date = None
    while next_oncall_date is None:
        start_time = datetime.combine(current_date, datetime.min.time()).replace(
            hour=anchor["start_hour"]
        )

        has_oncall = OnCall.query.filter(OnCall.start_time == start_time).first()

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
