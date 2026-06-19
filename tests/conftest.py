"""
Configuration des tests pour Leviia Schedule.
"""
import pytest
from app import create_app, db
from app.models import User, Group, Shift, OnCall, Leave
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    # Importer les routes
    from app.routes import main, admin, export, auth

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Client de test Flask."""
    with app.test_client() as client:
        yield client


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
def admin_user(app):
    """Crée un utilisateur administrateur."""
    with app.app_context():
        group = Group.query.first()
        if not group:
            group = Group(name='Admin Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
        
        user = User(
            name='Admin User',
            email='admin@test.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_user(app):
    """Crée un utilisateur normal."""
    with app.app_context():
        group = Group.query.first()
        if not group:
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
        
        user = User(
            name='Test User',
            email='test@test.com',
            password_hash=generate_password_hash('test123'),
            is_admin=False,
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_shift(app, test_user):
    """Crée un shift de test."""
    with app.app_context():
        from datetime import datetime, timedelta
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=8)
        
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
        from datetime import datetime, timedelta
        # Commence un vendredi à 21h
        now = datetime.now()
        days_until_friday = (4 - now.weekday()) % 7
        start_time = datetime.combine(now.date(), datetime.min.time()).replace(hour=21) + timedelta(days=days_until_friday)
        end_time = start_time + timedelta(days=7, hours=-14)
        
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
        from datetime import datetime, timedelta
        start_date = datetime.now().date() + timedelta(days=10)
        end_date = start_date + timedelta(days=5)
        
        leave = Leave(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            reason='Test Leave'
        )
        db.session.add(leave)
        db.session.commit()
        return leave


@pytest.fixture
def logged_in_client(client, test_user):
    """Client de test avec un utilisateur connecté."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True
    yield client


@pytest.fixture
def logged_in_admin_client(client, admin_user):
    """Client de test avec un administrateur connecté."""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['_fresh'] = True
    yield client
