import json
import logging
import os
import secrets

# Load environment variables from a .env file if present.
# This allows easy configuration without modifying the code.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv isn't installed, fall back to system environment variables only
    pass


# Utility function to convert boolean values from environment variables
def get_bool_from_env(env_var, default=False):
    """Convert an environment variable to a boolean.

    Accepts: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
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
        # For backward compatibility, return the default value but log
        # a warning if the value isn't recognized
        if value_lower:
            logging.warning(
                f"Unrecognized value for {env_var}: '{value}'. Using default: {default}"
            )
        return default


# Utility function to get an integer value from environment variables
def get_int_from_env(env_var, default=0):
    """Convert an environment variable to an integer."""
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


# Utility function to get a JSON value from environment variables
def get_str_from_env(env_var, default=""):
    """Convert an environment variable to a string."""
    value = os.environ.get(env_var)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def get_json_from_env(env_var, default=None):
    """Convert an environment variable to a Python object via JSON."""
    value = os.environ.get(env_var)
    if value is None or value.strip() == "":
        return default

    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        logging.warning(f"Invalid JSON value for {env_var}: '{value}'. Using default")
        return default


# Utility function to detect the database type
# Must be defined before the Config class to avoid circular reference issues
def get_database_type(database_uri=None):
    """Detect the database type from the URI."""
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
        # Default to assuming SQLite
        return "sqlite"


# Base configuration for Flask
class Config:
    # Secret key for Flask (REQUIRED in production)
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    # Database URI - can be configured via DATABASE_URL
    # SQLite remains the default database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = get_bool_from_env(
        "SQLALCHEMY_TRACK_MODIFICATIONS", False
    )

    # Flask-Login / session configuration
    LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)
    REMEMBER_COOKIE_DURATION = get_int_from_env("REMEMBER_COOKIE_DURATION", 86400)
    SESSION_PROTECTION = get_str_from_env("SESSION_PROTECTION", "strong")

    # Configuration so Flask listens on 0.0.0.0:5000
    HOST = os.environ.get("FLASK_HOST") or "0.0.0.0"
    PORT = int(os.environ.get("FLASK_PORT") or 5000)

    # Detect the database type from the URI
    @staticmethod
    def get_database_type(database_uri=None):
        """Detect the database type from the URI."""
        return get_database_type(database_uri or Config.SQLALCHEMY_DATABASE_URI)

    # SQLAlchemy engine options configuration depending on the database type
    custom_engine_options = get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS")
