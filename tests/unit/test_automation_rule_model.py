"""
Tests for the AutomationRule model (app/models/automation_rule.py):
JSON params round-trip, and the Group-override-with-global-fallback
resolution used by the configurable automation rules engine.
"""

from app.models import AutomationRule


class TestParams:
    def test_get_params_round_trip(self, test_app):
        rule = AutomationRule(rule_type="weekend_definition")
        rule.set_params({"weekend_days": [5, 6]})
        assert rule.get_params() == {"weekend_days": [5, 6]}

    def test_get_params_invalid_json_returns_empty_dict(self, test_app):
        rule = AutomationRule(rule_type="weekend_definition")
        rule.params = "not json"
        assert rule.get_params() == {}


class TestSet:
    def test_set_creates_global_row_when_none_exists(self, test_app):
        AutomationRule.set("weekend_definition", {"weekend_days": [5, 6]})
        assert AutomationRule.resolve_params("weekend_definition") == {
            "weekend_days": [5, 6]
        }

    def test_set_updates_existing_global_row_instead_of_duplicating(self, test_app):
        AutomationRule.set("weekend_definition", {"weekend_days": [5, 6]})
        AutomationRule.set("weekend_definition", {"weekend_days": [6]})

        assert (
            AutomationRule.query.filter_by(
                rule_type="weekend_definition", group_id=None
            ).count()
            == 1
        )
        assert AutomationRule.resolve_params("weekend_definition") == {
            "weekend_days": [6]
        }

    def test_set_scoped_to_group_does_not_affect_global(self, test_app, test_group):
        AutomationRule.set("weekend_definition", {"weekend_days": [5, 6]})
        AutomationRule.set(
            "weekend_definition", {"weekend_days": [6]}, group=test_group
        )

        assert AutomationRule.resolve_params("weekend_definition") == {
            "weekend_days": [5, 6]
        }
        assert AutomationRule.resolve_params(
            "weekend_definition", group=test_group
        ) == {"weekend_days": [6]}


class TestResolveParams:
    def test_resolve_params_returns_none_when_nothing_configured(self, test_app):
        assert AutomationRule.resolve_params("weekend_definition") is None

    def test_resolve_params_group_falls_back_to_global(self, test_app, test_group):
        AutomationRule.set("weekend_definition", {"weekend_days": [5, 6]})
        assert AutomationRule.resolve_params(
            "weekend_definition", group=test_group
        ) == {"weekend_days": [5, 6]}

    def test_resolve_params_ignores_disabled_rows(self, test_app):
        AutomationRule.set(
            "weekend_definition", {"weekend_days": [5, 6]}, enabled=False
        )
        assert AutomationRule.resolve_params("weekend_definition") is None


class TestHasGroupOverride:
    def test_false_when_no_row_at_all(self, test_app, test_group):
        assert (
            AutomationRule.has_group_override("weekend_definition", test_group) is False
        )

    def test_false_when_only_a_global_row_exists(self, test_app, test_group):
        AutomationRule.set("weekend_definition", {"weekend_days": [5, 6]})
        assert (
            AutomationRule.has_group_override("weekend_definition", test_group) is False
        )

    def test_true_when_an_enabled_group_row_exists(self, test_app, test_group):
        AutomationRule.set(
            "weekend_definition", {"weekend_days": [6]}, group=test_group
        )
        assert (
            AutomationRule.has_group_override("weekend_definition", test_group) is True
        )

    def test_false_when_the_group_row_is_disabled(self, test_app, test_group):
        AutomationRule.set(
            "weekend_definition",
            {"weekend_days": [6]},
            group=test_group,
            enabled=False,
        )
        assert (
            AutomationRule.has_group_override("weekend_definition", test_group) is False
        )

    def test_only_matches_the_given_group(self, test_app, test_group):
        from app import db
        from app.models import Group

        other_group = Group(name="Other")
        db.session.add(other_group)
        db.session.commit()
        AutomationRule.set(
            "weekend_definition", {"weekend_days": [6]}, group=other_group
        )

        assert (
            AutomationRule.has_group_override("weekend_definition", test_group) is False
        )
