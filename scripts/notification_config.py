"""
Kairos - Email notification configuration
=============================================================

This module holds the configuration for sending email notifications
(shift and on-call reminders). Follows the same pattern as
scripts/backup_config.py (dataclass loaded from environment variables,
used by the standalone scripts triggered via cron - no scheduler built
into the Flask app).

Available environment variables:
- NOTIFICATIONS_ENABLED: Enable/disable sending notifications (true/false)
- NOTIFICATION_FROM_EMAIL: Sender email address
- SMTP_HOST: SMTP server
- SMTP_PORT: SMTP port (default: 587)
- SMTP_USERNAME: SMTP username
- SMTP_PASSWORD: SMTP password
- SMTP_USE_TLS: Use TLS/STARTTLS (true/false)
- SMTP_TIMEOUT: SMTP connection timeout in seconds (default: 10)
- NOTIFICATION_APP_BASE_URL: Base URL of the application, for the "view
  schedule" link in emails (optional, no link if absent)
"""

import os
from dataclasses import dataclass


@dataclass
class NotificationConfig:
    """Full configuration for sending email notifications."""

    enabled: bool = False

    from_email: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout: int = 10

    app_base_url: str | None = None

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Loads the configuration from environment variables."""

        def get_bool(env_var: str, default: bool = False) -> bool:
            value = os.environ.get(env_var, "").lower()
            return value in ("true", "1", "yes", "y") if value else default

        def get_int(env_var: str, default: int = 0) -> int:
            try:
                return int(os.environ.get(env_var, default))
            except ValueError:
                return default

        def get_str(env_var: str, default: str | None = None) -> str | None:
            value = os.environ.get(env_var)
            return value if value else default

        return cls(
            enabled=get_bool("NOTIFICATIONS_ENABLED", False),
            from_email=get_str("NOTIFICATION_FROM_EMAIL"),
            smtp_host=get_str("SMTP_HOST"),
            smtp_port=get_int("SMTP_PORT", 587),
            smtp_username=get_str("SMTP_USERNAME"),
            smtp_password=get_str("SMTP_PASSWORD"),
            smtp_use_tls=get_bool("SMTP_USE_TLS", True),
            smtp_timeout=get_int("SMTP_TIMEOUT", 10),
            app_base_url=get_str("NOTIFICATION_APP_BASE_URL"),
        )

    def is_configured(self) -> bool:
        """True if enough information is available to attempt a send."""
        return bool(self.enabled and self.from_email and self.smtp_host)


# Global configuration instance
config = NotificationConfig.from_env()
