"""
Configuration des tests pour Leviia Schedule.
"""
import pytest
from app import create_app, db
from app.models import Group, User, Shift, OnCall, Leave
from datetime import datetime, timedelta


@pytest.fixture(scope='session')
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Importer les routes pour qu'elles soient enregistrées
    from app.routes import main, admin, export
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Crée un client de test pour Flask."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Crée une session de base de données pour les tests."""
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture
def test_group(db_session):
    """Crée un groupe de test."""
    group = Group(
        name='Test Group',
        is_part_of_schedule=True,
        is_part_of_oncall=True
    )
    db_session.add(group)
    db_session.commit()
    return group


@pytest.fixture
def test_user(db_session, test_group):
    """Crée un utilisateur de test."""
    user = User(
        name='Test User',
        email='test@example.com',
        group_id=test_group.id
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_shift(db_session, test_user):
    """Crée un shift de test."""
    start_time = datetime(2023, 12, 1, 7, 0)
    end_time = datetime(2023, 12, 1, 15, 0)
    shift = Shift(
        user_id=test_user.id,
        shift_type='morning',
        start_time=start_time,
        end_time=end_time,
        date=start_time.date()
    )
    db_session.add(shift)
    db_session.commit()
    return shift


@pytest.fixture
def test_oncall(db_session, test_user):
    """Crée une astreinte de test."""
    start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
    end_time = start_time + timedelta(days=7, hours=-14)  # Vendredi suivant 7h
    oncall = OnCall(
        user_id=test_user.id,
        start_time=start_time,
        end_time=end_time
    )
    db_session.add(oncall)
    db_session.commit()
    return oncall


@pytest.fixture
def test_leave(db_session, test_user):
    """Crée un congé de test."""
    start_date = datetime(2023, 12, 10).date()
    end_date = datetime(2023, 12, 15).date()
    leave = Leave(
        user_id=test_user.id,
        start_date=start_date,
        end_date=end_date,
        reason='Test Leave'
    )
    db_session.add(leave)
    db_session.commit()
    return leave
