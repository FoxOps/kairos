"""Tests for app/services/automation_admin_service.py::AutomationAdminService's
own error-handling branches (save_rotation_order/get_rotation_order),
not covered by the per-group tests in test_automation_admin_service_per_group.py."""

from app.services import AutomationAdminService


class TestSaveRotationOrder:
    def test_returns_error_message_on_failure(self, test_app, monkeypatch):
        """AutomationConfig.set_rotation_order() never actually fails on
        valid input - this exercises the route's own error branch
        directly via monkeypatch, same reasoning as this project's other
        structurally-dead-except-via-mock tests."""
        from app.models import AutomationConfig

        def _raise(rotation_order):
            raise RuntimeError("boom")

        monkeypatch.setattr(AutomationConfig, "set_rotation_order", _raise)

        error = AutomationAdminService.save_rotation_order([1, 2, 3])
        assert error == "boom"

    def test_returns_none_on_success(self, test_app):
        error = AutomationAdminService.save_rotation_order([])
        assert error is None


class TestGetRotationOrder:
    def test_returns_none_on_failure(self, test_app, monkeypatch):
        from app.models import AutomationConfig

        def _raise():
            raise RuntimeError("boom")

        monkeypatch.setattr(AutomationConfig, "get_rotation_order", _raise)

        assert AutomationAdminService.get_rotation_order() is None

    def test_returns_list_on_success(self, test_app):
        assert AutomationAdminService.get_rotation_order() == []
