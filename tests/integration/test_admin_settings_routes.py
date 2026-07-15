"""
Tests for the admin settings routes (app/routes/admin_settings_routes.py).
"""


class TestSettingsDashboardGet:
    def test_dashboard_get(self, logged_in_client):
        response = logged_in_client.get("/admin/settings")
        assert response.status_code == 200
        assert b"Param\xc3\xa8tres" in response.data

    def test_dashboard_unauthenticated(self, client):
        response = client.get("/admin/settings", follow_redirects=True)
        assert b"Connexion" in response.data


class TestSettingsTimezoneSection:
    def test_valid_timezone_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={"section": "timezone", "default_timezone": "America/New_York"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"enregistr\xc3\xa9" in response.data

        from app.services import SettingsService

        assert SettingsService.get_default_timezone() == "America/New_York"

    def test_invalid_timezone_flashes_error_without_persisting(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={"section": "timezone", "default_timezone": "Not/A_Real_Zone"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Erreur" in response.data

        from app.services import SettingsService

        assert SettingsService.get_default_timezone() == "Europe/Paris"


class TestSettingsGeneralSection:
    def test_public_base_url_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={
                "section": "general",
                "public_base_url": "https://schedule.example.com",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_public_base_url() == "https://schedule.example.com"


class TestSettingsPaginationSection:
    def test_valid_pagination_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={
                "section": "pagination",
                "items_per_page": "10",
                "max_per_page": "50",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_items_per_page() == 10
        assert SettingsService.get_max_per_page() == 50

    def test_invalid_pagination_flashes_error(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={
                "section": "pagination",
                "items_per_page": "200",
                "max_per_page": "50",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Erreur" in response.data


class TestSettingsNotificationsSection:
    def test_checkbox_checked_enables(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={"section": "notifications", "notifications_enabled": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_notifications_enabled() is True

    def test_checkbox_absent_disables(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={"section": "notifications"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_notifications_enabled() is False


class TestSettingsBackupsSection:
    def test_valid_retention_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={
                "section": "backups",
                "backup_retention_days": "60",
                "backup_max_backups": "15",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_backup_retention_days() == 60
        assert SettingsService.get_backup_max_backups() == 15


class TestSettingsIcsSection:
    def test_valid_expiry_persists(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/settings",
            data={"section": "ics", "ics_token_expiry_days": "30"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        from app.services import SettingsService

        assert SettingsService.get_ics_token_expiry_days() == 30
