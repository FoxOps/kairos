"""
Light tests for the combined "notifications enabled" guard in
scripts/send_shift_notifications.py and scripts/send_oncall_notifications.py:
SettingsService.get_notifications_enabled() (DB override, falls back to
the NOTIFICATIONS_ENABLED env var) is checked alongside SMTP
completeness, inside the scripts' own app.app_context().

Deliberately narrow (per CLAUDE.md's testing conventions for these cron
entry points, which have no existing test layer beyond config parsing):
only the "disabled -> short-circuits, service never called" path is
covered here - it needs no real DB access, unlike the full-send path.
"""

from unittest.mock import patch

import scripts.send_oncall_notifications as send_oncall_notifications
import scripts.send_shift_notifications as send_shift_notifications


class TestSendShiftNotificationsEnabledCheck:
    def test_disabled_short_circuits_without_sending(self, monkeypatch):
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")

        with (
            patch(
                "app.services.SettingsService.get_notifications_enabled",
                return_value=False,
            ),
            patch(
                "app.services.NotificationService.send_weekly_shift_notifications"
            ) as mock_send,
        ):
            exit_code = send_shift_notifications.main()

        assert exit_code == 0
        mock_send.assert_not_called()

    def test_missing_smtp_host_short_circuits_even_if_db_enabled(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")

        with (
            patch(
                "app.services.SettingsService.get_notifications_enabled",
                return_value=True,
            ),
            patch(
                "app.services.NotificationService.send_weekly_shift_notifications"
            ) as mock_send,
        ):
            exit_code = send_shift_notifications.main()

        assert exit_code == 0
        mock_send.assert_not_called()


class TestSendOncallNotificationsEnabledCheck:
    def test_disabled_short_circuits_without_sending(self, monkeypatch):
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")

        with (
            patch(
                "app.services.SettingsService.get_notifications_enabled",
                return_value=False,
            ),
            patch(
                "app.services.NotificationService.send_weekly_oncall_notification"
            ) as mock_send,
        ):
            exit_code = send_oncall_notifications.main()

        assert exit_code == 0
        mock_send.assert_not_called()
