"""
AutomationRule model for Kairos.

Backs the configurable automation rules engine: an extensible,
plugin-style store for the business rules that drive shift/on-call
generation (see app/utils/automation/rules/ for the rule-type classes
that interpret `params`). Each row is one rule type's configuration,
either the organization-wide default (`group_id` is None) or a
specific Group's override.
"""

import json

from app import db
from app.models.base import BaseModel


class AutomationRule(BaseModel):
    """
    One configured automation rule.

    Attributes:
        group_id: Group this override applies to, or None for the
            organization-wide default. Deliberately NOT enforced by a
            DB-level unique constraint on (group_id, rule_type): SQL
            treats two NULL group_id values as distinct, so such a
            constraint would not actually prevent duplicate global
            rows - dedup is enforced by set() instead (query-then-
            update, same pattern as AutomationConfig.set_config).
        rule_type: Key identifying which rule-type class in
            app/utils/automation/rules/ interprets `params` (e.g.
            "weekend_definition", "oncall_spacing").
        params: JSON-encoded dict, shape defined by the rule type.
        enabled: Per-row on/off switch - a disabled row is treated as
            "not configured" by resolve_params(), same as if it didn't
            exist, so disabling a Group override falls back to the
            organization default rather than to some other state.
    """

    __tablename__ = "automation_rules"

    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=True, index=True
    )
    rule_type = db.Column(db.String(50), nullable=False, index=True)
    params = db.Column(db.Text, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    def get_params(self) -> dict:
        try:
            return json.loads(self.params)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_params(self, params: dict) -> None:
        self.params = json.dumps(params)

    @classmethod
    def resolve_params(cls, rule_type: str, group=None) -> dict | None:
        """Effective configured params for this rule type: the Group's
        own override if one exists and is enabled, else the
        organization-wide default if one exists and is enabled, else
        None (callers fall back to the rule type's own
        default_params(), see app/utils/automation/rules/base.py)."""
        if group is not None:
            row = cls.query.filter_by(
                rule_type=rule_type, group_id=group.id, enabled=True
            ).first()
            if row:
                return row.get_params()
        row = cls.query.filter_by(
            rule_type=rule_type, group_id=None, enabled=True
        ).first()
        return row.get_params() if row else None

    @classmethod
    def set(
        cls, rule_type: str, params: dict, group=None, enabled: bool = True
    ) -> "AutomationRule":
        """Create or update the row for (rule_type, group) - never
        duplicates, see the group_id docstring note above for why this
        can't be left to a DB constraint."""
        group_id = group.id if group is not None else None
        row = cls.query.filter_by(rule_type=rule_type, group_id=group_id).first()
        if row:
            row.set_params(params)
            row.enabled = enabled
        else:
            row = cls(rule_type=rule_type, group_id=group_id, enabled=enabled)
            row.set_params(params)
            db.session.add(row)
        db.session.commit()
        return row

    def __repr__(self) -> str:
        return f"<AutomationRule {self.rule_type} group_id={self.group_id}>"
