"""Fixtures liées aux utilisateurs, groupes et clients de test authentifiés."""

import pytest

from app import db
from app.models import Group, User
from werkzeug.security import generate_password_hash


@pytest.fixture
def test_group(test_app):
    """Crée un groupe de test."""
    group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def group_not_in_schedule(test_app):
    """Crée un groupe de test qui ne fait pas partie du planning."""
    group = Group(name="Group Not In Schedule", is_part_of_schedule=False, is_part_of_oncall=False)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def test_user(test_app, test_group):
    """Crée un utilisateur normal."""
    user = User(
        name="Test User",
        email="test@test.com",
        password_hash=generate_password_hash("test123"),
        is_admin=False,
        group_id=test_group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(test_app, test_group):
    """Crée un utilisateur administrateur."""
    user = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True,
        group_id=test_group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def second_user(test_app, test_group):
    """Crée un deuxième utilisateur normal."""
    user = User(
        name="Second User",
        email="second@test.com",
        password_hash=generate_password_hash("test123"),
        is_admin=False,
        group_id=test_group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_client(client):
    """Client de test Flask avec un utilisateur connecté.

    Crée un utilisateur et se connecte via POST /login.
    """
    # Créer un groupe et un utilisateur dans le contexte du client
    with client.application.app_context():
        group = Group(name="Test Group Login", is_part_of_schedule=True, is_part_of_oncall=True)
        db.session.add(group)
        db.session.commit()

        user = User(
            email="login@example.com",
            name="Login User",
            password_hash=generate_password_hash("loginpassword"),
            is_admin=True,
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()

    # Se connecter via POST /login
    response = client.post(
        '/login',
        data={'email': 'login@example.com', 'password': 'loginpassword'},
        follow_redirects=True
    )
    # On devrait être sur la page d'accueil
    assert response.status_code == 200, f"Login failed with status {response.status_code}"

    yield client

    # Se déconnecter
    try:
        client.get('/logout', follow_redirects=True)
    except Exception:
        pass


@pytest.fixture
def non_admin_client(client, test_user):
    """Client de test Flask connecté avec un utilisateur non-admin (test_user).

    Utile pour vérifier qu'une route protégée par @admin_required rejette
    bien un utilisateur normal (logged_in_client est un admin).
    """
    response = client.post(
        '/login',
        data={'email': test_user.email, 'password': 'test123'},
        follow_redirects=True,
    )
    assert response.status_code == 200, f"Login failed with status {response.status_code}"

    yield client

    try:
        client.get('/logout', follow_redirects=True)
    except Exception:
        pass
