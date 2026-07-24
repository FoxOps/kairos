"""Configurable shift slot roles - which ShiftType plays each of the 3
roles AdvancedShiftAutomation assigns (see its class docstring, rules
1-3): the on-call slot, the rotation slot (previous week's on-call
person), and the default slot. References existing ShiftType rows
(reusing the /admin/shift-types admin page) instead of duplicating
hour inputs - see AdvancedShiftAutomation.get_shift_type_for_slot()
for the resolution this feeds, which also fixes a pre-existing bug
where get_shift_type_by_hours() matched by hours instead of id."""

from app.utils.automation.rules.base import AutomationRuleType

ONCALL_KEY = "oncall_shift_type_id"
ROTATION_KEY = "rotation_shift_type_id"
DEFAULT_KEY = "default_shift_type_id"

# Legacy hardcoded hour pairs - used only to fetch-or-create the
# fallback ShiftType rows when nothing is configured yet (see
# default_params() below). Not exposed as this rule type's params
# shape; params always store ShiftType ids, never raw hours.
_LEGACY_HOURS = {
    ONCALL_KEY: (13, 21),
    ROTATION_KEY: (7, 15),
    DEFAULT_KEY: (9, 17),
}


class ShiftSlotsRule(AutomationRuleType):
    """`oncall_shift_type_id`/`rotation_shift_type_id`/
    `default_shift_type_id`: ShiftType ids for the 3 roles.

    Unlike every other rule type, default_params() can't return a
    static dict - ShiftType ids vary per database. When unconfigured,
    it falls back to the historical hours-based lookup (fetch-or-
    create the legacy 07-15/09-17/13-21 ShiftType rows), matching the
    pre-existing hardcoded behavior exactly.
    """

    rule_type = "shift_slots"

    @classmethod
    def default_params(cls) -> dict:
        from app.utils.automation.advanced_shift_automation import (
            AdvancedShiftAutomation,
        )

        return {
            key: AdvancedShiftAutomation.get_shift_type_by_hours(*hours).id
            for key, hours in _LEGACY_HOURS.items()
        }

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        from app import db
        from app.models import ShiftType

        errors = []
        for key in (ONCALL_KEY, ROTATION_KEY, DEFAULT_KEY):
            value = params.get(key)
            if not isinstance(value, int) or db.session.get(ShiftType, value) is None:
                errors.append(f"{key} must reference an existing ShiftType id")
        return errors

    @classmethod
    def references_shift_type(cls, shift_type_id: int) -> bool:
        """True if any configured shift_slots row (organization
        default or a Group override) references this ShiftType id in
        any of its 3 role keys - used by ShiftTypeService.delete() to
        block deleting a ShiftType a rule still depends on. params is
        opaque JSON (no real DB foreign key, see AutomationRule's
        group_id docstring for why), so this has to parse rows rather
        than rely on a constraint."""
        from app.models import AutomationRule

        for row in AutomationRule.query.filter_by(rule_type=cls.rule_type).all():
            params = row.get_params()
            if shift_type_id in (
                params.get(ONCALL_KEY),
                params.get(ROTATION_KEY),
                params.get(DEFAULT_KEY),
            ):
                return True
        return False
