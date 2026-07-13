"""Tests unitaires pour config_oidc.py (OIDCConfig, get_bool_from_env).

OIDCConfig est un état de classe global (pas une instance) chargé depuis
les variables d'environnement - chaque test sauvegarde/restaure les env
vars qu'il touche et recharge la config au teardown, pour ne pas fuiter
d'état vers d'autres tests (même pattern que tests/conftest.py::test_app).
"""

import os

import pytest

from config_oidc import OIDCConfig, get_bool_from_env


@pytest.fixture
def clean_oidc_env():
    """Sauvegarde/restaure toutes les variables OIDC_* autour d'un test."""
    keys = [
        "OIDC_ENABLED",
        "OIDC_ISSUER",
        "OIDC_INTERNAL_ISSUER",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_REDIRECT_URI",
        "OIDC_POST_LOGOUT_REDIRECT_URI",
        "OIDC_EMAIL_CLAIM",
        "OIDC_NAME_CLAIM",
        "OIDC_USERNAME_CLAIM",
        "OIDC_GROUPS_CLAIM",
        "OIDC_ROLES_CLAIM",
        "OIDC_SIGNATURE_ALGORITHMS",
        "OIDC_SCOPE",
        "OIDC_DISABLE_BASIC_AUTH",
    ]
    original = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in original.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    OIDCConfig.load_config()


class TestGetBoolFromEnv:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("y", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("n", False),
            ("off", False),
        ],
    )
    def test_recognized_values(self, monkeypatch, raw, expected):
        monkeypatch.setenv("SOME_FLAG", raw)
        assert get_bool_from_env("SOME_FLAG") is expected

    def test_missing_var_returns_default(self, monkeypatch):
        monkeypatch.delenv("SOME_FLAG", raising=False)
        assert get_bool_from_env("SOME_FLAG", default=True) is True
        assert get_bool_from_env("SOME_FLAG", default=False) is False

    def test_unrecognized_value_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("SOME_FLAG", "maybe")
        assert get_bool_from_env("SOME_FLAG", default=True) is True


class TestOIDCConfigLoadConfig:
    def test_load_config_reads_env_vars(self, clean_oidc_env, monkeypatch):
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
        monkeypatch.setenv("OIDC_CLIENT_ID", "my-client")
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "my-secret")
        monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example.com/oidc/callback")

        OIDCConfig.load_config()

        assert OIDCConfig.ENABLED is True
        assert OIDCConfig.ISSUER == "https://idp.example.com"
        assert OIDCConfig.CLIENT_ID == "my-client"
        assert OIDCConfig.CLIENT_SECRET == "my-secret"
        assert OIDCConfig.REDIRECT_URI == "https://app.example.com/oidc/callback"

    def test_load_config_defaults_when_unset(self, clean_oidc_env, monkeypatch):
        for key in (
            "OIDC_ENABLED",
            "OIDC_ISSUER",
            "OIDC_CLIENT_ID",
            "OIDC_CLIENT_SECRET",
            "OIDC_REDIRECT_URI",
            "OIDC_EMAIL_CLAIM",
            "OIDC_NAME_CLAIM",
            "OIDC_USERNAME_CLAIM",
            "OIDC_SCOPE",
        ):
            monkeypatch.delenv(key, raising=False)

        OIDCConfig.load_config()

        assert OIDCConfig.ENABLED is False
        assert OIDCConfig.ISSUER == ""
        assert OIDCConfig.EMAIL_CLAIM == "email"
        assert OIDCConfig.NAME_CLAIM == "name"
        assert OIDCConfig.USERNAME_CLAIM == "preferred_username"
        assert OIDCConfig.SCOPE == "openid profile email"
        # DISABLE_BASIC_AUTH par défaut à True (pas False comme les
        # autres bools) - décision produit : une fois OIDC_ENABLED, on
        # bascule sur SSO par défaut plutôt que de garder les deux actifs
        # silencieusement.
        assert OIDCConfig.DISABLE_BASIC_AUTH is True


class TestOIDCConfigIsConfigured:
    def _set_all_required(self, monkeypatch):
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
        monkeypatch.setenv("OIDC_CLIENT_ID", "my-client")
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "my-secret")
        monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example.com/oidc/callback")

    def test_true_when_all_required_fields_set(self, clean_oidc_env, monkeypatch):
        self._set_all_required(monkeypatch)
        OIDCConfig.load_config()
        assert OIDCConfig.is_configured() is True

    @pytest.mark.parametrize(
        "missing_key",
        [
            "OIDC_ENABLED",
            "OIDC_ISSUER",
            "OIDC_CLIENT_ID",
            "OIDC_CLIENT_SECRET",
            "OIDC_REDIRECT_URI",
        ],
    )
    def test_false_when_a_required_field_is_missing(
        self, clean_oidc_env, monkeypatch, missing_key
    ):
        self._set_all_required(monkeypatch)
        monkeypatch.delenv(missing_key, raising=False)
        OIDCConfig.load_config()
        assert OIDCConfig.is_configured() is False

    def test_false_when_oidc_disabled_even_with_full_config(
        self, clean_oidc_env, monkeypatch
    ):
        self._set_all_required(monkeypatch)
        monkeypatch.setenv("OIDC_ENABLED", "false")
        OIDCConfig.load_config()
        assert OIDCConfig.is_configured() is False


class TestOIDCConfigGetConfigDict:
    def test_returns_all_expected_keys(self, clean_oidc_env, monkeypatch):
        monkeypatch.setenv("OIDC_ENABLED", "true")
        OIDCConfig.load_config()
        config_dict = OIDCConfig.get_config_dict()
        assert config_dict["OIDC_ENABLED"] is True
        assert "OIDC_CLIENT_SECRET" in config_dict
        assert "OIDC_SCOPE" in config_dict
