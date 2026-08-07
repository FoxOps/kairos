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
        built-in default_params(). Cached on flask.g for the lifetime
        of the request, keyed by (rule_type, group_id) - same
        pattern/rationale as SettingsService.get_default_timezone():
        shift/on-call generation calls resolve() once per user/per day
        (or more) for the same (rule_type, group) inside a single
        generation run - without the cache, that's a real N+1 (one
        AutomationRule query per iteration) instead of one query per
        distinct rule/group combination for the whole request. Safe to
        cache: a rule's configured value cannot change mid-request (the
        one place it's saved, admin_automation_rules_routes.py, always
        redirects after saving - a fresh request, fresh flask.g)."""
        from flask import g, has_request_context

        if not has_request_context():
            params = AutomationRule.resolve_params(cls.rule_type, group=group)
            return params if params is not None else cls.default_params()

        if not hasattr(g, "_resolved_automation_rules"):
            g._resolved_automation_rules = {}
        cache_key = (cls.rule_type, group.id if group is not None else None)
        if cache_key not in g._resolved_automation_rules:
            params = AutomationRule.resolve_params(cls.rule_type, group=group)
            g._resolved_automation_rules[cache_key] = (
                params if params is not None else cls.default_params()
            )
        return g._resolved_automation_rules[cache_key]
