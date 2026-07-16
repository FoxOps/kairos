"""
Targeted tests for the non-OIDC branches of app/routes/auth.py not
covered by test_auth_priority.py: redirect when already logged in,
update_profile (validation + password change), ICS token generation.

The OIDC branches (oidc_login/oidc_callback/logout in OIDC mode) are
deliberately left out: they require mocking the Authlib client
(authorization-code exchange, userinfo, id_token) - a separate, heavier
effort, not a simple test addition.
"""

from unittest.mock import patch

from app.models import AuditLog, User


class TestLoginRedirectsIfAlreadyAuthenticated:
    def test_get_login_while_authenticated_redirects(self, test_app, logged_in_client):
        resp = logged_in_client.get("/login", follow_redirects=False)
        assert resp.status_code == 302


class TestUpdateProfile:
    def test_empty_name_rejected(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/update",
            data={"name": "", "email": "admin@leviia.local"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"obligatoires" in resp.data

    def test_email_already_used_by_another_user(
        self, test_app, logged_in_client, test_user
    ):
        resp = logged_in_client.post(
            "/profile/update",
            data={"name": "Admin", "email": test_user.email},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "déjà utilisé".encode() in resp.data

    def test_password_change_requires_current_password(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin",
                "email": "login@example.com",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"mot de passe actuel est obligatoire" in resp.data

    def test_password_change_wrong_current_password(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin",
                "email": "login@example.com",
                "current_password": "wrong-password",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"incorrect" in resp.data

    def test_password_change_mismatch_confirmation(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin",
                "email": "login@example.com",
                "current_password": "loginpassword",
                "new_password": "newpass123",
                "confirm_password": "different",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"ne correspondent pas" in resp.data

    def test_password_change_success(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin Renamed",
                "email": "login@example.com",
                "current_password": "loginpassword",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "mis à jour avec succès".encode() in resp.data

    def test_password_change_writes_audit_log_entry(self, test_app, logged_in_client):
        logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin",
                "email": "login@example.com",
                "current_password": "loginpassword",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=True,
        )

        with test_app.app_context():
            entry = AuditLog.query.filter_by(action="profile.password_change").first()
            assert entry is not None

    def test_name_only_update_does_not_write_password_audit_entry(
        self, test_app, logged_in_client
    ):
        logged_in_client.post(
            "/profile/update",
            data={"name": "Admin Renamed", "email": "login@example.com"},
            follow_redirects=True,
        )

        with test_app.app_context():
            entry = AuditLog.query.filter_by(action="profile.password_change").first()
            assert entry is None


class TestProfileSettings:
    """Timezone preference + per-user notification opt-out, split out of
    TestUpdateProfile since /profile/settings is a separate route/page
    from /profile/update (identity fields only)."""

    def test_valid_timezone_persists(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": "America/New_York"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.timezone == "America/New_York"

    def test_org_default_options_show_a_rendered_sample_not_the_raw_pattern(
        self, logged_in_client
    ):
        """Regression test: the "use org default" <option> for date/time
        format must show a rendered sample (e.g. "31/12/2026"), not the
        raw strftime pattern (e.g. "%d/%m/%Y") - a real bug caught via a
        screenshot after this feature shipped."""
        resp = logged_in_client.get("/profile/settings")
        html = resp.get_data(as_text=True)
        assert "(%d/%m/%Y)" not in html
        assert "(%H:%M)" not in html
        assert "(%m/%d/%Y)" not in html
        assert "(%I:%M %p)" not in html

    def test_empty_timezone_clears_to_org_default(self, test_app, logged_in_client):
        """Set then clear through two real requests on the same client -
        an out-of-band DB write in a separate app_context wouldn't be
        seen by the request-handling session's identity map (same
        cross-session staleness documented in test_swap_service.py's
        TestPurgeSwaps), so this goes through the app's own code path
        both times instead."""
        logged_in_client.post(
            "/profile/settings",
            data={"timezone": "America/New_York"},
            follow_redirects=True,
        )

        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.timezone is None

    def test_invalid_timezone_rejected_without_mutation(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": "Not/A_Real_Zone"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalide" in resp.data
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.timezone is None

    def test_valid_language_persists(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"language": "en"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.language == "en"

    def test_empty_language_clears_to_org_default(self, test_app, logged_in_client):
        logged_in_client.post(
            "/profile/settings",
            data={"language": "en"},
            follow_redirects=True,
        )

        resp = logged_in_client.post(
            "/profile/settings",
            data={"language": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.language is None

    def test_invalid_language_rejected_without_mutation(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"language": "de"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalide" in resp.data
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.language is None

    def test_valid_date_format_persists(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"date_format": "%Y-%m-%d"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.date_format == "%Y-%m-%d"

    def test_empty_date_format_clears_to_org_default(self, test_app, logged_in_client):
        logged_in_client.post(
            "/profile/settings",
            data={"date_format": "%Y-%m-%d"},
            follow_redirects=True,
        )

        resp = logged_in_client.post(
            "/profile/settings",
            data={"date_format": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.date_format is None

    def test_invalid_date_format_rejected_without_mutation(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"date_format": "%B %d, %Y"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalide" in resp.data
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.date_format is None

    def test_valid_time_format_persists(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"time_format": "%I:%M %p"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.time_format == "%I:%M %p"

    def test_empty_time_format_clears_to_org_default(self, test_app, logged_in_client):
        logged_in_client.post(
            "/profile/settings",
            data={"time_format": "%I:%M %p"},
            follow_redirects=True,
        )

        resp = logged_in_client.post(
            "/profile/settings",
            data={"time_format": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.time_format is None

    def test_invalid_time_format_rejected_without_mutation(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.post(
            "/profile/settings",
            data={"time_format": "%H:%M:%S"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalide" in resp.data
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.time_format is None

    def test_notification_section_hidden_when_disabled_org_wide(
        self, test_app, logged_in_client
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_notifications_enabled(False)

        resp = logged_in_client.get("/profile/settings")
        assert resp.status_code == 200
        assert (
            "actuellement désactivées pour toute l'organisation".encode() in resp.data
        )

    def test_notification_toggles_persist_when_enabled_org_wide(
        self, test_app, logged_in_client
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_notifications_enabled(True)

        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": ""},  # unchecked checkboxes = disabled
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.shift_notifications_enabled is False
            assert user.oncall_notifications_enabled is False

    def test_notification_toggles_ignored_when_disabled_org_wide(
        self, test_app, logged_in_client
    ):
        """A stale form submitted after an admin disables notifications
        org-wide must not silently flip a preference the user never
        saw/edited - the checkboxes are only applied when the section
        was actually visible."""
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_notifications_enabled(False)

        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.shift_notifications_enabled is True
            assert user.oncall_notifications_enabled is True

    def test_apprise_section_hidden_when_disabled_org_wide(
        self, test_app, logged_in_client
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_apprise_notifications_enabled(False)

        resp = logged_in_client.get("/profile/settings")
        assert resp.status_code == 200
        assert (
            "notifications externes sont actuellement désactivées".encode() in resp.data
        )

    def test_apprise_toggles_persist_when_enabled_org_wide(
        self, test_app, logged_in_client
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_apprise_notifications_enabled(True)

        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": ""},  # unchecked checkboxes = disabled
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.apprise_shift_notifications_enabled is False
            assert user.apprise_oncall_notifications_enabled is False

    def test_apprise_toggles_ignored_when_disabled_org_wide(
        self, test_app, logged_in_client
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_apprise_notifications_enabled(False)

        resp = logged_in_client.post(
            "/profile/settings",
            data={"timezone": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            user = User.query.filter_by(email="login@example.com").first()
            assert user.apprise_shift_notifications_enabled is True
            assert user.apprise_oncall_notifications_enabled is True


class TestGenerateIcsToken:
    def test_get_shows_current_token(self, test_app, logged_in_client):
        resp = logged_in_client.get("/profile/ics-token")
        assert resp.status_code == 200

    def test_post_regenerates_token(self, test_app, logged_in_client):
        resp = logged_in_client.post("/profile/ics-token", follow_redirects=True)
        assert resp.status_code == 200
        assert "régénéré avec succès".encode() in resp.data

    def test_post_commit_exception_handled(self, test_app, logged_in_client):
        with patch(
            "app.routes.auth.db.session.commit", side_effect=RuntimeError("boom")
        ):
            resp = logged_in_client.post("/profile/ics-token", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Erreur" in resp.data
