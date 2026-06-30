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

# ============================================================================
# CONFIGURATION DU LOGGING - FORCER L'AFFICHAGE EN CONSOLE
# ============================================================================
# Configurer le logger racine pour afficher les logs en console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # ✅ Forcer l'affichage en console
    ]
)

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
app.logger.setLevel(logging.INFO)  # ✅ Forcer le niveau INFO
print("=" * 60)  # ✅ Utiliser print pour être sûr que ça s'affiche
print("DEBUG: Vérification de la configuration OIDC")
print("=" * 60)
print(f"OIDCConfig.ENABLED: {OIDCConfig.ENABLED} (type: {type(OIDCConfig.ENABLED)})")
print(f"OIDCConfig.ISSUER: '{OIDCConfig.ISSUER}' (type: {type(OIDCConfig.ISSUER)})")
print(f"OIDCConfig.CLIENT_ID: '{OIDCConfig.CLIENT_ID}' (type: {type(OIDCConfig.CLIENT_ID)})")
print(f"OIDCConfig.CLIENT_SECRET: '{OIDCConfig.CLIENT_SECRET}' (type: {type(OIDCConfig.CLIENT_SECRET)})")
print(f"OIDCConfig.REDIRECT_URI: '{OIDCConfig.REDIRECT_URI}' (type: {type(OIDCConfig.REDIRECT_URI)})")
print(f"OIDCConfig.is_configured(): {OIDCConfig.is_configured()}")
print("=" * 60)

# Initialisation de l'authentification OIDC (optionnelle)
if OIDCConfig.ENABLED and OIDCConfig.is_configured():
    from app.auth.oidc_auth import oidc_auth
    oidc_auth.init_app(app)
    print(f"✅ Authentification OIDC activée")
    
    # Vérifier que le client OIDC est bien enregistré
    if oidc_auth.oidc_client:
        print(f"✅ Client OIDC enregistré avec succès: {oidc_auth.oidc_client.name}")
    else:
        print("❌ ERREUR: Client OIDC est None après initialisation!")
else:
    print(f"⚠️  Authentification OIDC désactivée. ENABLED={OIDCConfig.ENABLED}, is_configured={OIDCConfig.is_configured()}")


# Initialiser le cache
init_cache(app)

# ============================================================================
