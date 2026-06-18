"""
Configuration des tests pour Leviia Schedule.
"""
import pytest
from app import create_app, db
from app.models import Group, User, Shift, OnCall, Leave
from datetime import datetime, timedelta


@pytest.fixture
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Crée un client de test pour Flask."""
    return app.test_client()


@pytest.fixture
def test_group(app):
    """Crée un groupe de test."""
    with app.app_context():
        group = Group(
            name='Test Group',
            is_part_of_schedule=True,
            is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()
        return group


@pytest.fixture
def test_user(app, test_group):
    """Crée un utilisateur de test."""
    with app.app_context():
        user = User(
            name='Test User',
            email='test@example.com',
            group_id=test_group.id
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_shift(app, test_user):
    """Crée un shift de test."""
    with app.app_context():
        start_time = datetime(2023, 12, 1, 7, 0)
        end_time = datetime(2023, 12, 1, 15, 0)
        shift = Shift(
            user_id=test_user.id,
            shift_type='morning',
            start_time=start_time,
            end_time=end_time,
            date=start_time.date()
        )
        db.session.add(shift)
        db.session.commit()
        return shift


@pytest.fixture
def test_oncall(app, test_user):
    """Crée une astreinte de test."""
    with app.app_context():
        start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
        end_time = start_time + timedelta(days=7, hours=-14)  # Vendredi suivant 7h
        oncall = OnCall(
            user_id=test_user.id,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(oncall)
        db.session.commit()
        return oncall


@pytest.fixture
def test_leave(app, test_user):
    """Crée un congé de test."""
    with app.app_context():
        start_date = datetime(2023, 12, 10).date()
        end_date = datetime(2023, 12, 15).date()
        leave = Leave(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            reason='Test Leave'
        )
        db.session.add(leave)
        db.session.commit()
        return leave
