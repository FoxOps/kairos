"""Tests for app/utils/automation/rules/base.py::AutomationRuleType's own
base implementation - every real rule type overrides validate_params(),
so the base "accepts anything" implementation is only reachable directly."""

from app.utils.automation.rules.base import AutomationRuleType


class TestAutomationRuleTypeBase:
    def test_validate_params_base_implementation_accepts_anything(self):
        assert AutomationRuleType.validate_params({"anything": "goes"}) == []
