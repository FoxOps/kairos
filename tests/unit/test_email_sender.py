"""
Tests pour app/utils/notifications/email_sender.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.notifications import send_email


class TestSendEmail:
    def test_builds_multipart_message_and_sends(self):
        with patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance

            send_email(
                smtp_host="smtp.example.com",
                smtp_port=587,
                from_email="noreply@kairos.local",
                to_email="alice@example.com",
                subject="Sujet de test",
                html_body="<p>Bonjour</p>",
                text_body="Bonjour",
            )

            mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
            instance.starttls.assert_called_once()
            instance.sendmail.assert_called_once()

            from_arg, to_arg, message_str = instance.sendmail.call_args[0]
            assert from_arg == "noreply@kairos.local"
            assert to_arg == ["alice@example.com"]
            assert "Subject: Sujet de test" in message_str
            assert "Bonjour" in message_str

    def test_skips_starttls_when_use_tls_false(self):
        with patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance

            send_email(
                smtp_host="smtp.example.com",
                smtp_port=25,
                from_email="noreply@kairos.local",
                to_email="alice@example.com",
                subject="Sujet",
                html_body="<p>x</p>",
                text_body="x",
                smtp_use_tls=False,
            )

            instance.starttls.assert_not_called()

    def test_logs_in_when_credentials_provided(self):
        with patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance

            send_email(
                smtp_host="smtp.example.com",
                smtp_port=587,
                from_email="noreply@kairos.local",
                to_email="alice@example.com",
                subject="Sujet",
                html_body="<p>x</p>",
                text_body="x",
                smtp_username="user",
                smtp_password="secret",
            )

            instance.login.assert_called_once_with("user", "secret")

    def test_no_login_without_credentials(self):
        with patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance

            send_email(
                smtp_host="smtp.example.com",
                smtp_port=587,
                from_email="noreply@kairos.local",
                to_email="alice@example.com",
                subject="Sujet",
                html_body="<p>x</p>",
                text_body="x",
            )

            instance.login.assert_not_called()

    def test_propagates_smtp_exception(self):
        with patch("app.utils.notifications.email_sender.smtplib.SMTP") as mock_smtp:
            instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = instance
            instance.sendmail.side_effect = OSError("connection refused")

            with pytest.raises(OSError):
                send_email(
                    smtp_host="smtp.example.com",
                    smtp_port=587,
                    from_email="noreply@kairos.local",
                    to_email="alice@example.com",
                    subject="Sujet",
                    html_body="<p>x</p>",
                    text_body="x",
                )
