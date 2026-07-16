"""
Flask application initialization for Leviia Schedule.

This version uses a modular approach with a factory function to create
and configure the application. The global _app variable is kept for
backward compatibility with existing code.

New structure:
- Modular configuration in app/config/
- Models split out in app/models/
- Services in app/services/
- Repositories in app/repositories/
- Routes organized into blueprints in app/routes/
"""

import os
import warnings

from flask import Flask, render_template
from flask_babel import Babel
from flask_compress import Compress
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LOGIN_MESSAGE, LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

# Flask-Limiter warns on every init without a shared backend (redis/memcached).
# Deliberate choice: in-memory storage (single process).
warnings.filterwarnings(
    "ignore",
    message="Using the in-memory storage",
    category=UserWarning,
    module="flask_limiter",
)

# ---------------------------------------------------------------------------
# Extension initialization
# ---------------------------------------------------------------------------

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_message_category = "danger"
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
compress = Compress()
babel = Babel()


def get_locale() -> str:
    """Resolution order: the authenticated user's own language
    preference, else the organization's default_language Setting.
    Deliberately no Accept-Language sniffing - org/user settings are
    the single source of truth here, exactly like effective_timezone()
    never consults browser-provided data. This also keeps rendering
    deterministic for anonymous pages (login, error pages) regardless
    of visitor - important for test stability (see
    SettingsService.FALLBACK_DEFAULT_LANGUAGE).

    This is Flask-Babel's locale_selector, invoked by gettext()/_() on
    every call - including from service-layer code that may run with
    only an app_context() and no real HTTP request (e.g. called
    directly in unit tests, or in principle any future non-request
    caller). current_user requires a request context to resolve;
    without one it's None rather than flask_login's usual
    AnonymousUserMixin, so check has_request_context() first instead of
    letting that raise AttributeError."""
    from flask import has_request_context
    from flask_login import current_user

    if has_request_context() and current_user.is_authenticated:
        return current_user.effective_language()

    from app.services import SettingsService

    return SettingsService.get_default_language()


# Content-Security-Policy applied by Talisman - see the comment in
# create_app() for details on each directive. Exposed as a module-level
# constant (rather than inline) so tests can check the actual policy
# without duplicating it.
CDNJS_HOST = "https://cdnjs.cloudflare.com"
# FullCalendar specifically: cdnjs doesn't host the locale files for any
# tested version of this package (consistent 404s) - see the comment at
# the top of app/static/js/calendar/fullcalendar-config.js for the full
# story - the one exception to "everything via cdnjs" in this policy.
JSDELIVR_HOST = "https://cdn.jsdelivr.net"

CSP_POLICY = {
    "default-src": "'self'",
    "object-src": "'none'",
    # cdnjs.cloudflare.com: Font Awesome, daisyUI, tailwindcss-browser
    # (Tailwind CSS 4's browser-JIT compiler) are loaded from this CDN
    # rather than vendored locally.
    # cdn.jsdelivr.net: FullCalendar only (see comment above).
    "script-src": f"'self' {CDNJS_HOST} {JSDELIVR_HOST}",
    "script-src-attr": "'unsafe-inline'",
    "style-src": f"'self' 'unsafe-inline' {CDNJS_HOST}",
    # FullCalendar bundles its icon font (calendar prev/next arrows) as a
    # @font-face data: URI in its own CSS (bundled into the vendor JS) -
    # without font-src, default-src 'self' blocks the data: URI and the
    # calendar's navigation icons stay invisible (found by inspecting a
    # real browser's console, not just the rendered HTML).
    # cdnjs.cloudflare.com: Font Awesome fonts (.woff2 webfonts).
    "font-src": f"'self' data: {CDNJS_HOST}",
    # daisyUI uses a data: SVG (noise/texture for the "depth" effect on
    # some components) as a CSS background - found via a real browser's
    # console (like font-src above), not in the rendered HTML.
    "img-src": "'self' data:",
}

# Variable kept for backward compatibility with existing code
_app = None

# Imported after `db` is defined: app.utils.helpers does `from app import
# db` and would cause a circular import if this module were imported earlier.
from app.utils.logging.logger import (  # noqa: E402
    SensitiveDataFilter,
    get_error_template_data,
    get_logger,
    log_audit_action,
    log_http_error,
)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


def handle_database_error(error):
    """Handler for database errors (SQLite/SQLAlchemy)."""
    log_http_error(500, str(error))
    return render_template("500.html"), 500


def handle_value_error(error):
    """Handler for ValueError not caught by the routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


def handle_type_error(error):
    """Handler for TypeError not caught by the routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


def handle_exception(error):
    """Generic handler for uncaught exceptions."""
    log_http_error(500, str(error))
    return render_template("500.html"), 500


