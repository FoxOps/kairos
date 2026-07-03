"""
Configuration des tests pour Leviia Schedule.

Cette version utilise create_app() pour créer une nouvelle instance de l'application
pour les tests, ce qui permet de désactiver Talisman avant son initialisation.

Mise à jour pour Flask 3.x et Flask-Login 0.6.3.
"""

import pytest
import warnings
import os
from datetime import datetime, timedelta

# Filtrer les warnings de dépréciation de datetime.utcnow()
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flask_login")

# Importer les modules nécessaires
from app import db, login_manager, limiter
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user


@pytest.fixture(scope="function")
def test_app():
    """
    Fixture qui crée une nouvelle instance de l'application pour les tests.
    Désactive Talisman et OIDC avant l'initialisation.
    Scope: function pour éviter les conflits entre tests.
    """
    # Sauvegarder et désactiver OIDC pour les tests
    original_oidc_enabled = os.environ.get("OIDC_ENABLED")
    original_oidc_disable_basic = os.environ.get("OIDC_DISABLE_BASIC_AUTH")
    os.environ["OIDC_ENABLED"] = "False"
    os.environ["OIDC_DISABLE_BASIC_AUTH"] = "False"
    
    # Recharger la configuration OIDC
    from config_oidc import OIDCConfig
    OIDCConfig.ENABLED = False
    OIDCConfig.DISABLE_BASIC_AUTH = False
    
    # Créer une nouvelle instance de l'application avec une configuration de test
    from app import create_app
    app = create_app('app.config.TestingConfig')
    
    # Désactiver le rate limiter
    limiter.enabled = False
    
    # Désactiver le cache pour les tests
    from app.utils.cache import CacheConfig
    CacheConfig.CACHE_ENABLED = False
    
    # Créer un contexte d'application
    with app.app_context():
        # Re-créer les tables pour le test
        db.drop_all()
        db.create_all()
        yield app
        # Nettoyer après le test
        db.session.rollback()
        db.drop_all()
    
    # Restaurer OIDC
    if original_oidc_enabled is not None:
        os.environ["OIDC_ENABLED"] = original_oidc_enabled
    else:
        os.environ.pop("OIDC_ENABLED", None)
    if original_oidc_disable_basic is not None:
        os.environ["OIDC_DISABLE_BASIC_AUTH"] = original_oidc_disable_basic
    else:
        os.environ.pop("OIDC_DISABLE_BASIC_AUTH", None)
    OIDCConfig.load_config()


@pytest.fixture
def client(test_app):
    """Client de test Flask avec cookies et session activés.
    
    NE CRÉE PAS d'utilisateur par défaut pour éviter les conflits entre tests.
    """
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
def test_shift(test_app, test_user):
    """Crée un shift de test."""
    from datetime import date, datetime, time
    shift = Shift(
        date=date.today(),
        start_time=datetime.combine(date.today(), datetime.min.time()),
        end_time=datetime.combine(date.today(), datetime.max.time()),
        user_id=test_user.id,
        shift_type_id=1,
    )
    db.session.add(shift)
    db.session.commit()
    return shift


@pytest.fixture
def afternoon_shift_type(test_app):
    """Crée un type de shift pour l'après-midi."""
    from datetime import time
    shift_type = ShiftType(
        name="Afternoon",
        start_hour=14,
        end_hour=18,
    )
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


@pytest.fixture
def test_leave(test_app, test_user):
    """Crée un congé de test."""
    from datetime import date, timedelta
    leave = Leave(
        user_id=test_user.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=5),
    )
    db.session.add(leave)
    db.session.commit()
    return leave


@pytest.fixture
def test_oncall(test_app, test_user):
    """Crée une astreinte de test."""
    from datetime import datetime, timedelta
    oncall = OnCall(
        user_id=test_user.id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=7),
    )
    db.session.add(oncall)
    db.session.commit()
    return oncall


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
