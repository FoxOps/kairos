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

    def test_resets_rotation_epoch_to_today(self, test_app):
        """Real production bug: with the epoch left at its year-2000
        fallback forever, a freshly saved rotation order's first user
        was essentially never the first one actually put on-call (an
        arbitrary offset unrelated to the order just configured).
        Saving must reset the epoch so the very next anchor date lands
        on offset 0 - i.e. rotation_order[0]."""
        from datetime import date

        from app.models import AutomationConfig

        AutomationAdminService.save_rotation_order([1, 2, 3])
        assert AutomationConfig.get_rotation_epoch() == date.today()

    def test_does_not_reset_epoch_when_order_content_is_unchanged(self, test_app):
        """Defect #4 (rotation.py's module docstring): repeatedly saving/
        generating with the *same* already-in-effect order must never
        re-shuffle an already-running rotation's phase - only an actual
        content change should reset the epoch."""
        from datetime import date

        from app.models import AutomationConfig

        AutomationAdminService.save_rotation_order([1, 2, 3])
        sentinel = date(2020, 5, 1)
        AutomationConfig.set_rotation_epoch(sentinel)

        AutomationAdminService.save_rotation_order([1, 2, 3])
        assert AutomationConfig.get_rotation_epoch() == sentinel

        # Sanity: a genuinely different order still resets it.
        AutomationAdminService.save_rotation_order([3, 2, 1])
        assert AutomationConfig.get_rotation_epoch() == date.today()


class TestGetRotationOrder:
    def test_returns_none_on_failure(self, test_app, monkeypatch):
        from app.models import AutomationConfig

        def _raise():
            raise RuntimeError("boom")

        monkeypatch.setattr(AutomationConfig, "get_rotation_order", _raise)

        assert AutomationAdminService.get_rotation_order() is None

    def test_returns_list_on_success(self, test_app):
        assert AutomationAdminService.get_rotation_order() == []
