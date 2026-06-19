"""
Configuration des tests pour Leviia Schedule.
"""

import pytest
from app import create_app, db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="function")
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"

    # Importer les routes
    from app.routes import main, admin, export, auth

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def client(app):
    """Client de test Flask."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_group(app):
    """Crée un groupe de test."""
    group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def admin_user(app, test_group):
    """Crée un utilisateur administrateur."""
    group = test_group
    user = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True,
        group_id=group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_user(app, test_group):
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
def second_user(app, test_group):
    """Crée un deuxième utilisateur normal."""
    user = User(
        name="Second User",
        email="second@test.com",
        password_hash=generate_password_hash("second123"),
        is_admin=False,
        group_id=test_group.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_shift_type(app):
    """Crée un type de shift de test."""
    shift_type = ShiftType(name="morning", label="Matin", start_hour=7, end_hour=15)
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


@pytest.fixture
def afternoon_shift_type(app):
    """Crée un type de shift après-midi."""
    shift_type = ShiftType(
        name="afternoon", label="Après-midi", start_hour=14, end_hour=22
    )
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


@pytest.fixture
def test_shift(app, test_user, test_shift_type):
    """Crée un shift de test."""
    from datetime import datetime, timedelta

    start_time = datetime.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=8)

    shift = Shift(
        user_id=test_user.id,
        shift_type_id=test_shift_type.id,
        start_time=start_time,
        end_time=end_time,
        date=start_time.date(),
    )
    db.session.add(shift)
    db.session.commit()
    return shift


@pytest.fixture
def test_oncall(app, test_user):
    """Crée une astreinte de test."""
    from datetime import datetime, timedelta

    # Commence un vendredi à 21h
    now = datetime.now()
    days_until_friday = (4 - now.weekday()) % 7
    start_time = datetime.combine(now.date(), datetime.min.time()).replace(
        hour=21
    ) + timedelta(days=days_until_friday)
    end_time = start_time + timedelta(days=7, hours=-14)

    oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
    db.session.add(oncall)
    db.session.commit()
    return oncall


@pytest.fixture
def test_leave(app, test_user):
    """Crée un congé de test."""
    from datetime import datetime, timedelta

    start_date = datetime.now().date() + timedelta(days=10)
    end_date = start_date + timedelta(days=5)

    leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
    db.session.add(leave)
    db.session.commit()
    return leave


@pytest.fixture
def logged_in_client(client, test_user, app):
    """Client de test avec un utilisateur connecté."""
    # Se connecter via le formulaire de login
    with app.app_context():
        client.post(
            "/login",
            data={"email": test_user.email, "password": "test123"},
            follow_redirects=True,
        )
    yield client


@pytest.fixture
def logged_in_admin_client(client, admin_user, app):
    """Client de test avec un administrateur connecté."""
    # Se connecter via le formulaire de login
    with app.app_context():
        client.post(
            "/login",
            data={"email": admin_user.email, "password": "admin123"},
            follow_redirects=True,
        )
    yield client


@pytest.fixture
def group_not_in_schedule(app):
    """Crée un groupe qui n'est pas dans le planning."""
    group = Group(
        name="Group No Schedule", is_part_of_schedule=False, is_part_of_oncall=False
    )
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def user_not_in_schedule(app, group_not_in_schedule):
    """Crée un utilisateur dans un groupe non dans le planning."""
    user = User(
        name="User No Schedule",
        email="noschedule@test.com",
        password_hash=generate_password_hash("noschedule123"),
        is_admin=False,
        group_id=group_not_in_schedule.id,
    )
    db.session.add(user)
    db.session.commit()
    return user
