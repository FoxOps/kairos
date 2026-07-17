"""
Tests for the application configuration.
"""


class TestConfig:
    """Tests for the Config class."""

    def test_config_import(self):
        """Test that the config module can be imported."""
        from config import Config

        assert Config is not None

    def test_config_has_secret_key(self):
        """Test that the configuration has a SECRET_KEY."""
        from config import Config

        config = Config()
        assert hasattr(config, "SECRET_KEY")
        assert config.SECRET_KEY is not None

    def test_config_secret_key_from_env(self, monkeypatch):
        """Test that SECRET_KEY can be read from environment variables."""
        import sys

        # Set an environment variable
        test_key = "test-secret-key-from-env"
        monkeypatch.setenv("SECRET_KEY", test_key)

        # Reload the config module to pick up the new variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config

        config = Config()
        assert config.SECRET_KEY == test_key

    def test_config_secret_key_default(self, monkeypatch):
        """Test that SECRET_KEY has a default value."""
        import sys

        # Make sure no environment variable is set
        monkeypatch.delenv("SECRET_KEY", raising=False)

        # Reload the config module to pick up the missing variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config

        config = Config()
        # SECRET_KEY without an env var: randomly generated
        # (secrets.token_urlsafe), no static value
        assert isinstance(config.SECRET_KEY, str)
        assert len(config.SECRET_KEY) > 0

    def test_config_sqlalchemy_database_uri(self):
        """Test that SQLALCHEMY_DATABASE_URI is configured."""
        from config import Config

        config = Config()
        assert hasattr(config, "SQLALCHEMY_DATABASE_URI")
        assert config.SQLALCHEMY_DATABASE_URI is not None
        assert "sqlite" in config.SQLALCHEMY_DATABASE_URI.lower()

    def test_config_sqlalchemy_track_modifications(self):
        """Test that SQLALCHEMY_TRACK_MODIFICATIONS is configured."""
        from config import Config

        config = Config()
        assert hasattr(config, "SQLALCHEMY_TRACK_MODIFICATIONS")
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_config_login_disabled_from_env(self, monkeypatch):
        """Test that LOGIN_DISABLED can be read from environment variables."""
        import sys

        # Clean up first
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

        monkeypatch.setenv("LOGIN_DISABLED", "True")

        # Reload the config module to pick up the new variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config

        config = Config()
        # LOGIN_DISABLED is now correctly read from the environment
        # variable via get_bool_from_env
        assert config.LOGIN_DISABLED is True

        # Clean up afterwards
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

    def test_config_login_disabled_default(self, monkeypatch):
        """Test that LOGIN_DISABLED defaults to False."""
        import sys

        # Clean up first
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

        # Reload the config module to pick up the missing variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config

        config = Config()
        assert config.LOGIN_DISABLED is False

    def test_config_remember_cookie_duration(self):
        """Test that REMEMBER_COOKIE_DURATION is configured."""
        from config import Config

        config = Config()
        assert hasattr(config, "REMEMBER_COOKIE_DURATION")
        assert config.REMEMBER_COOKIE_DURATION == 86400

    def test_config_session_protection(self):
        """Test that SESSION_PROTECTION is configured."""
        from config import Config

        config = Config()
        assert hasattr(config, "SESSION_PROTECTION")
        assert config.SESSION_PROTECTION == "strong"


class TestConfigInApp:
    """Tests checking that the configuration is correctly applied to the app."""

    def test_app_uses_config(self, test_app):
        """Test that the app uses the Config configuration."""
        with test_app.app_context():
            assert test_app.config["SECRET_KEY"] is not None
            assert "SQLALCHEMY_DATABASE_URI" in test_app.config
            assert "SQLALCHEMY_TRACK_MODIFICATIONS" in test_app.config

    def test_app_config_testing_mode(self, test_app):
        """Test that TESTING mode is enabled in tests."""
        with test_app.app_context():
            assert test_app.config["TESTING"] is True

    def test_app_config_secret_key_in_tests(self, test_app):
        """Test that SECRET_KEY is set in tests."""
        with test_app.app_context():
            # This is a test value, not a real secret
            assert test_app.config["SECRET_KEY"] == "test-secret-key"  # noqa: S105

    def test_app_config_database_uri_in_tests(self, test_app):
        """Test that the in-memory database is used in tests."""
        with test_app.app_context():
            assert test_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


class TestConfigEnvironmentVariables:
    """Tests for the environment variables."""

    def test_all_config_values_accessible(self, test_app):
        """Test that every configuration value is accessible."""
        with test_app.app_context():
            config_keys = [
                "SECRET_KEY",
                "SQLALCHEMY_DATABASE_URI",
                "SQLALCHEMY_TRACK_MODIFICATIONS",
                "LOGIN_DISABLED",
                "REMEMBER_COOKIE_DURATION",
                "SESSION_PROTECTION",
                "TESTING",
            ]

            for key in config_keys:
                assert key in test_app.config, f"Missing config key: {key}"

    def test_sqlalchemy_engine_options_is_uppercase_and_reads_env(self, monkeypatch):
        """Regression guard: this attribute used to be named
        custom_engine_options (lowercase), silently never copied into
        app.config by Flask's app.config.from_object() (which only copies
        uppercase attributes) - see app/config/base.py and config.py."""
        import sys

        monkeypatch.setenv(
            "SQLALCHEMY_ENGINE_OPTIONS", '{"pool_pre_ping": true, "pool_recycle": 3600}'
        )
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config

        config = Config()
        assert not hasattr(config, "custom_engine_options")
        assert config.SQLALCHEMY_ENGINE_OPTIONS == {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }


