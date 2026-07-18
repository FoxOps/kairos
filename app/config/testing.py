"""
Testing configuration for Kairos.

This configuration is used during testing and includes:
- In-memory database
- Disabled rate limiting
- Fast settings for tests
"""

import os

from app.config.base import Config, normalize_database_uri


class TestingConfig(Config):
    """
    Testing-specific configuration.

    Extends the base Config class with testing-specific settings.
    """

    # Testing mode
    TESTING: bool = True
    DEBUG: bool = False
    DEVELOPMENT: bool = False

    # In-memory database for tests - normalize_database_uri() rewrites a
    # bare postgresql://mysql://mariadb:// to the driver this app actually
    # ships, in case TEST_DATABASE_URL points at a real external server
    # rather than the sqlite in-memory default (see app/config/base.py).
    SQLALCHEMY_DATABASE_URI: str = normalize_database_uri(
        os.environ.get("TEST_DATABASE_URL") or "sqlite:///:memory:"
    )
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_RECORD_QUERIES: bool = False

    # Disable rate limiting for tests
    RATE_LIMIT_ENABLED: bool = False

    # Disable CSRF for tests (can be enabled if needed)
    WTF_CSRF_ENABLED: bool = False

    # Logging configuration
    LOG_LEVEL: str = "WARNING"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Session settings for tests
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # Security settings for tests
    SECRET_KEY: str = "test-secret-key"  # noqa: S105 - test-only, not a real secret
    SECURITY_PASSWORD_SALT: str = (
        "test-salt"  # noqa: S105 - test-only, not a real secret
    )

    # Pagination settings for tests
    ITEMS_PER_PAGE: int = 10
    MAX_PER_PAGE: int = 50

    # Disable templates auto-reload for tests
    TEMPLATES_AUTO_RELOAD: bool = False

    # Disable Talisman for tests (to avoid HTTPS redirects in test environment)
    TALISMAN_FORCE_HTTPS: bool = False
    TALISMAN_STRICT_TRANSPORT_SECURITY: bool = False
