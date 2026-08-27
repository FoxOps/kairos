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

    def test_resets_epoch_even_when_order_content_is_unchanged(self, test_app):
        """Real production bug: a stale epoch (set days earlier, e.g. by
        an unrelated prior save) drifted the rotation offset away from 0
        even when the order itself was never actually re-shuffled - the
        admin's own calendar had merely been cleared for testing between
        two generate attempts with the same order. The configured order
        must always be authoritative for non-locked weeks, so every
        save/generate call realigns the epoch to today unconditionally
        (see [[project-automation-engine-rework]] for the full incident)."""
        from datetime import date

        from app.models import AutomationConfig

        AutomationAdminService.save_rotation_order([1, 2, 3])
        AutomationConfig.set_rotation_epoch(date(2020, 5, 1))

        AutomationAdminService.save_rotation_order([1, 2, 3])
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
