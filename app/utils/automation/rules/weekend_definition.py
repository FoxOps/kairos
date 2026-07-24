"""Configurable weekend definition - which weekdays shift generation
treats as non-working days. Replaces the previously hardcoded
`date.weekday() >= 5` (Saturday/Sunday) checks in
AdvancedShiftAutomation."""

from datetime import date

from app.utils.automation.rules.base import AutomationRuleType


class WeekendDefinitionRule(AutomationRuleType):
    """`weekend_days`: list of `date.weekday()` values (Monday=0 ...
    Sunday=6) that count as the weekend."""

    rule_type = "weekend_definition"

    @classmethod
    def default_params(cls) -> dict:
        return {"weekend_days": [5, 6]}  # Saturday, Sunday

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        days = params.get("weekend_days")
        if not isinstance(days, list) or not days:
            errors.append("weekend_days must be a non-empty list")
        elif not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
            errors.append("weekend_days must contain integers 0-6 (Monday=0)")
        return errors

    @classmethod
    def is_weekend(cls, day: date, group=None) -> bool:
        return day.weekday() in cls.resolve(group=group)["weekend_days"]
