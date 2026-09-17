"""
Tests for the 3 remaining automation rule types with no prior hardcoded
equivalent (see plan): staffing_limits, rest_after_oncall,
oncall_shift_overlap. Unlike the 4 "transposed" rule types, none of
these existed in any form before - default_params() for each is chosen
so nothing is enforced until an admin actually configures it (zero
regression on introduction).

mandatory_shift (a 4th rule type from that same original plan) and the
`min` half of staffing_limits were later removed entirely: coverage for
the role-governed shift types (rotation/oncall, see ShiftSlotsRule) is
already structurally guaranteed by the generation algorithm itself, so
a separate admin-configured minimum/mandatory layer only produced false
"unfilled" alerts when the two didn't line up, without adding any real
guarantee - see [[project-automation-engine-rework]]."""

from app.models import AutomationRule
from app.utils.automation.rules import (
    OnCallShiftOverlapRule,
    RestAfterOnCallRule,
    StaffingLimitsRule,
)


class TestStaffingLimitsRule:
    def test_default_has_no_limits(self, test_app):
        assert StaffingLimitsRule.resolve() == {}

    def test_get_max_unconfigured_type_returns_none(self, test_app, test_shift_type):
        assert StaffingLimitsRule.get_max(test_shift_type.id) is None

    def test_get_max_returns_configured_value(self, test_app, test_shift_type):
        AutomationRule.set("staffing_limits", {str(test_shift_type.id): 3})
        assert StaffingLimitsRule.get_max(test_shift_type.id) == 3

    def test_get_max_group_override_falls_back_to_global(
        self, test_app, test_group, test_shift_type
    ):
        AutomationRule.set("staffing_limits", {str(test_shift_type.id): 3})
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): 5},
            group=test_group,
        )
        assert StaffingLimitsRule.get_max(test_shift_type.id) == 3
        assert StaffingLimitsRule.get_max(test_shift_type.id, group=test_group) == 5

    def test_validate_params_rejects_unknown_shift_type_key(self, test_app):
        errors = StaffingLimitsRule.validate_params({"999999": 1})
        assert errors

    def test_validate_params_accepts_valid_max(self, test_app, test_shift_type):
        errors = StaffingLimitsRule.validate_params({str(test_shift_type.id): 3})
        assert errors == []

    def test_validate_params_accepts_empty(self):
        assert StaffingLimitsRule.validate_params({}) == []

    def test_validate_params_rejects_non_integer_key(self, test_app):
        errors = StaffingLimitsRule.validate_params({"not-an-id": 1})
        assert errors
        assert "not-an-id" in errors[0]

    def test_validate_params_rejects_negative_max(self, test_app, test_shift_type):
        errors = StaffingLimitsRule.validate_params({str(test_shift_type.id): -1})
        assert errors
        assert "non-negative integer" in errors[0]

    def test_validate_params_rejects_non_integer_max(self, test_app, test_shift_type):
        errors = StaffingLimitsRule.validate_params({str(test_shift_type.id): "many"})
        assert errors
        assert "non-negative integer" in errors[0]

    def test_validate_params_accepts_none_value(self, test_app, test_shift_type):
        errors = StaffingLimitsRule.validate_params({str(test_shift_type.id): None})
        assert errors == []

    def test_get_max_ignores_stale_nested_min_max_shape(
        self, test_app, test_shift_type
    ):
        """Real bug found in production: a row saved under this rule's
        pre-1.1.1 shape (`{"min": .., "max": ..}` per ShiftType, before
        it became max-only) crashed generation with `'>=' not
        supported between instances of 'int' and 'dict'` - resolve()
        is a raw passthrough of whatever is already in the database,
        with no shape check. get_max() must treat it as unconfigured
        rather than propagate the dict to a caller that assumes int."""
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": 2, "max": 5}},
        )
        assert StaffingLimitsRule.get_max(test_shift_type.id) is None

    def test_coerce_max_passes_through_valid_values(self):
        assert StaffingLimitsRule.coerce_max(3) == 3
        assert StaffingLimitsRule.coerce_max(0) == 0
        assert StaffingLimitsRule.coerce_max(None) is None

    def test_coerce_max_rejects_non_int_values(self):
        assert StaffingLimitsRule.coerce_max({"min": 2, "max": 5}) is None
        assert StaffingLimitsRule.coerce_max("many") is None
        assert StaffingLimitsRule.coerce_max(True) is None

    def test_resolve_rules_for_groups_does_not_crash_on_stale_shape(
        self, test_app, test_shift_type
    ):
        """End-to-end regression for the same production crash, at the
        actual boundary "Générer"/"Prévisualiser (Dry Run)" call
        (app/utils/automation/planner/rule_resolution.py) - a stale
        nested-shape row must not blow up plan resolution."""
        from app.utils.automation.planner.rule_resolution import (
            resolve_rules_for_groups,
        )

        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": 2, "max": 5}},
        )
        resolved = resolve_rules_for_groups([None])
        assert resolved[None].staffing_limits[test_shift_type.id] is None


class TestRestAfterOnCallRule:
    def test_default_requires_no_rest(self, test_app):
        assert RestAfterOnCallRule.resolve() == {"min_rest_hours": 0}

    def test_validate_params_rejects_negative(self):
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": -1})

    def test_validate_params_accepts_zero_and_positive(self):
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": 0}) == []
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": 12}) == []


class TestOnCallShiftOverlapRule:
    def test_default_allows_overlap(self, test_app):
        # On-call duty coexists with normal shifts by default - a
        # week-long on-call naturally overlaps its holder's daytime
        # shift hours, which is expected, not a conflict. An org that
        # wants the old stricter behavior can opt in per group.
        assert OnCallShiftOverlapRule.resolve() == {"block": False}

    def test_validate_params_rejects_non_bool(self):
        assert OnCallShiftOverlapRule.validate_params({"block": "yes"})

    def test_validate_params_accepts_bool(self):
        assert OnCallShiftOverlapRule.validate_params({"block": False}) == []
