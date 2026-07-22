"""
Tests for app/services/settings_service.py.

Covers the fallback rule (DB row present wins, absent falls back live to
app.config/env) and validation rejection paths for each setting.
"""

from app.services import SettingsService


class TestDefaultTimezone:
    def test_falls_back_to_hardcoded_default_when_unset(self, test_app):
        with test_app.app_context():
            assert SettingsService.get_default_timezone() == "Europe/Paris"

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_timezone("America/New_York")
            assert error is None
            assert SettingsService.get_default_timezone() == "America/New_York"

    def test_set_writes_audit_log_entry(self, test_app):
        with test_app.app_context():
            from app.models import AuditLog

            SettingsService.set_default_timezone("America/New_York")

            entry = AuditLog.query.filter_by(action="setting.update").first()
            assert entry is not None
            assert "default_timezone=America/New_York" in entry.details

    def test_rejects_invalid_timezone(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_timezone("Not/A_Real_Zone")
            assert error is not None
            assert SettingsService.get_default_timezone() == "Europe/Paris"


class TestDefaultLanguage:
    def test_falls_back_to_hardcoded_default_when_unset(self, test_app):
        with test_app.app_context():
            assert SettingsService.get_default_language() == "fr"

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_language("en")
            assert error is None
            assert SettingsService.get_default_language() == "en"

    def test_rejects_invalid_language(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_language("de")
            assert error is not None
            assert SettingsService.get_default_language() == "fr"


class TestDefaultDateFormat:
    def test_falls_back_to_hardcoded_default_when_unset(self, test_app):
        with test_app.app_context():
            assert SettingsService.get_default_date_format() == "%d/%m/%Y"

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_date_format("%Y-%m-%d")
            assert error is None
            assert SettingsService.get_default_date_format() == "%Y-%m-%d"

    def test_rejects_invalid_date_format(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_date_format("%B %d, %Y")
            assert error is not None
            assert SettingsService.get_default_date_format() == "%d/%m/%Y"


class TestDefaultTimeFormat:
    def test_falls_back_to_hardcoded_default_when_unset(self, test_app):
        with test_app.app_context():
            assert SettingsService.get_default_time_format() == "%H:%M"

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_time_format("%I:%M %p")
            assert error is None
            assert SettingsService.get_default_time_format() == "%I:%M %p"

    def test_rejects_invalid_time_format(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_time_format("%H:%M:%S")
            assert error is not None
            assert SettingsService.get_default_time_format() == "%H:%M"


class TestPublicBaseUrl:
    def test_falls_back_to_app_config_when_unset(self, test_app):
        with test_app.app_context():
            test_app.config["PUBLIC_BASE_URL"] = "https://from-env.example.com"
            assert (
                SettingsService.get_public_base_url() == "https://from-env.example.com"
            )

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            test_app.config["PUBLIC_BASE_URL"] = "https://from-env.example.com"
            SettingsService.set_public_base_url("https://from-db.example.com")
            assert (
                SettingsService.get_public_base_url() == "https://from-db.example.com"
            )

    def test_explicit_clear_does_not_fall_back_to_env(self, test_app):
        """Bug hunt regression (v1.0): set_public_base_url(None) stores
        an empty string (the only setter that persists a falsy value on
        purpose, to represent "explicitly cleared"). get_public_base_url()
        used to check `if value:`, so an empty-string Setting row was
        treated the same as "no row at all" and silently fell back to
        the env var - contradicting the documented "a Setting row, if
        present, always wins" rule."""
        with test_app.app_context():
            test_app.config["PUBLIC_BASE_URL"] = "https://from-env.example.com"
            SettingsService.set_public_base_url("https://from-db.example.com")
            SettingsService.set_public_base_url(None)
            assert SettingsService.get_public_base_url() is None


class TestPagination:
    def test_falls_back_to_app_config_when_unset(self, test_app):
        with test_app.app_context():
            test_app.config["ITEMS_PER_PAGE"] = 20
            test_app.config["MAX_PER_PAGE"] = 100
            assert SettingsService.get_items_per_page() == 20
            assert SettingsService.get_max_per_page() == 100

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_pagination(items_per_page=10, max_per_page=50)
            assert error is None
            assert SettingsService.get_items_per_page() == 10
            assert SettingsService.get_max_per_page() == 50

    def test_rejects_non_positive_values(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_pagination(items_per_page=0, max_per_page=50)
            assert error is not None

    def test_rejects_items_per_page_above_max(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_pagination(items_per_page=200, max_per_page=50)
            assert error is not None

    def test_rejection_does_not_corrupt_other_keys(self, test_app):
        with test_app.app_context():
            SettingsService.set_default_timezone("America/New_York")
            SettingsService.set_pagination(items_per_page=200, max_per_page=50)
            assert SettingsService.get_default_timezone() == "America/New_York"


class TestNotificationsEnabled:
    def test_falls_back_to_env_when_unset(self, test_app, monkeypatch):
        with test_app.app_context():
            monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
            assert SettingsService.get_notifications_enabled() is True

    def test_db_override_wins(self, test_app, monkeypatch):
        with test_app.app_context():
            monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
            SettingsService.set_notifications_enabled(False)
            assert SettingsService.get_notifications_enabled() is False


class TestBackupRetention:
    def test_returns_none_when_unset(self, test_app):
        """None signals BackupService.get_config() to fall back to
        BackupConfig.from_env() itself - see app/services/backup_service.py."""
        with test_app.app_context():
            assert SettingsService.get_backup_retention_days() is None
            assert SettingsService.get_backup_max_backups() is None

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_backup_retention(
                retention_days=60, max_backups=15
            )
            assert error is None
            assert SettingsService.get_backup_retention_days() == 60
            assert SettingsService.get_backup_max_backups() == 15

    def test_rejects_non_positive_values(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_backup_retention(
                retention_days=0, max_backups=15
            )
            assert error is not None


class TestScheduleRetentionDays:
    def test_falls_back_to_365_when_unset(self, test_app):
        """No env-var equivalent (brand new concept) and no None
        sentinel either, unlike backup/audit retention - see
        FALLBACK_SCHEDULE_RETENTION_DAYS's docstring."""
        with test_app.app_context():
            assert SettingsService.get_schedule_retention_days() == 365

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_schedule_retention_days(90)
            assert error is None
            assert SettingsService.get_schedule_retention_days() == 90

    def test_zero_is_a_valid_value_meaning_never_purge(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_schedule_retention_days(0)
            assert error is None
            assert SettingsService.get_schedule_retention_days() == 0

    def test_rejects_negative_value(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_schedule_retention_days(-1)
            assert error is not None


class TestIcsTokenExpiryDays:
    def test_falls_back_to_env_when_unset(self, test_app, monkeypatch):
        with test_app.app_context():
            monkeypatch.setenv("ICS_TOKEN_EXPIRY_DAYS", "90")
            assert SettingsService.get_ics_token_expiry_days() == 90

    def test_db_override_wins(self, test_app, monkeypatch):
        with test_app.app_context():
            monkeypatch.setenv("ICS_TOKEN_EXPIRY_DAYS", "90")
            SettingsService.set_ics_token_expiry_days(30)
            assert SettingsService.get_ics_token_expiry_days() == 30

    def test_rejects_non_positive_value(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_ics_token_expiry_days(0)
            assert error is not None


class TestAppriseNotificationsEnabled:
    def test_defaults_to_false(self, test_app):
        with test_app.app_context():
            assert SettingsService.get_apprise_notifications_enabled() is False

    def test_db_override_wins(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_apprise_notifications_enabled(True)
            assert error is None
            assert SettingsService.get_apprise_notifications_enabled() is True


class TestSetWithAuditFailurePath:
    """_set_with_audit() (the shared skeleton every setter above now
    goes through) - an unexpected failure must never raise (returned as
    an error string instead, same convention as before), and must now
    actually be logged, unlike before this cleanup pass where it was
    silently swallowed - the only settings-related exception with no
    trace anywhere, inconsistent with audit_service.py/
    apprise_notification_service.py/backup_service.py."""

    def test_does_not_raise_and_returns_error_string(self, test_app):
        from unittest.mock import patch

        with test_app.app_context():
            with patch(
                "app.services.settings_service.Setting.set",
                side_effect=RuntimeError("db is down"),
            ):
                error = SettingsService.set_default_timezone("Europe/Paris")

            assert error == "db is down"

    def test_logs_the_exception(self, test_app, caplog):
        from unittest.mock import patch

        with test_app.app_context():
            with patch(
                "app.services.settings_service.Setting.set",
                side_effect=RuntimeError("db is down"),
            ):
                with caplog.at_level("ERROR"):
                    SettingsService.set_default_timezone("Europe/Paris")

            assert any(
                "default_timezone" in record.message for record in caplog.records
            )
