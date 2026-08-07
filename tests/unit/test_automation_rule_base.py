"""Tests for app/utils/automation/rules/base.py::AutomationRuleType's own
base implementation - every real rule type overrides validate_params(),
so the base "accepts anything" implementation is only reachable directly."""

from app.models import AutomationRule
from app.utils.automation.rules.base import AutomationRuleType
from app.utils.automation.rules.weekend_definition import WeekendDefinitionRule


class TestAutomationRuleTypeBase:
    def test_validate_params_base_implementation_accepts_anything(self):
        assert AutomationRuleType.validate_params({"anything": "goes"}) == []


class TestAutomationRuleTypeResolveCache:
    """resolve() caches its result on flask.g per (rule_type, group_id)
    for the request - regression tests for the two things that must stay
    true for that to be safe: a fresh AutomationRule.set() within the
    same request must invalidate its own cache entry, and distinct
    (rule_type, group_id) keys must never collide."""

    def test_set_within_same_request_invalidates_the_cache(self, test_app):
        with test_app.test_request_context("/"):
            assert WeekendDefinitionRule.resolve()["weekend_days"] == [5, 6]
            AutomationRule.set("weekend_definition", {"weekend_days": [4, 5, 6]})
            assert WeekendDefinitionRule.resolve()["weekend_days"] == [4, 5, 6]

    def test_org_default_and_group_override_use_distinct_cache_keys(
        self, test_app, test_group
    ):
        with test_app.test_request_context("/"):
            AutomationRule.set("weekend_definition", {"weekend_days": [6]})
            AutomationRule.set(
                "weekend_definition", {"weekend_days": [0, 6]}, group=test_group
            )
            assert WeekendDefinitionRule.resolve()["weekend_days"] == [6]
            assert WeekendDefinitionRule.resolve(group=test_group)["weekend_days"] == [
                0,
                6,
            ]
