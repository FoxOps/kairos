"""
Tests for AutomationRuleAdminService (app/services/automation_rule_admin_service.py):
one save_*() method per rule type, each validating via the rule
type's own validate_params() before persisting through AutomationRule.set(),
mirroring SettingsService's per-section setter pattern.
"""

from app.models import AutomationRule


class TestSaveShiftSlots:
    def test_valid_ids_persist(self, test_app, test_shift_type):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_shift_slots(
            test_shift_type.id, test_shift_type.id, test_shift_type.id
        )
        assert error is None
        assert AutomationRule.resolve_params("shift_slots") == {
            "oncall_shift_type_id": test_shift_type.id,
            "rotation_shift_type_id": test_shift_type.id,
            "default_shift_type_id": test_shift_type.id,
        }

    def test_unknown_id_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_shift_slots(999999, 999999, 999999)
        assert error is not None
        assert AutomationRule.resolve_params("shift_slots") is None


class TestSaveWeekendDefinition:
    def test_valid_days_persist(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_weekend_definition([5, 6])
        assert error is None
        assert AutomationRule.resolve_params("weekend_definition") == {
            "weekend_days": [5, 6]
        }

    def test_empty_days_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_weekend_definition([])
        assert error is not None


class TestSaveOnCallSpacing:
    def test_valid_weeks_persist(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_spacing(3)
        assert error is None
        assert AutomationRule.resolve_params("oncall_spacing") == {
            "min_spacing_weeks": 3
        }

    def test_zero_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_spacing(0)
        assert error is not None


class TestSaveOnCallAnchor:
    def test_valid_anchor_persists(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_anchor(0, 20, 8)
        assert error is None
        assert AutomationRule.resolve_params("oncall_anchor") == {
            "weekday": 0,
            "start_hour": 20,
            "end_hour": 8,
        }

    def test_invalid_hour_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_anchor(4, 25, 7)
        assert error is not None


class TestSaveStaffingLimits:
    def test_valid_limits_persist(self, test_app, test_shift_type):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_staffing_limits(
            {test_shift_type.id: (1, 3)}
        )
        assert error is None
        assert AutomationRule.resolve_params("staffing_limits") == {
            str(test_shift_type.id): {"min": 1, "max": 3}
        }

    def test_min_greater_than_max_rejected(self, test_app, test_shift_type):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_staffing_limits(
            {test_shift_type.id: (5, 2)}
        )
        assert error is not None

    def test_empty_values_mean_no_limit(self, test_app, test_shift_type):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_staffing_limits(
            {test_shift_type.id: (None, None)}
        )
        assert error is None
        assert AutomationRule.resolve_params("staffing_limits") == {
            str(test_shift_type.id): {"min": None, "max": None}
        }


class TestSaveMandatoryShift:
    def test_valid_ids_persist(self, test_app, test_shift_type):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_mandatory_shift([test_shift_type.id])
        assert error is None
        assert AutomationRule.resolve_params("mandatory_shift") == {
            "shift_type_ids": [test_shift_type.id]
        }

    def test_unknown_id_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_mandatory_shift([999999])
        assert error is not None

    def test_empty_list_persists_as_nothing_mandatory(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_mandatory_shift([])
        assert error is None
        assert AutomationRule.resolve_params("mandatory_shift") == {
            "shift_type_ids": []
        }


class TestSaveRestAfterOnCall:
    def test_valid_hours_persist(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_rest_after_oncall(12)
        assert error is None
        assert AutomationRule.resolve_params("rest_after_oncall") == {
            "min_rest_hours": 12
        }

    def test_negative_rejected(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_rest_after_oncall(-1)
        assert error is not None


class TestSaveOnCallShiftOverlap:
    def test_saves_true(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_shift_overlap(True)
        assert error is None
        assert AutomationRule.resolve_params("oncall_shift_overlap") == {"block": True}

    def test_saves_false(self, test_app):
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        error = AutomationRuleAdminService.save_oncall_shift_overlap(False)
        assert error is None
        assert AutomationRule.resolve_params("oncall_shift_overlap") == {"block": False}


class TestAuditTrail:
    def test_save_writes_audit_log_entry(self, test_app):
        from app.models import AuditLog
        from app.services.automation_rule_admin_service import (
            AutomationRuleAdminService,
        )

        AutomationRuleAdminService.save_oncall_spacing(3)

        entry = AuditLog.query.filter_by(action="automation_rule.update").first()
        assert entry is not None
        assert "oncall_spacing" in entry.details
