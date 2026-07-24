"""Configurable on-call week anchor - which weekday/hour an on-call
period starts and ends on. Replaces the previously hardcoded Friday
21:00 -> Friday 07:00 window (app/utils/automation/oncall_automation.py,
app/utils/automation/advanced_shift_automation.py,
app/utils/automation/status.py)."""

from app.utils.automation.rules.base import AutomationRuleType


class OnCallAnchorRule(AutomationRuleType):
    """`weekday` (date.weekday(), Monday=0 ... Sunday=6): the day an
    on-call period starts on. `start_hour`/`end_hour`: the on-call
    period runs from `start_hour` on that weekday to `end_hour` one
    week later."""

    rule_type = "oncall_anchor"

    @classmethod
    def default_params(cls) -> dict:
        return {"weekday": 4, "start_hour": 21, "end_hour": 7}  # Friday

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        weekday = params.get("weekday")
        start_hour = params.get("start_hour")
        end_hour = params.get("end_hour")
        if (
            not isinstance(weekday, int)
            or isinstance(weekday, bool)
            or not (0 <= weekday <= 6)
        ):
            errors.append("weekday must be an integer 0-6 (Monday=0)")
        for label, hour in (("start_hour", start_hour), ("end_hour", end_hour)):
            if (
                not isinstance(hour, int)
                or isinstance(hour, bool)
                or not (0 <= hour <= 23)
            ):
                errors.append(f"{label} must be an integer 0-23")
        return errors
