"""
Tests for admin_automation_routes._classify_automation_message() -
the leading-emoji-to-flash-category mapping (see
app/routes/admin_automation_routes.py's module docstring comment for
why messages generated in app/utils/automation/ carry an emoji).
"""

from app.routes.admin_automation_routes import _classify_automation_message


class TestClassifyAutomationMessage:
    def test_mandatory_gap_is_always_danger(self):
        """MandatoryShiftRule's elevated message must read as "danger"
        even on the shift-messages path, whose default_category is
        "info" - otherwise it would look identical to an ordinary
        success/info message, defeating the point of the escalation."""
        category, _stripped = _classify_automation_message(
            "🚨 Créneau obligatoire non pourvu pour le 01/01/2026 : Astreinte.",
            default_category="info",
        )
        assert category == "danger"

    def test_mandatory_gap_strips_the_emoji(self):
        _category, stripped = _classify_automation_message(
            "🚨 Créneau obligatoire non pourvu pour le 01/01/2026 : Astreinte.",
            default_category="info",
        )
        assert not stripped.startswith("🚨")
        assert "Créneau obligatoire" in stripped

    def test_success_still_classified_correctly(self):
        category, _stripped = _classify_automation_message(
            "✅ 3 shifts générés pour le 01/01/2026", default_category="info"
        )
        assert category == "success"

    def test_warning_still_classified_correctly(self):
        category, _stripped = _classify_automation_message(
            "⚠️ Aucun shift généré pour le 01/01/2026", default_category="info"
        )
        assert category == "warning"
