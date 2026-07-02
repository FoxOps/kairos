"""
Initialisation de l'application Flask pour Leviia Schedule.

Cette version utilise une approche modulaire avec une factory function
pour créer et configurer l'application. La variable globale _app
est conservée pour maintenir la compatibilité avec le code existant.

Nouvelle structure:
- Configuration modulaire dans app/config/
- Modèles séparés dans app/models/
- Services dans app/services/
- Repositories dans app/repositories/
- Routes organisées en blueprints dans app/routes/
"""

import logging
import os
import secrets
from typing import Optional

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
login_manager.login_message_category = "danger"
limiter = Limiter(key_func=get_remote_address)

# Variable pour maintenir la compatibilité avec le code existant
_app = None


def create_app(config_object: Optional[str] = None):
    """
    Factory function pour créer et configurer l'application Flask.
    
    Cette fonction crée une nouvelle instance de l'application avec la
    configuration spécifiée.
    
    Args:
        config_object: Chemin vers la classe de configuration à utiliser.
                      Par défaut, utilise 'app.config.Config'.
                      Exemples: 'app.config.DevelopmentConfig', 'app.config.ProductionConfig'
    
    Returns:
        Instance de l'application Flask configurée
    """
    global _app
    
    # Créer l'application Flask
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )
    
    # Charger la configuration
    if config_object is None:
        config_object = "app.config.Config"
    
    # Importer dynamiquement la classe de configuration
    module_path, class_name = config_object.rsplit('.', 1)
    config_module = __import__(module_path, fromlist=[class_name])
    config_class = getattr(config_module, class_name)
    
    app.config.from_object(config_class)
    
    # Configurer le logging via un module dédié
    from app.utils.logging import configure_logging
    configure_logging(app)
    
    # Initialiser les extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Configurer le rate limiting si activé
    if app.config.get('RATE_LIMIT_ENABLED', True):
        limiter.enabled = True
        app.config['RATELIMIT_DEFAULT'] = app.config.get('RATE_LIMIT_DEFAULT', '200 per day, 50 per hour')
    else:
        limiter.enabled = False
    
    # Configuration OIDC - charger avant de configurer login_manager
    from config_oidc import OIDCConfig
    OIDCConfig.load_config()
    
    # Configurer login_manager.login_view dynamiquement
    if OIDCConfig.ENABLED and OIDCConfig.is_configured() and OIDCConfig.DISABLE_BASIC_AUTH:
        login_manager.login_view = "auth.login"
    else:
        login_manager.login_view = "auth.login"
    
    # Configuration du User Loader
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialiser OIDC si configuré
    if OIDCConfig.ENABLED and OIDCConfig.is_configured():
        from app.auth.oidc_auth import oidc_auth
        oidc_auth.init_app(app)
    
    # Initialiser le cache
    from app.utils.cache import init_cache
    init_cache(app)
    
    # Initialiser Talisman pour la sécurité HTTP
    if app.config.get('TALISMAN_FORCE_HTTPS', True):
        Talisman(
            app,
            force_https=app.config.get('TALISMAN_FORCE_HTTPS', True),
            strict_transport_security=app.config.get('TALISMAN_STRICT_TRANSPORT_SECURITY', True)
        )
    
    # Initialiser CORS
    CORS(app)
    
    # Importer et enregistrer les blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.export import export_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(export_bp)
    
    # Stocker l'instance globale pour la compatibilité
    _app = app
    
    # Configuration des endpoints de santé pour Kubernetes/Monitoring
    from app.utils.health import register_health_endpoints
    register_health_endpoints(app)
    
    # Configuration des métriques Prometheus si activé
    if app.config.get('PROMETHEUS_ENABLED', False):
        from app.utils.prometheus_metrics import init_prometheus
        init_prometheus(app)
    
    return app


# ---------------------------------------------------------------------------
# Instance globale par défaut (pour la compatibilité ascendante)
# ---------------------------------------------------------------------------
# Créer l'instance globale pour maintenir la compatibilité
app = create_app()

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
__all__ = ['app', 'create_app', 'db', 'login_manager', 'limiter']
