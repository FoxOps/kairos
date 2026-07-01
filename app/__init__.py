"""
Initialisation de l'application Flask pour Leviia Schedule.

Note: Ce module utilise une approche hybride pour supporter à la fois
l'instance globale (pour la compatibilité) et la factory function create_app().
"""

import logging
import os
import secrets

from flask import Flask
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Initialisation des extensions
# ---------------------------------------------------------------------------

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "danger"
limiter = Limiter(key_func=get_remote_address)

# Variable pour la factory function
_app_for_factory = None


def asset_exists_filter(app, filename):
    """Vérifie si un fichier existe dans le dossier static."""
    static_folder = app.static_folder
    if static_folder:
        filepath = os.path.join(static_folder, filename)
        return os.path.exists(filepath)
    return False


def create_app(config_object="config.Config"):
    """
    Factory function pour créer et configurer l'application Flask.
    
    Cette fonction peut être appelée pour créer une nouvelle instance
    de l'application, utile pour les tests.
    
    Args:
        config_object: Objet de configuration à utiliser
        
    Returns:
        Instance de l'application Flask
    """
    global _app_for_factory
    
    # Si une instance existe déjà, la retourner
    if _app_for_factory is not None:
        return _app_for_factory
    
    # Créer l'application Flask
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )
    
    # Charger la configuration
    app.config.from_object(config_object)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Initialiser les extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Configurer le rate limiting si activé
    if app.config.get('RATE_LIMIT_ENABLED', True):
        limiter.enabled = True
        # Appliquer les limites par défaut
        limiter.limit(app.config.get('RATE_LIMIT_DEFAULT', '200 per day, 50 per hour'))(app)
    else:
        limiter.enabled = False
    
    # Initialiser le cache
    from app.utils.cache import init_cache
    init_cache(app)
    
    # Enregistrer le template filter pour asset_exists
    # Utiliser une fonction lambda pour capturer l'app
    app.add_template_filter(lambda filename: asset_exists_filter(app, filename), name='asset_exists')
    
    # Configuration du User Loader
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Configuration OIDC
    from config_oidc import OIDCConfig
    OIDCConfig.load_config()
    
    if OIDCConfig.ENABLED and OIDCConfig.is_configured():
        from app.auth.oidc_auth import oidc_auth
        oidc_auth.init_app(app)
    
    # Stocker l'instance pour la factory
    _app_for_factory = app
    
    # Importer les routes
    from app.routes import admin, auth, export, main
    
    return app


# ---------------------------------------------------------------------------
# Instance globale par défaut (créée directement pour éviter les circular imports)
# ---------------------------------------------------------------------------
# On crée l'instance directement ici pour que les imports dans les routes fonctionnent
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

app.config.from_object("config.Config")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Initialiser les extensions
db.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)

# Enregistrer le template filter pour asset_exists sur l'instance globale
app.add_template_filter(lambda filename: asset_exists_filter(app, filename), name='asset_exists')

# Configuration du User Loader
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configuration OIDC
from config_oidc import OIDCConfig
OIDCConfig.load_config()

if OIDCConfig.ENABLED and OIDCConfig.is_configured():
    from app.auth.oidc_auth import oidc_auth
    oidc_auth.init_app(app)

# Initialiser le cache
from app.utils.cache import init_cache
init_cache(app)

# Importer les routes
from app.routes import admin, auth, export, main

# Stocker l'instance pour la factory
_app_for_factory = app

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
__all__ = ['app', 'create_app', 'db', 'login_manager', 'limiter']
