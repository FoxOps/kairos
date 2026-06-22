"""
Tests prioritaires pour auth.py.
"""

import pytest
from app import db
from app.models import User, Group


class TestRegisterRoute:
    """Tests pour /register."""

    def test_register_get(self, client):
        """Test l'affichage de la page d'inscription."""
        response = client.get("/register")
        assert response.status_code == 302
        assert response.location.endswith("/login")

    def test_register_post(self, client):
        """Test l'inscription (désactivée)."""
        response = client.post(
            "/register",
            data={"name": "New User", "email": "new@test.com", "password": "password123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        # L'inscription publique est désactivée
        assert b"Connexion" in response.data


class TestProfileRoute:
    """Tests pour /profile."""

    def test_profile_get(self, logged_in_client, test_user):
        """Test l'affichage du profil."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200

    def test_profile_unauthenticated(self, client):
        """Test que le profil nécessite une authentification."""
        response = client.get("/profile", follow_redirects=True)
        assert b"Connexion" in response.data


class TestUpdateProfileRoute:
    """Tests pour /profile/update."""

    def test_update_profile_get(self, logged_in_client, test_user):
        """Test l'affichage du formulaire de mise à jour."""
        response = logged_in_client.get("/profile/update")
        assert response.status_code == 200

    def test_update_profile_get_unauthenticated(self, client):
        """Test que la mise à jour nécessite une authentification."""
        response = client.get("/profile/update", follow_redirects=True)
        assert b"Connexion" in response.data

    def test_update_profile_post_name(self, logged_in_client, test_user):
        """Test la mise à jour du nom."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Updated Name",
                "email": test_user.email,
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated_user = db.session.get(User, test_user.id)
        assert updated_user.name == "Updated Name"

    def test_update_profile_post_empty_name(self, logged_in_client, test_user):
        """Test avec un nom vide."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "",
                "email": test_user.email,
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoires" in response.data

    def test_update_profile_post_with_password(self, logged_in_client, test_user):
        """Test la mise à jour avec un nouveau mot de passe."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": test_user.name,
                "email": test_user.email,
                "current_password": "test123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated_user = db.session.get(User, test_user.id)
        assert updated_user.check_password("newpassword123") is True

    def test_update_profile_post_password_mismatch(self, logged_in_client, test_user):
        """Test avec des mots de passe non correspondants."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": test_user.name,
                "email": test_user.email,
                "current_password": "test123",
                "new_password": "newpassword123",
                "confirm_password": "different",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"ne correspondent pas" in response.data

    def test_update_profile_post_wrong_current_password(self, logged_in_client, test_user):
        """Test avec un mot de passe actuel incorrect."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": test_user.name,
                "email": test_user.email,
                "current_password": "wrong",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"incorrect" in response.data


class TestLogoutRoute:
    """Tests pour /logout."""

    def test_logout(self, logged_in_client):
        """Test la déconnexion."""
        response = logged_in_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200


class TestLoginRoute:
    """Tests supplémentaires pour /login."""

    def test_login_with_remember(self, client, test_user):
        """Test la connexion avec 'se souvenir de moi'."""
        response = client.post(
            "/login",
            data={"email": test_user.email, "password": "test123", "remember": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_login_with_empty_email(self, client):
        """Test avec un email vide."""
        response = client.post(
            "/login",
            data={"email": "", "password": "test123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoires" in response.data

    def test_login_with_empty_password(self, client, test_user):
        """Test avec un mot de passe vide."""
        response = client.post(
            "/login",
            data={"email": test_user.email, "password": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoires" in response.data

    def test_login_with_wrong_password(self, client, test_user):
        """Test avec un mot de passe incorrect."""
        response = client.post(
            "/login",
            data={"email": test_user.email, "password": "wrong"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"incorrect" in response.data

    def test_login_with_nonexistent_user(self, client):
        """Test avec un utilisateur inexistant."""
        response = client.post(
            "/login",
            data={"email": "nonexistent@test.com", "password": "password"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"incorrect" in response.data
