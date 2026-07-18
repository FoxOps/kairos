"""
Base configuration for Kairos.

This module provides the base configuration class that can be extended
for different environments (development, production, testing).
"""

import json
import logging
import os
import secrets
from datetime import timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Utility functions for environment variables
# ---------------------------------------------------------------------------


def get_bool_from_env(env_var: str, default: bool = False) -> bool:
    """
    Convert an environment variable to a boolean.

    Accepts: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO

    Args:
        env_var: Environment variable name
        default: Default value if variable is not set

    Returns:
        Boolean value of the environment variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default

    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "y", "on"):
        return True
    elif value_lower in ("false", "0", "no", "n", "off"):
        return False
    else:
        if value_lower:
            logging.warning(
                f"Unrecognized value for {env_var}: '{value}'. Using default: {default}"
            )
        return default


def get_int_from_env(env_var: str, default: int = 0) -> int:
    """
    Convert an environment variable to an integer.

    Args:
        env_var: Environment variable name
        default: Default value if variable is not set

    Returns:
        Integer value of the environment variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default

    try:
        return int(value.strip())
    except ValueError:
        logging.warning(
            f"Non-integer value for {env_var}: '{value}'. Using default: {default}"
        )
        return default


def get_str_from_env(env_var: str, default: str = "") -> str:
    """
    Get a string environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if variable is not set

    Returns:
        String value of the environment variable
    """
    value = os.environ.get(env_var)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def get_json_from_env(env_var: str, default: Any | None = None) -> Any:
    """
    Convert an environment variable to a Python object via JSON.

    Args:
        env_var: Environment variable name
        default: Default value if variable is not set

    Returns:
        Python object decoded from JSON
    """
    value = os.environ.get(env_var)
    if value is None or value.strip() == "":
        return default

    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        logging.warning(f"Invalid JSON value for {env_var}: '{value}'. Using default")
        return default


# Bare mysql://, mariadb://, postgres:// and postgresql:// (no explicit
# +driver suffix - the format documented throughout this app's docs and
# .env.example) all default, in SQLAlchemy, to the "classic" DBAPI driver
# for that dialect: MySQLdb (mysqlclient) for mysql/mariadb, psycopg2 for
# postgres/postgresql. Neither is installed in this project on purpose -
# requirements.txt ships PyMySQL and psycopg[binary] (psycopg 3) instead,
# specifically because they don't require compiled system libraries (see
# CLAUDE.md "Configuration: two parallel systems"). Left unrewritten, a
# bare DATABASE_URL=mysql://... or postgresql://... fails at engine
# creation with ModuleNotFoundError even though a perfectly good driver
# IS installed - confirmed by direct testing (create_engine() against
# each bare prefix), not assumed from SQLAlchemy's docs alone.
_DATABASE_URI_DRIVER_REWRITES = {
    "mysql": "mysql+pymysql://",
    "mariadb": "mariadb+pymysql://",
    "postgres": "postgresql+psycopg://",
    "postgresql": "postgresql+psycopg://",
}


def normalize_database_uri(database_uri: str) -> str:
    """
    Rewrites a bare mysql://, mariadb://, postgres:// or postgresql://
    prefix to the pure-Python/modern driver this app actually ships (see
    _DATABASE_URI_DRIVER_REWRITES above). An admin who already specifies
    an explicit +driver suffix (e.g. postgresql+psycopg2://, for a
    deployment that installed its own driver) is always left untouched -
    only a bare scheme with no "+" is rewritten.
    """
    scheme = database_uri.split("://", 1)[0] if "://" in database_uri else ""
    rewritten_prefix = _DATABASE_URI_DRIVER_REWRITES.get(scheme)
    if rewritten_prefix is None:
        return database_uri
    return rewritten_prefix + database_uri.split("://", 1)[1]


# ---------------------------------------------------------------------------
# Base Configuration Class
# ---------------------------------------------------------------------------


