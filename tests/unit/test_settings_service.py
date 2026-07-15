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

    def test_rejects_invalid_timezone(self, test_app):
        with test_app.app_context():
            error = SettingsService.set_default_timezone("Not/A_Real_Zone")
            assert error is not None
            assert SettingsService.get_default_timezone() == "Europe/Paris"


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
