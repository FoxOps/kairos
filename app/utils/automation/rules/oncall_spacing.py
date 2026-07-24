"""Configurable legal minimum spacing between two on-calls for the
same person. Replaces the previously hardcoded `2` (weeks), duplicated
in AvailabilityIndex.meets_spacing_constraint and the local
meets_spacing() closure in _solve_max_filled_weeks
(app/utils/automation/oncall_automation.py)."""

from app.utils.automation.rules.base import AutomationRuleType


class OnCallSpacingRule(AutomationRuleType):
    """`min_spacing_weeks`: minimum number of weeks required between
    two on-call periods for the same user."""

    rule_type = "oncall_spacing"

    @classmethod
    def default_params(cls) -> dict:
        return {"min_spacing_weeks": 2}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        weeks = params.get("min_spacing_weeks")
        if not isinstance(weeks, int) or isinstance(weeks, bool) or weeks < 1:
            errors.append("min_spacing_weeks must be an integer >= 1")
        return errors
