"""
Tests ciblés sur les branches non-OIDC de app/routes/auth.py non couvertes
par test_auth_priority.py : redirection si déjà connecté, update_profile
(validation + changement de mot de passe), génération de token ICS.

Les branches OIDC (oidc_login/oidc_callback/logout en mode OIDC) sont
délibérément laissées de côté : elles nécessitent de mocker le client
Authlib (échange de code d'autorisation, userinfo, id_token) - un chantier
séparé, plus lourd, pas un simple ajout de tests.
"""

from unittest.mock import patch


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
