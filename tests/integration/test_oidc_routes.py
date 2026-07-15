"""Integration tests for the OIDC routes (/login, /oidc/login,
/oidc/callback, /logout in SSO mode).

test_app disables OIDC globally (see tests/conftest.py) - the
oidc_mode fixture below re-enables it for this module by patching
OIDCConfig directly (class state already frozen by the time test_app
finishes its setup). OIDCAuthLib's real network calls are mocked at
the level of the `oidc_auth` singleton imported by app/routes/auth.py
- these tests check the route wiring (redirects, flashes, session),
not the OIDC logic itself (see tests/unit/test_oidc_auth.py and
test_user_manager_oidc_sync.py for that)."""

from unittest.mock import patch

import pytest

from config_oidc import OIDCConfig


@pytest.fixture
def oidc_mode(test_app, monkeypatch):
    """Enable OIDC mode (mandatory SSO, basic auth disabled)."""
    monkeypatch.setattr(OIDCConfig, "ENABLED", True)
    monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", True)
    monkeypatch.setattr(OIDCConfig, "ISSUER", "https://idp.example.com")
    monkeypatch.setattr(OIDCConfig, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(OIDCConfig, "CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(OIDCConfig, "REDIRECT_URI", "http://localhost/oidc/callback")
    monkeypatch.setattr(OIDCConfig, "POST_LOGOUT_REDIRECT_URI", "")


@pytest.fixture
def oidc_optional_mode(test_app, monkeypatch):
    """Enable OIDC in optional mode: SSO available IN ADDITION to the
    classic form (OIDC_DISABLE_BASIC_AUTH=false) - /login doesn't
    auto-redirect, shows both, see the "Se connecter avec SSO" button
    on auth/login.html."""
    monkeypatch.setattr(OIDCConfig, "ENABLED", True)
    monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", False)
    monkeypatch.setattr(OIDCConfig, "ISSUER", "https://idp.example.com")
    monkeypatch.setattr(OIDCConfig, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(OIDCConfig, "CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(OIDCConfig, "REDIRECT_URI", "http://localhost/oidc/callback")
    monkeypatch.setattr(OIDCConfig, "POST_LOGOUT_REDIRECT_URI", "")


class TestLoginRedirectsToOidcWhenBasicAuthDisabled:
    def test_get_login_redirects_to_oidc_login(self, test_app, oidc_mode, client):
        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code == 302
        assert "/oidc/login" in resp.headers["Location"]

    def test_post_login_also_redirects_to_oidc_login(self, test_app, oidc_mode, client):
        resp = client.post(
            "/login",
            data={"email": "someone@example.com", "password": "whatever"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/oidc/login" in resp.headers["Location"]

    def test_login_form_still_works_when_oidc_not_forced(self, test_app, client):
        # OIDC disabled (test_app's default behavior): /login correctly
        # shows the classic form, no redirect.
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"password" in resp.data.lower() or b"mot de passe" in resp.data.lower()


class TestOidcLoginRoute:
    def test_redirects_to_provider_authorization_url(self, test_app, oidc_mode, client):
        with patch(
            "app.routes.auth.oidc_auth.get_authorization_url",
            return_value="https://idp.example.com/authorize?client_id=test-client-id",
        ):
            resp = client.get("/oidc/login", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["Location"].startswith("https://idp.example.com/authorize")

    def test_redirects_to_local_login_when_oidc_not_configured(self, test_app, client):
        """No guard on is_basic_auth_disabled() here (there used to be
        one, and it was a real bug: it also blocked optional SSO
        whenever OIDC_DISABLE_BASIC_AUTH=false) - this redirect is
        actually triggered by get_authorization_url() returning None
        (OIDC not configured), with oidc_error=1 to avoid the infinite
        redirect loop documented further up in auth.login()."""
        resp = client.get("/oidc/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login?oidc_error=1"

    def test_flashes_error_when_authorization_url_unavailable(
        self, test_app, oidc_mode, client
    ):
        with patch(
            "app.routes.auth.oidc_auth.get_authorization_url", return_value=None
        ):
            resp = client.get("/oidc/login", follow_redirects=True)

        assert resp.status_code == 200
        assert b"pas disponible" in resp.data


class TestOidcCallbackRoute:
    def test_redirects_to_local_login_when_oidc_not_configured(self, test_app, client):
        """Same reason as TestOidcLoginRoute above: no more guard on
        is_basic_auth_disabled() (it used to block optional SSO), it's
        handle_oauth_callback() that fails (invalid state, OIDC not
        configured) and redirects with oidc_error=1."""
        resp = client.get("/oidc/callback", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login?oidc_error=1"

    def test_callback_failure_redirects_to_login_with_flash(
        self, test_app, oidc_mode, client
    ):
        with patch(
            "app.routes.auth.oidc_auth.handle_oauth_callback", return_value=None
        ):
            resp = client.get("/oidc/callback?state=bad&code=x", follow_redirects=True)

        assert resp.status_code == 200
        request_path = resp.request.path
        assert request_path == "/login"

    def test_login_user_failure_flashes_error(self, test_app, oidc_mode, client):
        with patch(
            "app.routes.auth.oidc_auth.handle_oauth_callback",
            return_value={"email": "user@example.com"},
        ), patch("app.routes.auth.oidc_auth.login_user", return_value=None):
            resp = client.get("/oidc/callback?state=s1&code=abc", follow_redirects=True)

        assert resp.status_code == 200
        assert "a échoué".encode() in resp.data

    def test_happy_path_logs_in_and_redirects_to_index(
        self, test_app, oidc_mode, client, test_group
    ):
        from app import db
        from app.models import User

        oidc_user = User(
            name="OIDC User", email="oidc-user@example.com", group_id=test_group.id
        )
        db.session.add(oidc_user)
        db.session.commit()

        # Only handle_oauth_callback is mocked (it makes real network
        # calls) - oidc_auth.login_user() stays the real implementation
        # (sync_user_from_oidc + flask_login.login_user(), all local, no
        # network call) so the session actually gets established.
        with patch(
            "app.routes.auth.oidc_auth.handle_oauth_callback",
            return_value={"email": "oidc-user@example.com", "name": "OIDC User"},
        ):
            resp = client.get("/oidc/callback?state=s1&code=abc", follow_redirects=True)

        assert resp.status_code == 200
        assert resp.request.path == "/"


class TestLogoutInOidcMode:
    """Logs in BEFORE enabling OIDC mode (the oidc_mode fixture would
    make /login redirect to /oidc/login before any credential check,
    cf. TestLoginRedirectsToOidcWhenBasicAuthDisabled) - only /logout's
    behavior matters here, not how the session was opened."""

    def _login_then_enable_oidc_mode(self, test_app, client, test_user, monkeypatch):
        client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )
        monkeypatch.setattr(OIDCConfig, "ENABLED", True)
        monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", True)

    def test_logout_redirects_to_provider_logout_url_when_available(
        self, test_app, client, test_user, monkeypatch
    ):
        self._login_then_enable_oidc_mode(test_app, client, test_user, monkeypatch)

        with patch(
            "app.routes.auth.oidc_auth.build_logout_url",
            return_value="https://idp.example.com/logout?id_token_hint=abc",
        ):
            resp = client.get("/logout", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["Location"].startswith("https://idp.example.com/logout")

    def test_logout_falls_back_to_local_login_without_end_session_endpoint(
        self, test_app, client, test_user, monkeypatch
    ):
        self._login_then_enable_oidc_mode(test_app, client, test_user, monkeypatch)

        with patch("app.routes.auth.oidc_auth.build_logout_url", return_value=None):
            resp = client.get("/logout", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_session_actually_invalidated_after_oidc_logout(
        self, test_app, client, test_user, monkeypatch
    ):
        self._login_then_enable_oidc_mode(test_app, client, test_user, monkeypatch)

        with patch("app.routes.auth.oidc_auth.build_logout_url", return_value=None):
            client.get("/logout", follow_redirects=False)

        resp = client.get("/schedule", follow_redirects=False)
        assert resp.status_code in (302, 401)


class TestOidcOptionalMode:
    """SSO available IN ADDITION to the classic form (a real bug: a
    guard on is_basic_auth_disabled() in oidc_login()/oidc_callback()
    silently blocked the entire SSO flow whenever
    OIDC_DISABLE_BASIC_AUTH=false - clicking "Se connecter avec SSO"
    did nothing observable for the user, just a round trip back to
    /login)."""

    def test_login_page_does_not_auto_redirect(
        self, test_app, oidc_optional_mode, client
    ):
        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code == 200

    def test_login_page_shows_both_form_and_sso_button(
        self, test_app, oidc_optional_mode, client
    ):
        resp = client.get("/login")
        assert b"SSO" in resp.data
        assert b"password" in resp.data.lower() or b"mot de passe" in resp.data.lower()

    def test_oidc_login_redirects_to_provider(
        self, test_app, oidc_optional_mode, client
    ):
        with patch(
            "app.routes.auth.oidc_auth.get_authorization_url",
            return_value="https://idp.example.com/authorize?client_id=test-client-id",
        ):
            resp = client.get("/oidc/login", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["Location"].startswith("https://idp.example.com/authorize")

    def test_oidc_callback_logs_in_successfully(
        self, test_app, oidc_optional_mode, client, test_group
    ):
        from app import db
        from app.models import User

        oidc_user = User(
            name="OIDC User", email="oidc-optional@example.com", group_id=test_group.id
        )
        db.session.add(oidc_user)
        db.session.commit()

        with patch(
            "app.routes.auth.oidc_auth.handle_oauth_callback",
            return_value={"email": "oidc-optional@example.com", "name": "OIDC User"},
        ):
            resp = client.get("/oidc/callback?state=s1&code=abc", follow_redirects=True)

        assert resp.status_code == 200
        assert resp.request.path == "/"

    def test_basic_auth_login_still_works(
        self, test_app, oidc_optional_mode, client, test_user
    ):
        resp = client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert resp.request.path == "/"
