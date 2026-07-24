"""Configurable "this ShiftType must never be left unfilled on a
business day" flag. No prior equivalent exists - the pre-existing
policy (ROADMAP.md) is "leave unfilled + notify admins, never block" -
this rule doesn't change that philosophy, it only escalates the
notification for the specific ShiftType(s) an admin flags as
mandatory. See AdvancedShiftAutomation.generate_daily_shifts()'s
mandatory-coverage check for the enforcement point."""

from app.utils.automation.rules.base import AutomationRuleType


class MandatoryShiftRule(AutomationRuleType):
    """`shift_type_ids`: list of ShiftType ids that must have at least
    one person assigned whenever the day has any available user at
    all. Default is empty - nothing is mandatory until configured."""

    rule_type = "mandatory_shift"

    @classmethod
    def default_params(cls) -> dict:
        return {"shift_type_ids": []}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        from app import db
        from app.models import ShiftType

        errors = []
        ids = params.get("shift_type_ids")
        if not isinstance(ids, list):
            errors.append("shift_type_ids must be a list")
            return errors
        for shift_type_id in ids:
            if (
                not isinstance(shift_type_id, int)
                or isinstance(shift_type_id, bool)
                or db.session.get(ShiftType, shift_type_id) is None
            ):
                errors.append(f"{shift_type_id!r} is not a valid ShiftType id")
        return errors

    @classmethod
    def is_mandatory(cls, shift_type_id: int, group=None) -> bool:
        return shift_type_id in cls.resolve(group=group)["shift_type_ids"]
