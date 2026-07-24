"""
Tests for the 4 automation rule types with no prior hardcoded
equivalent (see plan): staffing_limits, mandatory_shift,
rest_after_oncall, oncall_shift_overlap. Unlike the 4 "transposed"
rule types, none of these existed in any form before - default_params()
for each is chosen so nothing is enforced until an admin actually
configures it (zero regression on introduction).
"""

from app.models import AutomationRule
from app.utils.automation.rules import (
    MandatoryShiftRule,
    OnCallShiftOverlapRule,
    RestAfterOnCallRule,
    StaffingLimitsRule,
)


class TestStaffingLimitsRule:
    def test_default_has_no_limits(self, test_app):
        assert StaffingLimitsRule.resolve() == {}

    def test_get_limits_unconfigured_type_returns_no_limits(
        self, test_app, test_shift_type
    ):
        assert StaffingLimitsRule.get_limits(test_shift_type.id) == {
            "min": None,
            "max": None,
        }

    def test_get_limits_returns_configured_values(self, test_app, test_shift_type):
        AutomationRule.set(
            "staffing_limits", {str(test_shift_type.id): {"min": 1, "max": 3}}
        )
        assert StaffingLimitsRule.get_limits(test_shift_type.id) == {
            "min": 1,
            "max": 3,
        }

    def test_get_limits_group_override_falls_back_to_global(
        self, test_app, test_group, test_shift_type
    ):
        AutomationRule.set(
            "staffing_limits", {str(test_shift_type.id): {"min": 1, "max": 3}}
        )
        AutomationRule.set(
            "staffing_limits",
            {str(test_shift_type.id): {"min": 2, "max": 5}},
            group=test_group,
        )
        assert StaffingLimitsRule.get_limits(test_shift_type.id) == {
            "min": 1,
            "max": 3,
        }
        assert StaffingLimitsRule.get_limits(test_shift_type.id, group=test_group) == {
            "min": 2,
            "max": 5,
        }

    def test_validate_params_rejects_unknown_shift_type_key(self, test_app):
        errors = StaffingLimitsRule.validate_params({"999999": {"min": 1}})
        assert errors

    def test_validate_params_rejects_min_greater_than_max(
        self, test_app, test_shift_type
    ):
        errors = StaffingLimitsRule.validate_params(
            {str(test_shift_type.id): {"min": 5, "max": 2}}
        )
        assert errors

    def test_validate_params_accepts_valid_limits(self, test_app, test_shift_type):
        errors = StaffingLimitsRule.validate_params(
            {str(test_shift_type.id): {"min": 1, "max": 3}}
        )
        assert errors == []

    def test_validate_params_accepts_empty(self):
        assert StaffingLimitsRule.validate_params({}) == []


class TestMandatoryShiftRule:
    def test_default_has_nothing_mandatory(self, test_app):
        assert MandatoryShiftRule.resolve() == {"shift_type_ids": []}

    def test_is_mandatory_false_by_default(self, test_app, test_shift_type):
        assert MandatoryShiftRule.is_mandatory(test_shift_type.id) is False

    def test_is_mandatory_true_once_configured(self, test_app, test_shift_type):
        AutomationRule.set("mandatory_shift", {"shift_type_ids": [test_shift_type.id]})
        assert MandatoryShiftRule.is_mandatory(test_shift_type.id) is True

    def test_validate_params_rejects_unknown_shift_type_id(self, test_app):
        assert MandatoryShiftRule.validate_params({"shift_type_ids": [999999]})

    def test_validate_params_accepts_known_ids(self, test_app, test_shift_type):
        assert (
            MandatoryShiftRule.validate_params({"shift_type_ids": [test_shift_type.id]})
            == []
        )


class TestRestAfterOnCallRule:
    def test_default_requires_no_rest(self, test_app):
        assert RestAfterOnCallRule.resolve() == {"min_rest_hours": 0}

    def test_validate_params_rejects_negative(self):
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": -1})

    def test_validate_params_accepts_zero_and_positive(self):
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": 0}) == []
        assert RestAfterOnCallRule.validate_params({"min_rest_hours": 12}) == []


class TestOnCallShiftOverlapRule:
    def test_default_blocks_overlap(self, test_app):
        # Safe default: block overlap unless an admin explicitly opts out -
        # unlike the other 3 new rule types, "off" would silently allow a
        # data-integrity problem (a user double-booked on the same instant).
        assert OnCallShiftOverlapRule.resolve() == {"block": True}

    def test_validate_params_rejects_non_bool(self):
        assert OnCallShiftOverlapRule.validate_params({"block": "yes"})

    def test_validate_params_accepts_bool(self):
        assert OnCallShiftOverlapRule.validate_params({"block": False}) == []
