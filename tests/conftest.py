"""
Configuration des tests pour Leviia Schedule.

Cette version utilise l'instance globale de l'application et la reconfigure
pour chaque test.
"""

import pytest
import warnings
from datetime import datetime, timedelta

# Filtrer les warnings de dprciation de datetime.utcnow()
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flask_login")

# Importer l'instance globale de l'application
from app import app as flask_app, db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="function")
def test_app():
    """
    Fixture qui configure l'instance globale de l'application pour les tests.
    
    Note: On utilise l'instance globale existante et on modifie sa configuration
    pour les tests. Cela vite les problmes de circular import.
    """
    # Sauvegarder la configuration originale
    original_testing = flask_app.config.get("TESTING")
    original_db_uri = flask_app.config.get("SQLALCHEMY_DATABASE_URI")
    original_csrf = flask_app.config.get("WTF_CSRF_ENABLED")
    original_secret = flask_app.config.get("SECRET_KEY")
    original_rate_limit = flask_app.config.get("RATE_LIMIT_ENABLED")
    
    # Configurer pour les tests
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    flask_app.config["RATE_LIMIT_ENABLED"] = False
    
    # Dsactiver le cache pour les tests
    from app.utils.cache import CacheConfig
    original_cache_enabled = CacheConfig.CACHE_ENABLED
    CacheConfig.CACHE_ENABLED = False
    
    # Dsactiver le rate limiter pour les tests
    from app import limiter
    original_limiter_enabled = limiter.enabled
    limiter.enabled = False
    
    # Crer un contexte d'application
    with flask_app.app_context():
        # Re-crer les tables pour le test
        db.drop_all()
        db.create_all()
        yield flask_app
        # Nettoyer aprs le test
        db.session.rollback()
        db.drop_all()
    
    # Restaurer la configuration originale
    flask_app.config["TESTING"] = original_testing
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = original_db_uri
    flask_app.config["WTF_CSRF_ENABLED"] = original_csrf
    flask_app.config["SECRET_KEY"] = original_secret
    flask_app.config["RATE_LIMIT_ENABLED"] = original_rate_limit
    CacheConfig.CACHE_ENABLED = original_cache_enabled
    limiter.enabled = original_limiter_enabled


@pytest.fixture
def client(test_app):
    """Client de test Flask avec cookies et session activés."""
    # Utiliser use_cookies=True pour sauvegarder les cookies de session
    with test_app.test_client(use_cookies=True) as client:
        yield client


@pytest.fixture
def test_group(test_app):
    """Cre un groupe de test."""
    group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def test_user(test_app, test_group):
    """Cre un utilisateur normal."""
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
    """Cre un utilisateur administrateur."""
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
def logged_in_client(client):
    """Client de test Flask avec un utilisateur connect."""
    from app.models import Group
    
    # Crer un groupe et un utilisateur dans le contexte du client
    with client.application.app_context():
        # Crer un groupe
        group = Group(name="Test Group Login")
        db.session.add(group)
        db.session.commit()
        
        # Crer un utilisateur
        user = User(
            email="login@example.com",
            name="Login User",
            password_hash=generate_password_hash("loginpassword"),
            is_admin=True,
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()
    
    # Se connecter - le client sauvegarde automatiquement les cookies avec use_cookies=True
    client.post('/login', data={
        'email': 'login@example.com',
        'password': 'loginpassword'
    }, follow_redirects=True)
    
    yield client
    
    # Se dconnecter
    client.get('/logout', follow_redirects=True)


@pytest.fixture
def test_shift_type(test_app):
    """Cre un type de shift de test."""
    from app.models import ShiftType
    shift_type = ShiftType(
        name='morning',
        label='Matin',
        start_hour=7,
        end_hour=15
    )
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


# Alias pour la compatibilit avec les tests existants
app = test_app
