"""
Production configuration for Leviia Schedule.

This configuration is used in production and includes:
- Debug mode disabled
- Secure settings
- Performance optimizations
"""

import os
from datetime import timedelta

from app.config.base import Config, get_bool_from_env, normalize_database_uri


class ProductionConfig(Config):
    """
    Production-specific configuration.

    Extends the base Config class with production-specific settings.
    """

    # Disable debug mode
    DEBUG: bool = False
    TESTING: bool = False
    DEVELOPMENT: bool = False

    # Production database (should be set via DATABASE_URL) - normalize_database_uri()
    # rewrites a bare postgresql://mysql://mariadb:// to the driver this app
    # actually ships (psycopg 3/PyMySQL), see app/config/base.py.
    SQLALCHEMY_DATABASE_URI: str = normalize_database_uri(
        os.environ.get("DATABASE_URL") or "postgresql:///leviia"
    )
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_RECORD_QUERIES: bool = False

    # Security settings for production
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # Rate limiting (strict in production)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "200 per day, 50 per hour"

    # Logging configuration
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL") or "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Production-specific settings
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=1)

    # Security headers
    TALISMAN_FORCE_HTTPS: bool = get_bool_from_env("TALISMAN_FORCE_HTTPS", True)
    TALISMAN_STRICT_TRANSPORT_SECURITY: bool = get_bool_from_env(
        "TALISMAN_STRICT_TRANSPORT_SECURITY", True
    )

    # CORS settings
    CORS_ORIGINS: list = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Compression settings
    COMPRESS_REGISTER: bool = get_bool_from_env("COMPRESS_REGISTER", True)
    COMPRESS_MIMETYPES: list = [
        "text/html",
        "text/css",
        "text/xml",
        "application/json",
        "application/javascript",
    ]
