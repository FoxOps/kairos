"""
Tests for the configurable automation rule-type classes
(app/utils/automation/rules/): default_params() must match today's
pre-existing hardcoded behavior (zero regression when nothing is
configured), and resolve() must honor a Group override, falling back
to the organization default, then to default_params().
"""

import datetime

from app.models import AutomationRule
from app.utils.automation.rules import (
    RULE_TYPES,
    OnCallAnchorRule,
    OnCallSpacingRule,
    WeekendDefinitionRule,
)


class TestRegistry:
    def test_all_rule_types_registered_by_their_own_key(self):
        for key, rule_cls in RULE_TYPES.items():
            assert rule_cls.rule_type == key


class TestWeekendDefinitionRule:
    def test_default_matches_pre_existing_hardcoded_weekend(self, test_app):
        assert WeekendDefinitionRule.resolve() == {"weekend_days": [5, 6]}

    def test_group_override_falls_back_to_global_then_default(
        self, test_app, test_group
    ):
        assert WeekendDefinitionRule.resolve(group=test_group) == {
            "weekend_days": [5, 6]
        }

        AutomationRule.set("weekend_definition", {"weekend_days": [4, 5]})
        assert WeekendDefinitionRule.resolve(group=test_group) == {
            "weekend_days": [4, 5]
        }

        AutomationRule.set(
            "weekend_definition", {"weekend_days": [6]}, group=test_group
        )
        assert WeekendDefinitionRule.resolve(group=test_group) == {"weekend_days": [6]}
        assert WeekendDefinitionRule.resolve() == {"weekend_days": [4, 5]}

    def test_is_weekend_uses_resolved_days(self, test_app):
        saturday = datetime.date(2026, 7, 25)
        monday = datetime.date(2026, 7, 27)
        assert WeekendDefinitionRule.is_weekend(saturday) is True
        assert WeekendDefinitionRule.is_weekend(monday) is False

    def test_validate_params_rejects_non_list(self):
        assert WeekendDefinitionRule.validate_params({"weekend_days": "nope"})

    def test_validate_params_rejects_out_of_range_day(self):
        assert WeekendDefinitionRule.validate_params({"weekend_days": [7]})

    def test_validate_params_accepts_valid_days(self):
        assert WeekendDefinitionRule.validate_params({"weekend_days": [5, 6]}) == []


class TestOnCallSpacingRule:
    def test_default_matches_pre_existing_hardcoded_two_weeks(self, test_app):
        assert OnCallSpacingRule.resolve() == {"min_spacing_weeks": 2}

    def test_validate_params_rejects_zero(self):
        assert OnCallSpacingRule.validate_params({"min_spacing_weeks": 0})

    def test_validate_params_accepts_positive_int(self):
        assert OnCallSpacingRule.validate_params({"min_spacing_weeks": 3}) == []


class TestOnCallAnchorRule:
    def test_default_matches_pre_existing_hardcoded_friday_anchor(self, test_app):
        assert OnCallAnchorRule.resolve() == {
            "weekday": 4,
            "start_hour": 21,
            "end_hour": 7,
        }

    def test_validate_params_rejects_invalid_hour(self):
        assert OnCallAnchorRule.validate_params(
            {"weekday": 4, "start_hour": 24, "end_hour": 7}
        )

    def test_validate_params_accepts_valid_anchor(self):
        assert (
            OnCallAnchorRule.validate_params(
                {"weekday": 4, "start_hour": 21, "end_hour": 7}
            )
            == []
        )
