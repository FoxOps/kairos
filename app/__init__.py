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

# Initialisation de l'authentification OIDC (optionnelle)
from config_oidc import OIDCConfig

# Vérifier la configuration OIDC
app.logger.info(f"OIDC_ENABLED: {OIDCConfig.ENABLED}")
app.logger.info(f"OIDC_ISSUER: {OIDCConfig.ISSUER}")
app.logger.info(f"OIDC_CLIENT_ID: {OIDCConfig.CLIENT_ID}")
app.logger.info(f"OIDC_CLIENT_SECRET: {'***' if OIDCConfig.CLIENT_SECRET else 'None'}")
app.logger.info(f"OIDC_REDIRECT_URI: {OIDCConfig.REDIRECT_URI}")
app.logger.info(f"OIDC is_configured: {OIDCConfig.is_configured()}")

if OIDCConfig.ENABLED and OIDCConfig.is_configured():
    from app.auth.oidc_auth import oidc_auth
    oidc_auth.init_app(app)
    app.logger.info("Authentification OIDC activée")
else:
    app.logger.warning("Authentification OIDC désactivée ou mal configurée")


# Initialiser le cache
init_cache(app)

# ============================================================================
