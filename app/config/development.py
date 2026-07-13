"""
Development configuration for Leviia Schedule.

This configuration is used during development and includes:
- Debug mode enabled
- Less secure settings for easier development
- Detailed logging
"""

from app.config.base import Config, get_bool_from_env


class DevelopmentConfig(Config):
    """
    Development-specific configuration.

    Extends the base Config class with development-specific settings.
    """

    # Enable debug mode
    DEBUG: bool = True

    # Development-specific database (can be overridden by DATABASE_URL)
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///dev.db"
    SQLALCHEMY_ECHO: bool = get_bool_from_env("SQLALCHEMY_ECHO", True)

    # Security settings for development
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # Rate limiting (less strict in development)
    RATE_LIMIT_ENABLED: bool = get_bool_from_env("RATE_LIMIT_ENABLED", False)
    RATE_LIMIT_DEFAULT: str = "1000 per day, 100 per hour"

    # Cache settings for development
    CACHE_TYPE: str = "simple"
    CACHE_DEFAULT_TIMEOUT: int = 60  # 1 minute for development

    # Logging configuration
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )

    # Development-specific settings
    DEVELOPMENT: bool = True
    TESTING: bool = False

    # Auto-reload templates
    TEMPLATES_AUTO_RELOAD: bool = True

    # Show SQL queries in logs
    SQLALCHEMY_RECORD_QUERIES: bool = get_bool_from_env(
        "SQLALCHEMY_RECORD_QUERIES", True
    )
