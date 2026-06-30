from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import sqlite3
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import os
import traceback
import re
from datetime import datetime

# Initialisation de la base de données
db = SQLAlchemy()

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login"  # Route pour la page de login
login_manager.login_message_category = "danger"  # Catégorie pour les messages flash

# Initialisation du cache
from app.utils.cache import cache, init_cache, CacheConfig

# Initialisation de la pagination
from app.utils.pagination import Pagination, PaginationConfig, paginate_query

# Initialisation du lazy loading
from app.utils.lazy_loading import LazyLoader, LazyCollection, LazyQuery, LazyLoadingConfig

# Créer l'instance Flask
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)
app.config.from_object("config.Config")

# CONFIGURATION DU LOGGING
# ============================================================================
# Initialiser les extensions
db.init_app(app)
login_manager.init_app(app)

# ✅ CONFIGURATION DU USER_LOADER POUR FLASK-LOGIN
# Cela doit être fait AVANT d'utiliser current_user
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur depuis la base de données."""
    return User.query.get(int(user_id))

# ✅ Recharger la configuration OIDC après que Flask ait chargé sa configuration
from config_oidc import OIDCConfig
OIDCConfig.load_config()  # Recharger la configuration

# ============================================================================
# DEBUG: Vérifier la configuration OIDC
# ============================================================================
app.logger.info("=" * 60)
app.logger.info("DEBUG: Vérification de la configuration OIDC")
app.logger.info("=" * 60)
app.logger.info(f"OIDCConfig.ENABLED: {OIDCConfig.ENABLED} (type: {type(OIDCConfig.ENABLED)})")
app.logger.info(f"OIDCConfig.ISSUER: '{OIDCConfig.ISSUER}' (type: {type(OIDCConfig.ISSUER)})")
app.logger.info(f"OIDCConfig.CLIENT_ID: '{OIDCConfig.CLIENT_ID}' (type: {type(OIDCConfig.CLIENT_ID)})")
app.logger.info(f"OIDCConfig.CLIENT_SECRET: '{OIDCConfig.CLIENT_SECRET}' (type: {type(OIDCConfig.CLIENT_SECRET)})")
app.logger.info(f"OIDCConfig.REDIRECT_URI: '{OIDCConfig.REDIRECT_URI}' (type: {type(OIDCConfig.REDIRECT_URI)})")
app.logger.info(f"OIDCConfig.is_configured(): {OIDCConfig.is_configured()}")

# Vérifier les variables d'environnement brutes
import os
app.logger.info("=" * 60)
app.logger.info("DEBUG: Variables d'environnement brutes")
app.logger.info("=" * 60)
app.logger.info(f"os.environ.get('OIDC_ENABLED'): '{os.environ.get('OIDC_ENABLED')}'")
app.logger.info(f"os.environ.get('OIDC_ISSUER'): '{os.environ.get('OIDC_ISSUER')}'")
app.logger.info(f"os.environ.get('OIDC_CLIENT_ID'): '{os.environ.get('OIDC_CLIENT_ID')}'")
app.logger.info(f"os.environ.get('OIDC_CLIENT_SECRET'): '{os.environ.get('OIDC_CLIENT_SECRET')}'")
app.logger.info(f"os.environ.get('OIDC_REDIRECT_URI'): '{os.environ.get('OIDC_REDIRECT_URI')}'")
app.logger.info("=" * 60)

# Initialisation de l'authentification OIDC (optionnelle)
if OIDCConfig.ENABLED and OIDCConfig.is_configured():
    from app.auth.oidc_auth import oidc_auth
    oidc_auth.init_app(app)
    app.logger.info("Authentification OIDC activée")
    
    # Vérifier que le client OIDC est bien enregistré
    if oidc_auth.oidc_client:
        app.logger.info(f"Client OIDC enregistré avec succès: {oidc_auth.oidc_client.name}")
    else:
        app.logger.error("ERREUR: Client OIDC est None après initialisation!")
else:
    app.logger.warning(f"Authentification OIDC désactivée. ENABLED={OIDCConfig.ENABLED}, is_configured={OIDCConfig.is_configured()}")


# Initialiser le cache
init_cache(app)

# ============================================================================
