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
import warnings
from typing import Optional

from flask import Flask, render_template
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_cors import CORS
from flask_wtf import CSRFProtect
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

# Flask-Limiter avertit à chaque init sans backend partagé (redis/memcached).
# Choix assumé : stockage en mémoire (mono-process), cf. discussion équipe.
warnings.filterwarnings(
    "ignore",
    message="Using the in-memory storage",
    category=UserWarning,
    module="flask_limiter",
)

# ---------------------------------------------------------------------------
# Initialisation des extensions
# ---------------------------------------------------------------------------

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_message_category = "danger"
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
compress = Compress()

# Policy Content-Security-Policy appliquée par Talisman - voir le
# commentaire dans create_app() pour le détail de chaque directive.
# Exposée en constante de module (plutôt qu'inline) pour que les tests
# puissent vérifier la policy réelle sans la dupliquer.
CSP_POLICY = {
    "default-src": "'self'",
    "object-src": "'none'",
    "script-src": "'self'",
    "script-src-attr": "'unsafe-inline'",
    "style-src": "'self' 'unsafe-inline'",
}

# Variable pour maintenir la compatibilité avec le code existant
_app = None

# Importé après la définition de `db` : app.utils.helpers fait `from app import db`
# et créerait un import circulaire si ce module était importé plus tôt.
from app.utils.logging.logger import (
    get_error_template_data,
    log_audit_action,
    log_http_error,
    get_logger,
    SensitiveDataFilter,
)

# ---------------------------------------------------------------------------
# Gestionnaires d'erreurs
# ---------------------------------------------------------------------------


def handle_database_error(error):
    """Gestionnaire pour les erreurs de base de données (SQLite/SQLAlchemy)."""
    log_http_error(500, str(error))
    return render_template("500.html"), 500


def handle_value_error(error):
    """Gestionnaire pour les ValueError non interceptées par les routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


def handle_type_error(error):
    """Gestionnaire pour les TypeError non interceptées par les routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


def handle_exception(error):
    """Gestionnaire générique pour les exceptions non interceptées."""
    log_http_error(500, str(error))
    return render_template("500.html"), 500


def _make_http_error_handler(code: int):
    def _handler(error):
        log_http_error(code, getattr(error, "description", str(error)))
        return render_template(f"{code}.html"), code

    return _handler


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
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    # Charger la configuration
    if config_object is None:
        config_object = "app.config.Config"

    # Importer dynamiquement la classe de configuration
    module_path, class_name = config_object.rsplit(".", 1)
    config_module = __import__(module_path, fromlist=[class_name])
    config_class = getattr(config_module, class_name)

    app.config.from_object(config_class)

    # Faire confiance aux en-têtes X-Forwarded-* d'un unique reverse proxy
    # (nginx/caddy en prod). Sans ça, Talisman/force_https ne voit jamais
    # une requête comme "sécurisée" même quand le TLS est terminé en amont,
    # et boucle sur des redirections https. Sans proxy devant l'app
    # (dev/test), ces en-têtes ne sont simplement jamais présents et ce
    # middleware ne change rien.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Configurer le logging via un module dédié
    from app.utils.logging import configure_logging

    configure_logging(app)

    # Initialiser les extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # Configurer le rate limiting si activé
    if app.config.get("RATE_LIMIT_ENABLED", True):
        limiter.enabled = True
        app.config["RATELIMIT_DEFAULT"] = app.config.get(
            "RATE_LIMIT_DEFAULT", "200 per day, 50 per hour"
        )
    else:
        limiter.enabled = False

    # Configuration OIDC - charger avant de configurer login_manager
    from config_oidc import OIDCConfig

    OIDCConfig.load_config()

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

    # Initialiser Talisman pour la sécurité HTTP (en-têtes + CSP).
    # Toujours actif : force_https ne contrôle que la redirection HTTP->HTTPS
    # et HSTS, pas les autres en-têtes (CSP, X-Content-Type-Options,
    # X-Frame-Options...) - avant ce correctif, tout était gated derrière
    # TALISMAN_FORCE_HTTPS, donc un déploiement avec TLS terminé en amont
    # (reverse proxy) et TALISMAN_FORCE_HTTPS=false n'avait AUCUN en-tête
    # de sécurité du tout.
    #
    # CSP : script-src 'self' bloque tout <script> injecté (le vecteur XSS
    # le plus dangereux) - les scripts de l'app sont tous dans des fichiers
    # externes servis localement (Phase 3/6). script-src-attr autorise
    # 'unsafe-inline' spécifiquement pour les attributs onclick="" encore
    # utilisés dans certains templates (contenu statique écrit par les
    # développeurs, jamais de données utilisateur) - script-src-attr est une
    # directive distincte de script-src depuis CSP niveau 3, les nonces ne
    # couvrent pas les attributs d'événements. style-src autorise
    # 'unsafe-inline' pour un seul style dynamique (largeur de barre de
    # graphique) dans dashboard.html - CSS injecté est un vecteur bien
    # moins dangereux qu'un script injecté.
    if not app.config.get("TESTING", False):
        Talisman(
            app,
            force_https=app.config.get("TALISMAN_FORCE_HTTPS", True),
            strict_transport_security=app.config.get(
                "TALISMAN_STRICT_TRANSPORT_SECURITY", True
            ),
            content_security_policy=CSP_POLICY,
        )

    # Compression Gzip/Brotli des réponses (flask-compress était une
    # dépendance déclarée avec sa config dans ProductionConfig mais jamais
    # initialisée : Compress(app) n'était appelé nulle part, donc
    # COMPRESS_REGISTER/COMPRESS_MIMETYPES ne faisaient rien). Désactivée en
    # test car le client de test ne décode pas Content-Encoding : les
    # assertions sur resp.data (texte) casseraient sur des réponses gzippées.
    if not app.config.get("TESTING", False):
        compress.init_app(app)

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

    # Configurer login_manager.login_view APRES l'enregistrement des blueprints
    # Cela permet à Flask-Login de trouver la route auth.login
    if (
        OIDCConfig.ENABLED
        and OIDCConfig.is_configured()
        and OIDCConfig.DISABLE_BASIC_AUTH
    ):
        login_manager.login_view = "auth.oidc_login"
    else:
        login_manager.login_view = "auth.login"

    # Stocker l'instance globale pour la compatibilité
    _app = app

    # Configuration des endpoints de santé pour Kubernetes/Monitoring
    from app.utils.health import register_health_endpoints

    register_health_endpoints(app)

    # Configuration des métriques Prometheus si activé
    if app.config.get("PROMETHEUS_ENABLED", False):
        from app.utils.prometheus_metrics import init_prometheus

        init_prometheus(app)

    # Gestionnaires d'erreurs HTTP (pages personnalisées + logging)
    for error_code in (400, 401, 403, 404, 405, 500, 502, 503, 504):
        app.register_error_handler(error_code, _make_http_error_handler(error_code))

    # Gestionnaires d'exceptions applicatives
    app.register_error_handler(ValueError, handle_value_error)
    app.register_error_handler(TypeError, handle_type_error)

    return app


# ---------------------------------------------------------------------------
# Instance globale par défaut (pour la compatibilité ascendante)
# ---------------------------------------------------------------------------
# Créer l'instance globale pour maintenir la compatibilité
app = create_app()

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
__all__ = [
    "app",
    "create_app",
    "db",
    "login_manager",
    "limiter",
    "get_logger",
    "get_error_template_data",
    "log_audit_action",
    "log_http_error",
    "SensitiveDataFilter",
    "handle_database_error",
    "handle_value_error",
    "handle_type_error",
    "handle_exception",
]