class Config:
    """
    Base configuration class for Kairos.

    This class contains default configuration values that can be overridden
    by environment-specific configuration classes.

    All configuration values can be set via environment variables.
    """

    # Flask Configuration
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    # Database Configuration
    SQLALCHEMY_DATABASE_URI: str = normalize_database_uri(
        os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = get_bool_from_env(
        "SQLALCHEMY_TRACK_MODIFICATIONS", False
    )

    # Flask Server Configuration. Binding to all interfaces is
    # intentional, not an oversight: the app always runs inside a
    # container (Docker) or behind a reverse proxy in production - it
    # must accept connections forwarded from outside its own network
    # namespace, which a 127.0.0.1 default would silently break.
    # Network-level exposure is controlled by the deployment (Docker
    # port mapping, reverse proxy, firewall), not by this app.
    HOST: str = os.environ.get("FLASK_HOST") or "0.0.0.0"  # nosec B104
    PORT: int = int(os.environ.get("FLASK_PORT") or 5000)

    # Public URL of the app behind a reverse proxy (e.g. https://schedule.example.com/)
    # Optional: acts as a fallback when request.host_url doesn't reflect
    # the right domain (proxy not forwarding X-Forwarded-Host). See
    # app/__init__.py's inject_public_base_url and the
    # _ics_export_buttons.html / auth/ics_token.html templates.
    # Fallback only when no DB-stored Setting exists - admin-editable at
    # /admin/settings without redeploy, see
    # app/services/settings_service.py::SettingsService.get_public_base_url().
    PUBLIC_BASE_URL: str | None = os.environ.get("PUBLIC_BASE_URL") or None

    # Debug Mode (should be False in production)
    DEBUG: bool = get_bool_from_env("FLASK_DEBUG", False)

    # Testing Configuration
    TESTING: bool = get_bool_from_env("FLASK_TESTING", False)

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = get_bool_from_env("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_DEFAULT: str = (
        os.environ.get("RATE_LIMIT_DEFAULT") or "200 per day, 50 per hour"
    )

    # Session Configuration
    SESSION_COOKIE_SECURE: bool = get_bool_from_env("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY: bool = get_bool_from_env("SESSION_COOKIE_HTTPONLY", True)
    SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE") or "Lax"
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        days=get_int_from_env("PERMANENT_SESSION_LIFETIME_DAYS", 30)
    )

    # Flask-Login Configuration
    LOGIN_DISABLED: bool = get_bool_from_env("LOGIN_DISABLED", False)
    REMEMBER_COOKIE_DURATION: int = get_int_from_env("REMEMBER_COOKIE_DURATION", 86400)
    SESSION_PROTECTION: str = os.environ.get("SESSION_PROTECTION") or "strong"

    # Security Configuration
    SECURITY_PASSWORD_SALT: str = os.environ.get(
        "SECURITY_PASSWORD_SALT"
    ) or secrets.token_urlsafe(16)

    # Talisman (HTTP security headers). force_https redirects to https://
    # on every request: only enable behind a reverse proxy that
    # terminates TLS (otherwise it loops on a redirect that serves no
    # purpose).
    TALISMAN_FORCE_HTTPS: bool = get_bool_from_env("TALISMAN_FORCE_HTTPS", False)
    TALISMAN_STRICT_TRANSPORT_SECURITY: bool = get_bool_from_env(
        "TALISMAN_STRICT_TRANSPORT_SECURITY", False
    )

    # Pagination Configuration
    # Fallback only when no DB-stored Setting exists - see
    # app/services/settings_service.py::SettingsService.get_items_per_page()/
    # get_max_per_page().
    ITEMS_PER_PAGE: int = get_int_from_env("ITEMS_PER_PAGE", 20)
    MAX_PER_PAGE: int = get_int_from_env("MAX_PER_PAGE", 100)

    # i18n (Flask-Babel). BABEL_DEFAULT_LOCALE is a defensive fallback,
    # never actually exercised in practice: app/__init__.py's get_locale()
    # always returns a value of its own (falls back to
    # SettingsService.FALLBACK_DEFAULT_LANGUAGE = "fr" when nothing else
    # applies). BABEL_TRANSLATION_DIRECTORIES matches Flask-Babel's own
    # default already, spelled out explicitly for discoverability.
    BABEL_DEFAULT_LOCALE: str = "fr"
    BABEL_TRANSLATION_DIRECTORIES: str = "translations"

    # Prometheus metrics (app/utils/prometheus_metrics.py, /metrics
    # endpoint). Bug found during the v1.0 bug hunt: this key was never
    # actually wired here, so app/__init__.py's
    # `app.config.get("PROMETHEUS_ENABLED", False)` check could never be
    # True from an env var in a real deployment - the feature was
    # structurally unreachable regardless of what an admin set. Masked in
    # tests because tests/integration/test_prometheus_metrics.py forces
    # app.config["PROMETHEUS_ENABLED"] = True directly and calls
    # init_prometheus() manually, bypassing this wiring entirely.
    PROMETHEUS_ENABLED: bool = get_bool_from_env("PROMETHEUS_ENABLED", False)

    # Logging Configuration
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL") or "INFO"
    LOG_FORMAT: str = (
        os.environ.get("LOG_FORMAT")
        or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Custom SQLAlchemy Engine Options. Must stay UPPERCASE: Config.from_object()
    # (this class's own utility method below) and Flask's app.config.from_object()
    # (app/__init__.py) both only copy attributes where key.isupper() - a
    # lowercase name here would silently never reach app.config, exactly the bug
    # this attribute previously had (confirmed dead: SQLALCHEMY_ENGINE_OPTIONS was
    # documented in Docs/reference/ENVIRONMENT_VARIABLES.md but had zero effect).
    SQLALCHEMY_ENGINE_OPTIONS: dict[str, Any] = (
        get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS") or {}
    )

    # ---------------------------------------------------------------------------
    # Configuration Validation
    # ---------------------------------------------------------------------------

    @staticmethod
    def validate() -> bool:
        """
        Validate the configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        # Check required configurations
        if not Config.SECRET_KEY:
            logging.error("SECRET_KEY is not set!")
            return False

        if not Config.SQLALCHEMY_DATABASE_URI:
            logging.error("SQLALCHEMY_DATABASE_URI is not set!")
            return False

        return True

    # ---------------------------------------------------------------------------
    # Utility Methods
    # ---------------------------------------------------------------------------

    @classmethod
    def from_object(cls, obj: Any) -> None:
        """
        Update configuration from another object.

        Args:
            obj: Object with configuration attributes
        """
        for key in dir(obj):
            if key.isupper() and not key.startswith("_"):
                setattr(cls, key, getattr(obj, key))

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary of configuration values
        """
        return {
            key: value
            for key, value in cls.__dict__.items()
            if key.isupper() and not key.startswith("_")
        }
