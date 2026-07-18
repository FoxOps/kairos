"""
Automation utilities for Kairos.

This module provides automation functionality for shifts and on-call rotations.
"""

from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation
from app.utils.automation.status import get_automation_status

__all__ = [
    "AdvancedShiftAutomation",
    "OnCallAutomation",
    "get_automation_status",
]
