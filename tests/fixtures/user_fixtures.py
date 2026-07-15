"""User, group, and authenticated test client fixtures."""

import pytest
from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, User


@pytest.fixture
def test_group(test_app):
    """Create a test group."""
    group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def group_not_in_schedule(test_app):
    """Create a test group that isn't part of the schedule."""
    group = Group(
        name="Group Not In Schedule", is_part_of_schedule=False, is_part_of_oncall=False
    )
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def test_user(test_app, test_group):
    """Create a regular user."""
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
    """Create an admin user."""
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
    """Create a second regular user."""
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
    """Flask test client with a logged-in user.

    Creates a user and logs in via POST /login.
    """
    # Create a group and a user within the client's context
    with client.application.app_context():
        group = Group(
            name="Test Group Login", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        user = User(
            email="login@example.com",
            name="Login User",
            password_hash=generate_password_hash("loginpassword"),
            is_admin=True,
            group_id=group.id,
        )
        db.session.add(user)
        db.session.commit()

    # Log in via POST /login
    response = client.post(
        "/login",
        data={"email": "login@example.com", "password": "loginpassword"},
        follow_redirects=True,
    )
    # We should land on the home page
    assert (
        response.status_code == 200
    ), f"Login failed with status {response.status_code}"

    yield client

    # Log out
    try:
        client.get("/logout", follow_redirects=True)
    except Exception:
        pass


@pytest.fixture
def non_admin_client(client, test_user):
    """Flask test client logged in as a non-admin user (test_user).

    Useful for checking that a route protected by @admin_required
    correctly rejects a regular user (logged_in_client is an admin).
    """
    response = client.post(
        "/login",
        data={"email": test_user.email, "password": "test123"},
        follow_redirects=True,
    )
    assert (
        response.status_code == 200
    ), f"Login failed with status {response.status_code}"

    yield client

    try:
        client.get("/logout", follow_redirects=True)
    except Exception:
        pass
