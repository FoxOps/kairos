"""Configurable minimum rest period between a user's on-call ending and
a shift of theirs starting. No prior equivalent exists in this
codebase. Enforced at creation time by
app/utils/helpers/common_helpers.py's can_add_shift() - see
check_shift_rule_violations()."""

from app.utils.automation.rules.base import AutomationRuleType


class RestAfterOnCallRule(AutomationRuleType):
    """`min_rest_hours`: minimum number of hours required between a
    user's on-call ending and a shift of theirs starting. Default is
    0 (no requirement) - matches the pre-existing absence of any such
    check."""

    rule_type = "rest_after_oncall"

    @classmethod
    def default_params(cls) -> dict:
        return {"min_rest_hours": 0}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        hours = params.get("min_rest_hours")
        if not isinstance(hours, int) or isinstance(hours, bool) or hours < 0:
            errors.append("min_rest_hours must be a non-negative integer")
        return errors