def _make_http_error_handler(code: int):
    def _handler(error):
        log_http_error(code, getattr(error, "description", str(error)))
        return render_template(f"{code}.html"), code

    return _handler


def create_app(config_object: str | None = None):
    """
    Factory function to create and configure the Flask application.

    This function creates a new application instance with the given
    configuration.

    Args:
        config_object: Path to the configuration class to use.
                      Defaults to 'app.config.Config'.
                      Examples: 'app.config.DevelopmentConfig', 'app.config.ProductionConfig'

    Returns:
        Configured Flask application instance
    """
    global _app

    # Create the Flask application
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    # Load the configuration
    if config_object is None:
        config_object = "app.config.Config"

    # Dynamically import the configuration class
    module_path, class_name = config_object.rsplit(".", 1)
    config_module = __import__(module_path, fromlist=[class_name])
    config_class = getattr(config_module, class_name)

    app.config.from_object(config_class)

    # Trust the X-Forwarded-* headers from a single reverse proxy
    # (nginx/caddy in prod). Without this, Talisman/force_https never
    # sees a request as "secure" even when TLS is terminated upstream,
    # and loops on https redirects. With no proxy in front of the app
    # (dev/test), these headers are simply never present and this
    # middleware changes nothing.
    # Standard Werkzeug pattern for applying a WSGI middleware - mypy
    # confuses the instance attribute with the inherited
    # Flask.wsgi_app method (100% valid and documented at runtime).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    # Configure logging via a dedicated module
    from app.utils.logging import configure_logging

    configure_logging(app)

    # Initialize the extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    # Flask-Babel auto-injects _/gettext/ngettext as Jinja globals (and
    # the {% trans %} extension), but NOT get_locale() itself - register
    # it explicitly so base.html's <html lang="{{ get_locale() }}">
    # works.
    app.jinja_env.globals["get_locale"] = get_locale

    # Configure rate limiting if enabled
    if app.config.get("RATE_LIMIT_ENABLED", True):
        limiter.enabled = True
        app.config["RATELIMIT_DEFAULT"] = app.config.get(
            "RATE_LIMIT_DEFAULT", "200 per day, 50 per hour"
        )
    else:
        limiter.enabled = False

    # OIDC configuration - load before configuring login_manager
    from config_oidc import OIDCConfig

    OIDCConfig.load_config()

    # User loader configuration
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Always (re)initialize OIDC, even when disabled/unconfigured: oidc_auth
    # is a module-level singleton shared across every app instance built by
    # create_app() in this process (see the comment on
    # OIDCAuthLib.init_app) - it must be reset here regardless, or a
    # previous app's real OIDC discovery could leak into this one.
    from app.auth.oidc_auth import oidc_auth

    oidc_auth.init_app(app)

    # Initialize Talisman for HTTP security (headers + CSP).
    # Always active: force_https only controls the HTTP->HTTPS redirect
    # and HSTS, not the other headers (CSP, X-Content-Type-Options,
    # X-Frame-Options...) - before this fix, everything was gated behind
    # TALISMAN_FORCE_HTTPS, so a deployment with TLS terminated upstream
    # (reverse proxy) and TALISMAN_FORCE_HTTPS=false had NO security
    # headers at all.
    #
    # CSP: script-src 'self' blocks any injected <script> (the most
    # dangerous XSS vector) - the app's scripts all live in external
    # files served locally. script-src-attr allows 'unsafe-inline'
    # specifically for the onclick="" attributes still used in some
    # templates (static content written by developers, never user data)
    # - script-src-attr is a directive distinct from script-src since
    # CSP level 3, nonces don't cover event attributes. style-src allows
    # 'unsafe-inline' for a single dynamic style (chart bar width) in
    # dashboard.html - injected CSS is a far less dangerous vector than
    # injected script.
    if not app.config.get("TESTING", False):
        Talisman(
            app,
            force_https=app.config.get("TALISMAN_FORCE_HTTPS", True),
            strict_transport_security=app.config.get(
                "TALISMAN_STRICT_TRANSPORT_SECURITY", True
            ),
            content_security_policy=CSP_POLICY,
        )

    # Gzip/Brotli response compression (flask-compress was a declared
    # dependency with its config in ProductionConfig but never
    # initialized: Compress(app) was called nowhere, so
    # COMPRESS_REGISTER/COMPRESS_MIMETYPES did nothing). Disabled in
    # tests because the test client doesn't decode Content-Encoding:
    # assertions on resp.data (text) would break on gzipped responses.
    if not app.config.get("TESTING", False):
        compress.init_app(app)

    # Initialize CORS
    CORS(app)

    # Import and register the blueprints
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.export import export_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(export_bp)

    # Configure login_manager.login_view AFTER registering the blueprints
    # This lets Flask-Login find the auth.login route
    if (
        OIDCConfig.ENABLED
        and OIDCConfig.is_configured()
        and OIDCConfig.DISABLE_BASIC_AUTH
    ):
        login_manager.login_view = "auth.oidc_login"
        # auth.oidc_login never renders a template: it redirects
        # straight to the OIDC provider. Flask-Login's default "please
        # log in" flash (triggered by @login_required before this
        # redirect) therefore never gets a chance to display on its
        # own - it rides along through the whole round trip to the IdP
        # and ends up stuck next to the "OIDC login successful!" flash
        # on the first page rendered afterward (both shown at once).
        # Useless in this mode: disabled. Stays active in classic
        # auth.login mode, where it displays normally on the login form.
        login_manager.login_message = None
    else:
        login_manager.login_view = "auth.login"
        # login_manager is a module-level singleton reused by every
        # create_app() call in the same process (tests included) -
        # explicitly restore Flask-Login's default, otherwise an
        # earlier call in OIDC mode (branch above) leaves login_message
        # at None here too.
        login_manager.login_message = LOGIN_MESSAGE

    # Store the global instance for backward compatibility
    _app = app

    # Health endpoint configuration for Kubernetes/monitoring
    from app.utils.health import register_health_endpoints

    register_health_endpoints(app)

    # App version available in all templates (footer, etc.) - same
    # source as the /version endpoint (APP_VERSION_DEFAULT imported from
    # app/utils/health.py, not redefined here) to avoid two values
    # drifting apart (already happened twice: hardcoded "0.5", then
    # "0.6.0" left stale here after a bump made only in health.py).
    from app.utils.health import APP_VERSION_DEFAULT

    @app.context_processor
    def inject_app_version():
        return {"app_version": os.environ.get("APP_VERSION", APP_VERSION_DEFAULT)}

    # Explicit fallback for absolute links (ICS export) when the reverse
    # proxy doesn't correctly forward X-Forwarded-Host to ProxyFix above
    # - otherwise request.host_url exposes the backend's internal
    # IP/hostname instead of the public domain. Admin-editable at
    # /admin/settings (falls back to the PUBLIC_BASE_URL env var when no
    # DB override exists - see SettingsService.get_public_base_url()).
    @app.context_processor
    def inject_public_base_url():
        from app.services import SettingsService

        base_url = SettingsService.get_public_base_url()
        return {"public_base_url": base_url.rstrip("/") if base_url else None}

    # Server-translated strings for the handful of hardcoded-in-JS
    # user-facing texts - see app/utils/helpers/js_translations.py and
    # base.html's #i18n-strings script tag.
    @app.context_processor
    def inject_js_translations():
        from app.utils.helpers.js_translations import get_js_translations

        return {"js_translations": get_js_translations()}

    # Unread notifications badge in the sidebar (see "Notifications" in
    # nav_links, base.html) - lightweight query (COUNT), acceptable on
    # every page view given this app's scale.
    #
    # has_request_context() is necessary: the weekly reminder emails
    # (NotificationService, scripts/send_*_notifications.py) call
    # render_template() from a plain app_context() (cron, no HTTP
    # request) - current_user resolves to None there (not an
    # exception), so current_user.is_authenticated used to crash
    # ("'NoneType' object has no attribute 'is_authenticated'") and
    # broke sending ALL reminder emails as soon as a user had a
    # shift/on-call.
    @app.context_processor
    def inject_unread_notifications_count():
        from flask import has_request_context
        from flask_login import current_user

        if not has_request_context() or not current_user.is_authenticated:
            return {"unread_notifications_count": 0}
        from app.services import AppNotificationService

        return {
            "unread_notifications_count": AppNotificationService.count_unread(
                current_user.id
            )
        }

    # Jinja filter: dates in French (%a depends on the OS locale, never
    # reliable in a WSGI app - see format_date_fr). The per-shift-type
    # color (dashboard) is computed per view via
    # build_shift_type_color_map (rank among the displayed types, not a
    # filter by ID - see app/routes/dashboard_routes.py): a plain `id %
    # palette size` makes two types collide as soon as their IDs differ
    # by a multiple of the palette size.
    from app.utils.helpers import format_date_fr

    app.jinja_env.filters["date_fr"] = format_date_fr

    # Prometheus metrics configuration if enabled
    if app.config.get("PROMETHEUS_ENABLED", False):
        from app.utils.prometheus_metrics import init_prometheus

        init_prometheus(app)

    # HTTP error handlers (custom pages + logging)
    for error_code in (400, 401, 403, 404, 405, 500, 502, 503, 504):
        app.register_error_handler(error_code, _make_http_error_handler(error_code))

    # Application exception handlers
    app.register_error_handler(ValueError, handle_value_error)
    app.register_error_handler(TypeError, handle_type_error)

    return app


# ---------------------------------------------------------------------------
# Default global instance (for backward compatibility)
# ---------------------------------------------------------------------------
# Create the global instance to maintain backward compatibility
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
