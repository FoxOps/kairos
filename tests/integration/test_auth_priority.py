"""
Tests prioritaires pour auth.py.
"""

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, User


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
            data={
                "name": "New User",
                "email": "new@test.com",
                "password": "password123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # L'inscription publique est désactivée
        assert b"Connexion" in response.data


class TestProfileRoute:
    """Tests pour /profile."""

    def test_profile_get(self, client):
        """Test l'affichage du profil."""
        # Créer un groupe et un utilisateur
        with client.application.app_context():
            group = Group(
                name="Test Group Profile",
                is_part_of_schedule=True,
                is_part_of_oncall=True,
            )
            db.session.add(group)
            db.session.commit()

            user = User(
                email="profile@example.com",
                name="Profile User",
                password_hash=generate_password_hash("profilepassword"),
                is_admin=True,
                group_id=group.id,
            )
            db.session.add(user)
            db.session.commit()

        # Se connecter
        response = client.post(
            "/login",
            data={"email": "profile@example.com", "password": "profilepassword"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Accéder au profil
        response = client.get("/profile")
        assert response.status_code == 200

    def test_profile_unauthenticated(self, client):
        """Test que le profil nécessite une authentification."""
        response = client.get("/profile", follow_redirects=True)
        assert b"Connexion" in response.data
