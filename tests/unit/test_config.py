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
