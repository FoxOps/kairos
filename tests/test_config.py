"""
Tests pour la configuration de l'application.
"""




class TestConfig:
    """Tests pour la classe Config."""

    def test_config_import(self):
        """Test que le module config peut être importé."""
        from config import Config
        assert Config is not None

    def test_config_has_secret_key(self):
        """Test que la configuration a une SECRET_KEY."""
        from config import Config

        config = Config()
        assert hasattr(config, "SECRET_KEY")
        assert config.SECRET_KEY is not None

    def test_config_secret_key_from_env(self, monkeypatch):
        """Test que SECRET_KEY peut être lu depuis les variables d'environnement."""
        import sys

        # Définir une variable d'environnement
        test_key = "test-secret-key-from-env"
        monkeypatch.setenv("SECRET_KEY", test_key)

        # Recharger le module config pour prendre en compte la nouvelle variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config
        config = Config()
        assert config.SECRET_KEY == test_key

    def test_config_secret_key_default(self, monkeypatch):
        """Test que SECRET_KEY a une valeur par défaut."""
        import sys

        # S'assurer qu'aucune variable d'environnement n'est définie
        monkeypatch.delenv("SECRET_KEY", raising=False)

        # Recharger le module config pour prendre en compte l'absence de variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config
        config = Config()
        # SECRET_KEY sans env var: généré aléatoirement (secrets.token_urlsafe), pas de valeur statique
        assert isinstance(config.SECRET_KEY, str)
        assert len(config.SECRET_KEY) > 0

    def test_config_sqlalchemy_database_uri(self):
        """Test que SQLALCHEMY_DATABASE_URI est configuré."""
        from config import Config

        config = Config()
        assert hasattr(config, "SQLALCHEMY_DATABASE_URI")
        assert config.SQLALCHEMY_DATABASE_URI is not None
        assert "sqlite" in config.SQLALCHEMY_DATABASE_URI.lower()

    def test_config_sqlalchemy_track_modifications(self):
        """Test que SQLALCHEMY_TRACK_MODIFICATIONS est configuré."""
        from config import Config

        config = Config()
        assert hasattr(config, "SQLALCHEMY_TRACK_MODIFICATIONS")
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_config_login_disabled_default(self):
        """Test que LOGIN_DISABLED est False par défaut."""
        from config import Config

        config = Config()
        assert hasattr(config, "LOGIN_DISABLED")
        assert config.LOGIN_DISABLED is False

    def test_config_login_disabled_from_env(self, monkeypatch):
        """Test que LOGIN_DISABLED peut être lu depuis les variables d'environnement."""
        import sys

        # Nettoyer d'abord
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

        monkeypatch.setenv("LOGIN_DISABLED", "True")

        # Recharger le module config pour prendre en compte la nouvelle variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config
        config = Config()
        # Maintenant LOGIN_DISABLED est bien lu depuis les variables d'environnement
        # via la fonction get_bool_from_env
        assert config.LOGIN_DISABLED is True

        # Nettoyer après
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

    def test_config_login_disabled_default(self, monkeypatch):
        """Test que LOGIN_DISABLED a la valeur par défaut False."""
        import sys

        # Nettoyer d'abord
        monkeypatch.delenv("LOGIN_DISABLED", raising=False)

        # Recharger le module config pour prendre en compte l'absence de variable
        if "config" in sys.modules:
            del sys.modules["config"]

        from config import Config
        config = Config()
        assert config.LOGIN_DISABLED is False

    def test_config_remember_cookie_duration(self):
        """Test que REMEMBER_COOKIE_DURATION est configuré."""
        from config import Config

        config = Config()
        assert hasattr(config, "REMEMBER_COOKIE_DURATION")
        assert config.REMEMBER_COOKIE_DURATION == 86400

    def test_config_session_protection(self):
        """Test que SESSION_PROTECTION est configuré."""
        from config import Config

        config = Config()
        assert hasattr(config, "SESSION_PROTECTION")
        assert config.SESSION_PROTECTION == "strong"


class TestConfigInApp:
    """Tests pour vérifier que la configuration est correctement appliquée à l'application."""

    def test_app_uses_config(self, test_app):
        """Test que l'application utilise la configuration Config."""
        with test_app.app_context():
            assert test_app.config["SECRET_KEY"] is not None
            assert "SQLALCHEMY_DATABASE_URI" in test_app.config
            assert "SQLALCHEMY_TRACK_MODIFICATIONS" in test_app.config

    def test_app_config_testing_mode(self, test_app):
        """Test que le mode TESTING est activé dans les tests."""
        with test_app.app_context():
            assert test_app.config["TESTING"] is True

    def test_app_config_secret_key_in_tests(self, test_app):
        """Test que SECRET_KEY est défini dans les tests."""
        with test_app.app_context():
            # This is a test value, not a real secret
            assert test_app.config["SECRET_KEY"] == "test-secret-key"  # noqa: S105

    def test_app_config_database_uri_in_tests(self, test_app):
        """Test que la base de données en mémoire est utilisée dans les tests."""
        with test_app.app_context():
            assert test_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


class TestConfigEnvironmentVariables:
    """Tests pour les variables d'environnement."""

    def test_all_config_values_accessible(self, test_app):
        """Test que toutes les valeurs de configuration sont accessibles."""
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
                assert key in test_app.config, f"Clé de configuration manquante: {key}"
