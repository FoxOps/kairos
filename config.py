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


# Bare mysql://, mariadb://, postgres:// and postgresql:// (no explicit
# +driver suffix) all default, in SQLAlchemy, to the "classic" DBAPI
# driver for that dialect (MySQLdb/mysqlclient, psycopg2) - neither
# installed here on purpose, this project ships PyMySQL and
# psycopg[binary] (psycopg 3) instead. Kept in sync with
# app/config/base.py::normalize_database_uri() - see that module's
# docstring for the full rationale.
_DATABASE_URI_DRIVER_REWRITES = {
    "mysql": "mysql+pymysql://",
    "mariadb": "mariadb+pymysql://",
    "postgres": "postgresql+psycopg://",
    "postgresql": "postgresql+psycopg://",
}


def normalize_database_uri(database_uri):
    """Rewrites a bare mysql://, mariadb://, postgres:// or postgresql://
    prefix to the driver this app actually ships - see
    _DATABASE_URI_DRIVER_REWRITES above."""
    scheme = database_uri.split("://", 1)[0] if "://" in database_uri else ""
    rewritten_prefix = _DATABASE_URI_DRIVER_REWRITES.get(scheme)
    if rewritten_prefix is None:
        return database_uri
    return rewritten_prefix + database_uri.split("://", 1)[1]


# Base configuration for Flask
class Config:
    # Secret key for Flask (REQUIRED in production)
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    # Database URI - can be configured via DATABASE_URL
    # SQLite remains the default database
    SQLALCHEMY_DATABASE_URI = normalize_database_uri(
        os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    )
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

    # SQLAlchemy engine options configuration depending on the database type.
    # Uppercase to stay consistent with app/config/base.py::Config
    # (there, the name matters: Flask's app.config.from_object() only copies
    # uppercase attributes).
    SQLALCHEMY_ENGINE_OPTIONS = get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS")
