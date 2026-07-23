"""
Tests for scripts/notification_config.py (loading the email
notifications config from environment variables).
"""

from scripts.notification_config import NotificationConfig

NOTIFICATION_ENV_VARS = [
    "NOTIFICATIONS_ENABLED",
    "NOTIFICATION_FROM_EMAIL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_USE_TLS",
    "SMTP_TIMEOUT",
    "NOTIFICATION_APP_BASE_URL",
]


def clear_notification_env(monkeypatch):
    for var in NOTIFICATION_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class TestNotificationConfigDefaults:
    def test_defaults_when_no_env_vars_set(self, monkeypatch):
        clear_notification_env(monkeypatch)
        config = NotificationConfig.from_env()

        assert config.enabled is False
        assert config.from_email is None
        assert config.smtp_host is None
        assert config.smtp_port == 587
        assert config.smtp_use_tls is True
        assert config.smtp_timeout == 10
        assert config.app_base_url is None

    def test_disabled_by_default_is_not_configured(self, monkeypatch):
        clear_notification_env(monkeypatch)
        config = NotificationConfig.from_env()
        assert config.is_configured() is False


class TestNotificationConfigFromEnv:
    def test_reads_all_variables(self, monkeypatch):
        clear_notification_env(monkeypatch)
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "2525")
        monkeypatch.setenv("SMTP_USERNAME", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "secret")
        monkeypatch.setenv("SMTP_USE_TLS", "false")
        monkeypatch.setenv("SMTP_TIMEOUT", "30")
        monkeypatch.setenv("NOTIFICATION_APP_BASE_URL", "https://schedule.example.com")

        config = NotificationConfig.from_env()

        assert config.enabled is True
        assert config.from_email == "noreply@kairos.local"
        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 2525
        assert config.smtp_username == "user"
        assert config.smtp_password == "secret"
        assert config.smtp_use_tls is False
        assert config.smtp_timeout == 30
        assert config.app_base_url == "https://schedule.example.com"

    def test_invalid_port_falls_back_to_default(self, monkeypatch):
        clear_notification_env(monkeypatch)
        monkeypatch.setenv("SMTP_PORT", "not-a-number")
        config = NotificationConfig.from_env()
        assert config.smtp_port == 587


class TestNotificationConfigIsConfigured:
    def test_configured_when_enabled_with_from_email_and_host(self, monkeypatch):
        clear_notification_env(monkeypatch)
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        config = NotificationConfig.from_env()
        assert config.is_configured() is True

    def test_not_configured_when_enabled_but_missing_smtp_host(self, monkeypatch):
        clear_notification_env(monkeypatch)
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("NOTIFICATION_FROM_EMAIL", "noreply@kairos.local")
        config = NotificationConfig.from_env()
        assert config.is_configured() is False

    def test_not_configured_when_enabled_but_missing_from_email(self, monkeypatch):
        clear_notification_env(monkeypatch)
        monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        config = NotificationConfig.from_env()
        assert config.is_configured() is False
