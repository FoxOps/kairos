"""Unit tests for config_oidc.py (OIDCConfig, get_bool_from_env).

OIDCConfig is global class state (not an instance) loaded from
environment variables - each test saves/restores the env vars it
touches and reloads the config at teardown, so state doesn't leak into
other tests (same pattern as tests/conftest.py::test_app).
"""

import os
from unittest.mock import patch

import pytest

from config_oidc import OIDCConfig, get_bool_from_env


@pytest.fixture
def clean_oidc_env():
    """Save/restore every OIDC_* variable around a test."""
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
        # DISABLE_BASIC_AUTH defaults to True (not False like the other
        # bools) - a product decision: once OIDC_ENABLED, we switch to
        # SSO by default rather than silently keeping both active.
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


class TestCreateAppLoginManagerOidcMode:
    """create_app() sets login_manager.login_view/login_message based on
    OIDCConfig - read from environment variables when the app is created
    (OIDCConfig.load_config() is called there), not patchable after the
    fact on an already-built app (see tests/integration/
    test_oidc_routes.py::oidc_mode, which tests the ROUTE wiring, not
    this once-at-startup configuration).

    OIDCAuthLib.init_app is mocked to avoid a real network OIDC
    discovery call (irrelevant here, and otherwise slow/flaky in
    tests)."""

    def _set_all_required(self, monkeypatch):
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
        monkeypatch.setenv("OIDC_CLIENT_ID", "my-client")
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "my-secret")
        monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example.com/oidc/callback")

    def test_disables_login_message_when_basic_auth_disabled(
        self, clean_oidc_env, monkeypatch
    ):
        """Otherwise Flask-Login's default "please log in" flash,
        triggered by @login_required before the redirect to
        auth.oidc_login (which never renders a template), ends up stuck
        alongside the "Connexion OIDC réussie !" flash on the first page
        rendered after returning from the IdP - both show up at once."""
        self._set_all_required(monkeypatch)
        monkeypatch.setenv("OIDC_DISABLE_BASIC_AUTH", "true")

        with patch("app.auth.oidc_auth.OIDCAuthLib.init_app"):
            from app import create_app

            app = create_app("app.config.TestingConfig")

        assert app.login_manager.login_view == "auth.oidc_login"
        assert app.login_manager.login_message is None

    def test_keeps_login_message_in_basic_auth_mode(self, clean_oidc_env, monkeypatch):
        """In classic auth.login mode (form-based), the flash displays
        normally on this page - a single hop, no double flash."""
        monkeypatch.setenv("OIDC_ENABLED", "false")

        from app import create_app

        app = create_app("app.config.TestingConfig")

        assert app.login_manager.login_view == "auth.login"
        assert app.login_manager.login_message is not None
