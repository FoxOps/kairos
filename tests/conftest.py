"""
Configuration des tests pour Leviia Schedule.

Cette version utilise l'instance globale de l'application et la reconfigure
pour chaque test. La fixture logged_in_client utilise maintenant une approche
plus robuste pour gérer la session.
"""

import pytest
import warnings
from datetime import datetime, timedelta

# Filtrer les warnings de dépréciation de datetime.utcnow()
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
    pour les tests. Cela évite les problèmes de circular import.
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
    
    # Désactiver le cache pour les tests
    from app.utils.cache import CacheConfig
    original_cache_enabled = CacheConfig.CACHE_ENABLED
    CacheConfig.CACHE_ENABLED = False
    
    # Désactiver le rate limiter pour les tests
    from app import limiter
    original_limiter_enabled = limiter.enabled
    limiter.enabled = False
    
    # Créer un contexte d'application
    with flask_app.app_context():
        # Re-créer les tables pour le test
        db.drop_all()
        db.create_all()
        yield flask_app
        # Nettoyer après le test
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
    # Utiliser l'instance globale avec use_cookies=True
    with test_app.test_client(use_cookies=True) as client:
        yield client


@pytest.fixture
def test_group(test_app):
    """Crée un groupe de test."""
    group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
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
def logged_in_client(client):
    """Client de test Flask avec un utilisateur connecté."""
    from app.models import Group
    from flask_login import login_user
    
    with client.application.app_context():
        # Créer un groupe
        group = Group(name="Test Group Login")
        db.session.add(group)
        db.session.commit()
        
        # Créer un utilisateur
        user = User(
            email="login@example.com",
            name="Login User",
            password_hash=generate_password_hash("loginpassword"),
            is_admin=True,
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()
        
        # Connecter l'utilisateur manuellement via Flask-Login
        # Il faut utiliser request context
        with client.session_transaction() as sess:
            # Stocker l'ID utilisateur dans la session manuellement
            sess['_user_id'] = user.id
            sess['_fresh'] = True
    
    yield client
    
    # Se déconnecter
    with client.session_transaction() as sess:
        sess.clear()


@pytest.fixture
def test_shift_type(test_app):
    """Crée un type de shift de test."""
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


# Alias pour la compatibilité avec les tests existants
app = test_app
