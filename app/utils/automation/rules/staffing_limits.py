"""Configurable maximum headcount per ShiftType. No prior hardcoded
equivalent exists for this - AdvancedShiftAutomation only has the
1-person/2-person special-case branches (unrelated, not made
configurable here) and leave_keeps_minimum_headcount() (a floor-of-1
check scoped to leave creation, not per-shift-type). Enforced at
creation time by app/utils/helpers/common_helpers.py's can_add_shift()
- see check_shift_rule_violations().

Deliberately max-only, no minimum: coverage for the two role-governed
shift types (the "rotation"/"oncall" slots configured via
ShiftSlotsRule) is already structurally guaranteed by the generation
algorithm itself - rotation always has a fallback assignment
(assign_shift_slots_for_day's "rule 7"), oncall is filled by that
week's actual on-call holder whenever they belong to the shift scope
being planned. A separate, admin-configured minimum/mandatory layer on
top of that only produced false "unfilled" alerts when the two didn't
line up (e.g. a shift scope narrower than the on-call pool), without
adding any real guarantee the algorithm didn't already provide - see
[[project-automation-engine-rework]] for the production report that
led to removing it."""

from app.utils.automation.rules.base import AutomationRuleType


class StaffingLimitsRule(AutomationRuleType):
    """params: `{"<shift_type_id>": int|None}` - a JSON object keyed by
    ShiftType id (string keys, JSON requirement) to that type's maximum
    headcount for a single day. A ShiftType with no entry (or a null
    value) has no limit. Default is empty - nothing is limited until an
    admin configures it."""

    rule_type = "staffing_limits"

    @classmethod
    def default_params(cls) -> dict:
        return {}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        from app import db
        from app.models import ShiftType

        errors = []
        for key, max_value in params.items():
            try:
                shift_type_id = int(key)
            except (TypeError, ValueError):
                errors.append(f"{key!r} is not a valid ShiftType id")
                continue
            if db.session.get(ShiftType, shift_type_id) is None:
                errors.append(f"ShiftType {shift_type_id} does not exist")
                continue

            if max_value is not None and (
                not isinstance(max_value, int)
                or isinstance(max_value, bool)
                or max_value < 0
            ):
                errors.append(
                    f"max for ShiftType {shift_type_id} must be a "
                    "non-negative integer or null"
                )
        return errors

    @classmethod
    def get_max(cls, shift_type_id: int, group=None) -> int | None:
        params = cls.resolve(group=group)
        return params.get(str(shift_type_id))
