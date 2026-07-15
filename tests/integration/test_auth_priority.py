"""
Tests prioritaires pour auth.py.
"""

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, User


class TestRegisterRoute:
    """Tests pour /register."""

    def test_register_get(self, client):
        """Test rendering the registration page."""
        response = client.get("/register")
        assert response.status_code == 302
        assert response.location.endswith("/login")

    def test_register_post(self, client):
        """Test registration (disabled)."""
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
        # Public registration is disabled
        assert b"Connexion" in response.data


class TestProfileRoute:
    """Tests for /profile."""

    def test_profile_get(self, client):
        """Test rendering the profile page."""
        # Create a group and a user
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

        # Log in
        response = client.post(
            "/login",
            data={"email": "profile@example.com", "password": "profilepassword"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Access the profile page
        response = client.get("/profile")
        assert response.status_code == 200

    def test_profile_unauthenticated(self, client):
        """Test that the profile page requires authentication."""
        response = client.get("/profile", follow_redirects=True)
        assert b"Connexion" in response.data
