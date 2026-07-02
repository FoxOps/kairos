"""
Automation utilities for Leviia Schedule.

This module provides automation functionality for shifts and on-call rotations.
"""

from app.utils.automation.shift_automation import (
    generate_shifts,
    generate_oncall_rotations,
    check_shift_conflicts,
    check_oncall_conflicts
)
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation
from app.utils.automation.shift_automation_class import ShiftAutomation
from app.utils.automation.business_rules import BusinessRules

__all__ = [
    'generate_shifts',
    'generate_oncall_rotations',
    'check_shift_conflicts',
    'check_oncall_conflicts',
    'AdvancedShiftAutomation',
    'OnCallAutomation',
    'ShiftAutomation',
    'BusinessRules'
]
