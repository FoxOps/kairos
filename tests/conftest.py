"""
Configuration des tests pour Leviia Schedule.

Cette version utilise create_app() pour créer une nouvelle instance de l'application
pour les tests, ce qui permet de désactiver Talisman avant son initialisation.

Mise à jour pour Flask 3.x et Flask-Login 0.6.3.
"""

import pytest
import warnings
import os

# Filtrer les warnings de dépréciation de datetime.utcnow()
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flask_login")

# Importer les modules nécessaires
from app import db, limiter

# Fixtures de modèles (user/group, shift/shift_type, leave, oncall) extraites
# dans tests/fixtures/ - déclarées ici pour rester visibles dans tous les
# sous-dossiers (unit/integration/e2e) sans import explicite par test.
pytest_plugins = [
    "tests.fixtures.user_fixtures",
    "tests.fixtures.shift_fixtures",
    "tests.fixtures.leave_fixtures",
    "tests.fixtures.oncall_fixtures",
]


@pytest.fixture(scope="function")
def test_app():
    """
    Fixture qui crée une nouvelle instance de l'application pour les tests.
    Désactive Talisman et OIDC avant son initialisation.
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


# Alias requis par pytest-flask : son fixture autouse _configure_application
# cherche une fixture nommée exactement "app" (voir pytest_flask/plugin.py).
app = test_app
