"""Configurable "block a shift and an on-call overlapping in time for
the same user" guard. No prior equivalent exists - can_add_shift()/
can_add_oncall() (app/utils/helpers/common_helpers.py) never checked
the other model at all before this. Defaults to blocking (True),
unlike every other new rule type here, which default to "off"/
unconfigured: an unblocked overlap is a real data-integrity problem
(a user double-booked on the same instant), not a preference an admin
would reasonably want off by default."""

from app.utils.automation.rules.base import AutomationRuleType


class OnCallShiftOverlapRule(AutomationRuleType):
    """`block`: whether creating a shift/on-call that overlaps the
    same user's existing on-call/shift is rejected."""

    rule_type = "oncall_shift_overlap"

    @classmethod
    def default_params(cls) -> dict:
        return {"block": True}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        if not isinstance(params.get("block"), bool):
            errors.append("block must be a boolean")
        return errors
