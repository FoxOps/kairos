"""
Base configuration for Leviia Schedule.

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


def get_database_type(database_uri: str | None = None) -> str:
    """
    Detect the database type from the URI.

    Args:
        database_uri: Database URI (default: DATABASE_URL environment variable)

    Returns:
        Database type: 'postgresql', 'mysql', 'sqlite'
    """
    if database_uri is None:
        database_uri = os.environ.get("DATABASE_URL") or "sqlite:///app.db"

    if database_uri.startswith("postgresql://") or database_uri.startswith(
        "postgres://"
    ):
        return "postgresql"
    elif database_uri.startswith("mysql://") or database_uri.startswith("mariadb://"):
        return "mysql"
    elif database_uri.startswith("sqlite://"):
        return "sqlite"
    else:
        return "sqlite"


# ---------------------------------------------------------------------------
# Base Configuration Class
# ---------------------------------------------------------------------------


class Config:
    """
    Base configuration class for Leviia Schedule.

    This class contains default configuration values that can be overridden
    by environment-specific configuration classes.

    All configuration values can be set via environment variables.
    """

    # Flask Configuration
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    # Database Configuration
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = get_bool_from_env(
        "SQLALCHEMY_TRACK_MODIFICATIONS", False
    )

    # Flask Server Configuration
    HOST: str = os.environ.get("FLASK_HOST") or "0.0.0.0"
    PORT: int = int(os.environ.get("FLASK_PORT") or 5000)

    # URL publique de l'app derrière un reverse proxy (ex: https://schedule.example.com/)
    # Optionnel : sert de repli quand request.host_url ne reflète pas le bon domaine
    # (proxy qui ne transmet pas X-Forwarded-Host). Voir app/__init__.py
    # inject_public_base_url et templates _ics_export_buttons.html / auth/ics_token.html.
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

    # Talisman (en-têtes de sécurité HTTP). force_https redirige vers https://
    # à chaque requête : à activer uniquement derrière un reverse proxy qui
    # termine le TLS (sinon boucle sur une redirection que rien ne sert).
    # Note: create_app() charge cette classe de base par défaut, quel que
    # soit FLASK_ENV - ces clés doivent donc être lues ici, pas seulement
    # dans ProductionConfig/TestingConfig, pour que la variable d'env ait un
    # effet réel en déploiement.
    TALISMAN_FORCE_HTTPS: bool = get_bool_from_env("TALISMAN_FORCE_HTTPS", False)
    TALISMAN_STRICT_TRANSPORT_SECURITY: bool = get_bool_from_env(
        "TALISMAN_STRICT_TRANSPORT_SECURITY", False
    )

    # Cache Configuration
    CACHE_TYPE: str = os.environ.get("CACHE_TYPE") or "simple"
    CACHE_DEFAULT_TIMEOUT: int = get_int_from_env("CACHE_DEFAULT_TIMEOUT", 300)
    CACHE_REDIS_URL: str = (
        os.environ.get("CACHE_REDIS_URL") or "redis://localhost:6379/0"
    )

    # Pagination Configuration
    ITEMS_PER_PAGE: int = get_int_from_env("ITEMS_PER_PAGE", 20)
    MAX_PER_PAGE: int = get_int_from_env("MAX_PER_PAGE", 100)

    # Logging Configuration
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL") or "INFO"
    LOG_FORMAT: str = (
        os.environ.get("LOG_FORMAT")
        or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Custom SQLAlchemy Engine Options
    custom_engine_options: dict[str, Any] = (
        get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS") or {}
    )

    # ---------------------------------------------------------------------------
    # Database Type Detection
    # ---------------------------------------------------------------------------

    @staticmethod
    def get_database_type(database_uri: str | None = None) -> str:
        """
        Detect the database type from the URI.

        Args:
            database_uri: Database URI (default: SQLALCHEMY_DATABASE_URI)

        Returns:
            Database type: 'postgresql', 'mysql', 'sqlite'
        """
        return get_database_type(database_uri or Config.SQLALCHEMY_DATABASE_URI)

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
