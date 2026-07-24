"""Configurable minimum/maximum headcount per ShiftType. No prior
hardcoded equivalent exists for this - AdvancedShiftAutomation only
has the 1-person/2-person special-case branches (unrelated, not made
configurable here) and leave_keeps_minimum_headcount() (a floor-of-1
check scoped to leave creation, not per-shift-type). Enforced at
creation time by app/utils/helpers/common_helpers.py's can_add_shift()
- see check_shift_rule_violations()."""

from app.utils.automation.rules.base import AutomationRuleType


class StaffingLimitsRule(AutomationRuleType):
    """params: `{"<shift_type_id>": {"min": int|None, "max": int|None}}`
    - a JSON object keyed by ShiftType id (string keys, JSON
    requirement) to that type's headcount bounds for a single day.
    A ShiftType with no entry has no limit either way. Default is
    empty - nothing is limited until an admin configures it."""

    rule_type = "staffing_limits"

    @classmethod
    def default_params(cls) -> dict:
        return {}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        from app import db
        from app.models import ShiftType

        errors = []
        for key, limits in params.items():
            try:
                shift_type_id = int(key)
            except (TypeError, ValueError):
                errors.append(f"{key!r} is not a valid ShiftType id")
                continue
            if db.session.get(ShiftType, shift_type_id) is None:
                errors.append(f"ShiftType {shift_type_id} does not exist")
                continue

            if not isinstance(limits, dict):
                errors.append(f"limits for ShiftType {shift_type_id} must be an object")
                continue
            min_value = limits.get("min")
            max_value = limits.get("max")
            for label, value in (("min", min_value), ("max", max_value)):
                if value is not None and (
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                ):
                    errors.append(
                        f"{label} for ShiftType {shift_type_id} must be a "
                        "non-negative integer or null"
                    )
            if (
                min_value is not None
                and max_value is not None
                and isinstance(min_value, int)
                and isinstance(max_value, int)
                and min_value > max_value
            ):
                errors.append(f"min must not exceed max for ShiftType {shift_type_id}")
        return errors

    @classmethod
    def get_limits(cls, shift_type_id: int, group=None) -> dict:
        params = cls.resolve(group=group)
        limits = params.get(str(shift_type_id), {})
        return {"min": limits.get("min"), "max": limits.get("max")}
