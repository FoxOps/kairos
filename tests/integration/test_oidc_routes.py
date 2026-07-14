"""Tests d'intégration pour les routes OIDC (/login, /oidc/login,
/oidc/callback, /logout en mode SSO).

test_app désactive OIDC globalement (voir tests/conftest.py) - le
fixture oidc_mode ci-dessous le réactive pour ce module en patchant
directement OIDCConfig (state de classe déjà figé au moment où
test_app a fini son setup). Les appels réseau réels d'OIDCAuthLib sont
mockés au niveau du singleton `oidc_auth` importé par app/routes/auth.py
- ces tests vérifient le câblage des routes (redirections, flashs,
session), pas la logique OIDC elle-même (voir tests/unit/test_oidc_auth.py
et test_user_manager_oidc_sync.py pour ça)."""

from unittest.mock import patch

import pytest

from config_oidc import OIDCConfig


@pytest.fixture
def oidc_mode(test_app, monkeypatch):
    """Active le mode OIDC (SSO obligatoire, auth basique désactivée)."""
    monkeypatch.setattr(OIDCConfig, "ENABLED", True)
    monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", True)
    monkeypatch.setattr(OIDCConfig, "ISSUER", "https://idp.example.com")
    monkeypatch.setattr(OIDCConfig, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(OIDCConfig, "CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(OIDCConfig, "REDIRECT_URI", "http://localhost/oidc/callback")
    monkeypatch.setattr(OIDCConfig, "POST_LOGOUT_REDIRECT_URI", "")


@pytest.fixture
def oidc_optional_mode(test_app, monkeypatch):
    """Active OIDC en mode optionnel : SSO disponible EN PLUS du
    formulaire classique (OIDC_DISABLE_BASIC_AUTH=false) - /login
    n'auto-redirige pas, affiche les deux, voir bouton "Se connecter
    avec SSO" sur auth/login.html."""
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
        # OIDC désactivé (comportement par défaut de test_app) : /login
        # affiche bien le formulaire classique, pas de redirection.
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
        """Aucun garde sur is_basic_auth_disabled() ici (il y en avait un
        avant, bug réel : bloquait aussi le SSO optionnel quand
        OIDC_DISABLE_BASIC_AUTH=false, voir CHANGELOG/commit) - c'est
        get_authorization_url() qui renvoie None (OIDC non configuré) qui
        déclenche cette redirection, avec oidc_error=1 pour éviter la
        boucle de redirection infinie documentée plus haut dans
        auth.login()."""
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
        """Même raison que TestOidcLoginRoute ci-dessus : plus de garde sur
        is_basic_auth_disabled() (bloquait le SSO optionnel), c'est
        handle_oauth_callback() qui échoue (state invalide, OIDC non
        configuré) et redirige avec oidc_error=1."""
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

        # Seul handle_oauth_callback est mocké (fait de vrais appels
        # réseau) - oidc_auth.login_user() reste la vraie implémentation
        # (sync_user_from_oidc + flask_login.login_user(), tout local,
        # pas d'appel réseau) pour que la session soit réellement établie.
        with patch(
            "app.routes.auth.oidc_auth.handle_oauth_callback",
            return_value={"email": "oidc-user@example.com", "name": "OIDC User"},
        ):
            resp = client.get("/oidc/callback?state=s1&code=abc", follow_redirects=True)

        assert resp.status_code == 200
        assert resp.request.path == "/"


class TestLogoutInOidcMode:
    """Se connecte AVANT d'activer le mode OIDC (le fixture oidc_mode
    ferait rediriger /login vers /oidc/login avant toute vérification
    d'identifiants, cf. TestLoginRedirectsToOidcWhenBasicAuthDisabled) -
    seul le comportement de /logout nous intéresse ici, pas la façon
    dont la session a été ouverte."""

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
    """SSO disponible EN PLUS du formulaire classique (bug réel : un
    garde sur is_basic_auth_disabled() dans oidc_login()/oidc_callback()
    bloquait silencieusement tout le flux SSO dès que
    OIDC_DISABLE_BASIC_AUTH=false - le clic sur "Se connecter avec SSO"
    ne faisait rien d'observable pour l'utilisateur, juste un aller-retour
    vers /login)."""

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
