"""
Tests for AppriseNotificationService (app/services/apprise_notification_service.py).

apprise.Apprise talks to real external services over the network, so
every test here mocks it at its import site in the service module -
no real network call should ever happen in this suite.
"""

from unittest.mock import MagicMock, patch

from app import db
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)
from app.services.apprise_notification_service import AppriseNotificationService
from app.services.settings_service import SettingsService


class TestNotify:
    def test_master_toggle_off_sends_nothing(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create(
                "Slack", "json://localhost", True, ["swap"]
            )
            db.session.commit()

            with patch(
                "app.services.apprise_notification_service.apprise.Apprise"
            ) as mock_cls:
                AppriseNotificationService.notify("swap", "title", "body")
                mock_cls.assert_not_called()

    def test_enabled_with_matching_target_sends(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            NotificationTargetRepository.create(
                "Slack", "json://localhost", True, ["swap"]
            )
            db.session.commit()

            mock_instance = MagicMock()
            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                return_value=mock_instance,
            ):
                AppriseNotificationService.notify("swap", "title", "body")

            mock_instance.add.assert_called_once_with("json://localhost")
            mock_instance.notify.assert_called_once_with(title="title", body="body")

    def test_no_matching_category_sends_nothing(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            NotificationTargetRepository.create(
                "Slack", "json://localhost", True, ["backup"]
            )
            db.session.commit()

            with patch(
                "app.services.apprise_notification_service.apprise.Apprise"
            ) as mock_cls:
                AppriseNotificationService.notify("swap", "title", "body")
                mock_cls.assert_not_called()

    def test_one_target_failure_does_not_stop_others(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            NotificationTargetRepository.create(
                "Broken", "json://localhost", True, ["swap"]
            )
            NotificationTargetRepository.create(
                "Working", "json://localhost", True, ["swap"]
            )
            db.session.commit()

            broken_instance = MagicMock()
            broken_instance.add.side_effect = RuntimeError("boom")
            working_instance = MagicMock()

            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                side_effect=[broken_instance, working_instance],
            ):
                AppriseNotificationService.notify("swap", "title", "body")

            working_instance.notify.assert_called_once_with(title="title", body="body")

    def test_never_raises_even_if_repository_fails(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            with patch(
                "app.services.apprise_notification_service."
                "NotificationTargetRepository.list_enabled_for_category",
                side_effect=RuntimeError("db is down"),
            ):
                AppriseNotificationService.notify("swap", "title", "body")


class TestNotifyToTargets:
    def test_master_toggle_off_sends_nothing(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

            with patch(
                "app.services.apprise_notification_service.apprise.Apprise"
            ) as mock_cls:
                AppriseNotificationService.notify_to_targets(
                    [target_id], "title", "body"
                )
                mock_cls.assert_not_called()

    def test_sends_only_to_selected_targets(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            selected = NotificationTargetRepository.create(
                "Selected", "json://localhost", True, []
            )
            NotificationTargetRepository.create(
                "Not selected", "json://localhost", True, []
            )
            db.session.commit()

            mock_instance = MagicMock()
            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                return_value=mock_instance,
            ):
                AppriseNotificationService.notify_to_targets(
                    [selected.id], "title", "body"
                )

            mock_instance.add.assert_called_once_with("json://localhost")
            mock_instance.notify.assert_called_once_with(title="title", body="body")

    def test_disabled_target_skipped(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            target = NotificationTargetRepository.create(
                "Disabled", "json://localhost", False, []
            )
            db.session.commit()
            target_id = target.id

            with patch(
                "app.services.apprise_notification_service.apprise.Apprise"
            ) as mock_cls:
                AppriseNotificationService.notify_to_targets(
                    [target_id], "title", "body"
                )
                mock_cls.assert_not_called()

    def test_unknown_target_id_skipped_without_raising(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            AppriseNotificationService.notify_to_targets([999999], "title", "body")

    def test_never_raises_even_if_repository_fails(self, test_app):
        with test_app.app_context():
            SettingsService.set_apprise_notifications_enabled(True)
            with patch(
                "app.services.apprise_notification_service."
                "NotificationTargetRepository.get_by_id",
                side_effect=RuntimeError("db is down"),
            ):
                AppriseNotificationService.notify_to_targets([1], "title", "body")


class TestSendTest:
    def test_success(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()

            mock_instance = MagicMock()
            mock_instance.add.return_value = True
            mock_instance.notify.return_value = True
            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                return_value=mock_instance,
            ):
                ok, error = AppriseNotificationService.send_test(target)

            assert ok is True
            assert error is None

    def test_invalid_url(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "not-a-valid-url", True, []
            )
            db.session.commit()

            mock_instance = MagicMock()
            mock_instance.add.return_value = False
            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                return_value=mock_instance,
            ):
                ok, error = AppriseNotificationService.send_test(target)

            assert ok is False
            assert error is not None
            mock_instance.notify.assert_not_called()

    def test_send_failure(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()

            mock_instance = MagicMock()
            mock_instance.add.return_value = True
            mock_instance.notify.return_value = False
            with patch(
                "app.services.apprise_notification_service.apprise.Apprise",
                return_value=mock_instance,
            ):
                ok, error = AppriseNotificationService.send_test(target)

            assert ok is False
            assert error is not None