class TestGetDatabaseType:
    """Tests for get_database_type() - database dialect detection from the
    DATABASE_URL prefix. Not called anywhere in app/ (SQLAlchemy resolves
    the dialect/driver itself from the URI prefix at runtime), but its
    detection logic is still exercised here since it's public, documented
    behavior (see CLAUDE.md's "Configuration: two parallel systems")."""

    def test_sqlite(self):
        from config import get_database_type

        assert get_database_type("sqlite:///app.db") == "sqlite"
        assert get_database_type("sqlite:///:memory:") == "sqlite"

    def test_postgresql(self):
        from config import get_database_type

        assert get_database_type("postgresql://u:p@host:5432/db") == "postgresql"
        assert get_database_type("postgres://u:p@host:5432/db") == "postgresql"

    def test_mysql(self):
        from config import get_database_type

        assert get_database_type("mysql://u:p@host:3306/db") == "mysql"

    def test_mariadb(self):
        from config import get_database_type

        assert get_database_type("mariadb://u:p@host:3306/db") == "mysql"

    def test_unknown_scheme_falls_back_to_sqlite(self):
        """Unrecognized scheme silently defaults to sqlite - documented
        existing fallback behavior, not something this change introduces."""
        from config import get_database_type

        assert get_database_type("oracle://u:p@host/db") == "sqlite"

    def test_default_reads_database_url_env(self, monkeypatch):
        from config import get_database_type

        monkeypatch.setenv("DATABASE_URL", "mysql://u:p@host:3306/db")
        assert get_database_type() == "mysql"


class TestNormalizeDatabaseUri:
    """Tests for normalize_database_uri() (app/config/base.py, mirrored in
    config.py) - the fix for a real bug found while building MySQL
    support: SQLAlchemy's bare mysql://, mariadb://, postgres:// and
    postgresql:// prefixes (the format documented everywhere in this
    repo's docs/.env.example) default to the "classic" DBAPI drivers
    (MySQLdb/mysqlclient, psycopg2), NOT the pure-Python/modern ones this
    app actually ships (PyMySQL, psycopg 3) - confirmed by
    create_engine() raising ModuleNotFoundError on the bare prefixes
    before this fix existed."""

    def test_rewrites_bare_mysql(self):
        from app.config.base import normalize_database_uri

        assert normalize_database_uri("mysql://u:p@host:3306/db") == (
            "mysql+pymysql://u:p@host:3306/db"
        )

    def test_rewrites_bare_mariadb(self):
        from app.config.base import normalize_database_uri

        assert normalize_database_uri("mariadb://u:p@host:3306/db") == (
            "mariadb+pymysql://u:p@host:3306/db"
        )

    def test_rewrites_bare_postgres_and_postgresql(self):
        from app.config.base import normalize_database_uri

        assert normalize_database_uri("postgres://u:p@host:5432/db") == (
            "postgresql+psycopg://u:p@host:5432/db"
        )
        assert normalize_database_uri("postgresql://u:p@host:5432/db") == (
            "postgresql+psycopg://u:p@host:5432/db"
        )

    def test_leaves_sqlite_untouched(self):
        from app.config.base import normalize_database_uri

        assert normalize_database_uri("sqlite:///app.db") == "sqlite:///app.db"

    def test_leaves_explicit_driver_untouched(self):
        """An admin who already picked their own driver (e.g. installed
        mysqlclient themselves) must never be silently overridden."""
        from app.config.base import normalize_database_uri

        uri = "postgresql+psycopg2://u:p@host:5432/db"
        assert normalize_database_uri(uri) == uri

    def test_config_py_mirror_matches(self):
        """config.py (legacy module) must stay in sync with
        app/config/base.py - see CLAUDE.md "Configuration: two parallel
        systems"."""
        from app.config.base import normalize_database_uri as app_version
        from config import normalize_database_uri as legacy_version

        for uri in (
            "mysql://u:p@host:3306/db",
            "mariadb://u:p@host:3306/db",
            "postgres://u:p@host:5432/db",
            "sqlite:///app.db",
        ):
            assert app_version(uri) == legacy_version(uri)


class TestMySQLDriverAvailable:
    """PyMySQL must be resolvable by SQLAlchemy without a real MySQL
    server - proves a normalized DATABASE_URL actually works once
    PyMySQL is installed, not just in theory."""

    def test_pymysql_importable(self):
        """PyMySQL is installed and importable (pure-Python, no system
        library required)."""
        import pymysql  # noqa: F401

    def test_sqlalchemy_resolves_mysql_pymysql_dialect(self):
        """Building (not connecting) an engine with mysql+pymysql:// must
        not raise ImportError/ModuleNotFoundError."""
        from sqlalchemy import create_engine

        engine = create_engine("mysql+pymysql://user:pass@localhost:3306/testdb")
        assert engine.dialect.name == "mysql"
        assert engine.dialect.driver == "pymysql"

    def test_normalized_bare_mysql_scheme_resolves_to_pymysql(self):
        """The exact round-trip a real deployment goes through:
        DATABASE_URL=mysql://... (bare, the documented format) ->
        normalize_database_uri() -> a SQLAlchemy engine using pymysql,
        with zero ModuleNotFoundError."""
        from sqlalchemy import create_engine

        from app.config.base import normalize_database_uri

        uri = normalize_database_uri("mysql://user:pass@localhost:3306/testdb")
        engine = create_engine(uri)
        assert engine.dialect.driver == "pymysql"
