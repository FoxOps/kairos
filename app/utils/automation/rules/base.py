"""
Base class for configurable automation rule types - see
app/utils/automation/rules/__init__.py for the registry these plug
into.
"""

from app.models import AutomationRule


class AutomationRuleType:
    """One configurable rule type.

    Subclasses declare `rule_type` (the key stored in
    AutomationRule.rule_type) and `default_params()` (the value used
    when nothing is configured - must match this rule's pre-existing
    hardcoded behavior, so introducing the rule engine is behavior-
    neutral until an admin actually configures something).
    """

    rule_type: str

    @classmethod
    def default_params(cls) -> dict:
        raise NotImplementedError

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        """Human-readable validation errors for the admin form, empty
        list if params are valid. Base implementation accepts
        anything - subclasses override to check their own shape."""
        return []

    @classmethod
    def resolve(cls, group=None) -> dict:
        """Effective params for this rule type: a Group override if
        one is configured and enabled, else the organization-wide
        default if configured and enabled, else this rule type's
        built-in default_params()."""
        params = AutomationRule.resolve_params(cls.rule_type, group=group)
        return params if params is not None else cls.default_params()
