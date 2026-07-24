"""
Rule-type registry for the configurable automation rules engine.

Each rule type is a small class (subclassing AutomationRuleType, see
base.py) describing what its `params` JSON looks like, what it
defaults to when unconfigured, and how to resolve its effective value
for a given Group (or the organization default, see
AutomationRule.resolve_params). Adding a new rule type means adding a
class here and registering it below - no migration needed, since
AutomationRule.params is generic JSON.
"""

from app.utils.automation.rules.base import AutomationRuleType
from app.utils.automation.rules.mandatory_shift import MandatoryShiftRule
from app.utils.automation.rules.oncall_anchor import OnCallAnchorRule
from app.utils.automation.rules.oncall_shift_overlap import OnCallShiftOverlapRule
from app.utils.automation.rules.oncall_spacing import OnCallSpacingRule
from app.utils.automation.rules.rest_after_oncall import RestAfterOnCallRule
from app.utils.automation.rules.shift_slots import ShiftSlotsRule
from app.utils.automation.rules.staffing_limits import StaffingLimitsRule
from app.utils.automation.rules.weekend_definition import WeekendDefinitionRule

RULE_TYPES: dict[str, type[AutomationRuleType]] = {
    rule_cls.rule_type: rule_cls
    for rule_cls in (
        OnCallAnchorRule,
        OnCallSpacingRule,
        ShiftSlotsRule,
        WeekendDefinitionRule,
        StaffingLimitsRule,
        MandatoryShiftRule,
        RestAfterOnCallRule,
        OnCallShiftOverlapRule,
    )
}

__all__ = [
    "AutomationRuleType",
    "RULE_TYPES",
    "OnCallAnchorRule",
    "OnCallSpacingRule",
    "ShiftSlotsRule",
    "WeekendDefinitionRule",
    "StaffingLimitsRule",
    "MandatoryShiftRule",
    "RestAfterOnCallRule",
    "OnCallShiftOverlapRule",
]
