"""Unit tests for app/auth/oidc_auth.py (OIDCAuthLib).

Builds OIDCAuthLib instances directly (not via the global `oidc_auth`
singleton nor a real network discovery) to isolate each method -
`oidc_client`/`authorization_endpoint`/etc. are pre-filled by hand to
simulate an already-configured client. Outgoing HTTP calls
(`requests.get`/`requests.post`) are mocked: no test here contacts a
real OIDC provider (see tests/e2e/test_oidc_browser_flow.py for the
full flow against a real fake OIDC provider).
"""

import base64
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.auth.oidc_auth import OIDCAuthLib
from config_oidc import OIDCConfig


@pytest.fixture
def configured_auth():
    """OIDCAuthLib with a client + endpoints already in place (simulates
    a successful OIDC discovery), with no network call."""
    auth = OIDCAuthLib()
    auth.oidc_client = MagicMock()
    auth.authorization_endpoint = "https://idp.example.com/authorize"
    auth.token_endpoint = "https://idp.example.com/token"
    auth.userinfo_endpoint = "https://idp.example.com/userinfo"
    auth.end_session_endpoint = "https://idp.example.com/logout"
    return auth


@pytest.fixture(autouse=True)
def oidc_config_values(monkeypatch, test_app):
    """Deterministic OIDCConfig values for this test module.

    Explicitly depends on test_app: its creation (create_app()) calls
    OIDCConfig.load_config(), which would overwrite these values if this
    fixture ran first (fixture ordering among autouse fixtures with no
    explicit dependency isn't guaranteed relative to a non-autouse
    fixture)."""
    monkeypatch.setattr(OIDCConfig, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(OIDCConfig, "CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(
        OIDCConfig, "REDIRECT_URI", "https://app.example.com/oidc/callback"
    )
    monkeypatch.setattr(OIDCConfig, "SCOPE", "openid profile email")
    monkeypatch.setattr(OIDCConfig, "EMAIL_CLAIM", "email")
    monkeypatch.setattr(OIDCConfig, "NAME_CLAIM", "name")
    monkeypatch.setattr(OIDCConfig, "USERNAME_CLAIM", "preferred_username")
    monkeypatch.setattr(OIDCConfig, "GROUPS_CLAIM", "")
    monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "")


def _fake_jwt(payload: dict) -> str:
    """An unsigned JWT, good enough for these tests: oidc_auth.py
    decodes the payload manually (base64) without ever checking the
    signature."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fakesignature"


class TestGetAuthorizationUrl:
    def test_returns_none_without_configured_client(self):
        auth = OIDCAuthLib()
        assert auth.get_authorization_url() is None

    def test_returns_none_without_authorization_endpoint(self):
        auth = OIDCAuthLib()
        auth.oidc_client = MagicMock()
        auth.authorization_endpoint = None
        assert auth.get_authorization_url() is None

    def test_builds_url_with_state_and_nonce(self, configured_auth, test_app):
        with test_app.test_request_context():
            url = configured_auth.get_authorization_url()

            assert url.startswith("https://idp.example.com/authorize?")
            assert "client_id=test-client-id" in url
            assert "response_type=code" in url
            assert "state=" in url
            assert "nonce=" in url

    def test_stores_state_and_nonce_in_session(self, configured_auth, test_app):
        with test_app.test_request_context():
            from flask import session

            configured_auth.get_authorization_url()
            assert session.get("oidc_state")
            assert session.get("oidc_nonce")

    def test_uses_provided_state_and_nonce(self, configured_auth, test_app):
        with test_app.test_request_context():
            from flask import session

            url = configured_auth.get_authorization_url(
                state="fixed-state", nonce="fixed-nonce"
            )
            assert "state=fixed-state" in url
            assert "nonce=fixed-nonce" in url
            assert session["oidc_state"] == "fixed-state"


class TestExchangeCodeForToken:
    def test_returns_none_without_configured_client(self, test_app):
        with test_app.test_request_context():
            auth = OIDCAuthLib()
            assert auth.exchange_code_for_token("some-code") is None

    def test_success_stores_id_token_in_session(self, configured_auth, test_app):
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "access_token": "at-123",
            "id_token": "it-456",
            "expires_at": time.time() + 3600,
        }
        fake_response.raise_for_status.return_value = None

        with test_app.test_request_context():
            from flask import session

            with patch("requests.post", return_value=fake_response) as mock_post:
                token_data = configured_auth.exchange_code_for_token("some-code")

            assert token_data["access_token"] == "at-123"
            assert session["oidc_id_token"] == "it-456"
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["code"] == "some-code"
            assert call_kwargs["data"]["client_id"] == "test-client-id"

    def test_request_exception_returns_none(self, configured_auth, test_app):
        import requests

        with test_app.test_request_context():
            with patch("requests.post", side_effect=requests.RequestException("boom")):
                assert configured_auth.exchange_code_for_token("some-code") is None


class TestGetUserInfo:
    def test_returns_none_without_configured_client(self):
        auth = OIDCAuthLib()
        assert auth.get_user_info("some-access-token") is None

    def test_success_returns_user_info(self, configured_auth):
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "email": "alice@example.com",
            "name": "Alice",
        }
        fake_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=fake_response) as mock_get:
            user_info = configured_auth.get_user_info("at-123")

        assert user_info["email"] == "alice@example.com"
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer at-123"

    def test_request_exception_returns_none(self, configured_auth):
        import requests

        with patch("requests.get", side_effect=requests.RequestException("boom")):
            assert configured_auth.get_user_info("at-123") is None


class TestVerifyToken:
    def test_none_token_data_is_invalid(self):
        auth = OIDCAuthLib()
        assert auth.verify_token(None) is False

    def test_no_expiry_claim_is_valid(self):
        auth = OIDCAuthLib()
        assert auth.verify_token({"access_token": "at"}) is True

    def test_future_expiry_is_valid(self):
        auth = OIDCAuthLib()
        assert auth.verify_token({"expires_at": time.time() + 3600}) is True

    def test_past_expiry_is_invalid(self):
        auth = OIDCAuthLib()
        assert auth.verify_token({"expires_at": time.time() - 3600}) is False


class TestExtractUserInfoFromToken:
    def test_from_userinfo_endpoint_response(self):
        auth = OIDCAuthLib()
        user_info = {
            "email": "alice@example.com",
            "name": "Alice Example",
            "preferred_username": "alice",
        }
        data = auth.extract_user_info_from_token(token_data={}, user_info=user_info)
        assert data == {
            "email": "alice@example.com",
            "name": "Alice Example",
            "username": "alice",
        }

    def test_from_userinfo_with_groups_and_roles_claims(self, monkeypatch):
        monkeypatch.setattr(OIDCConfig, "GROUPS_CLAIM", "groups")
        monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "roles")
        auth = OIDCAuthLib()
        user_info = {
            "email": "alice@example.com",
            "groups": ["team-a"],
            "roles": ["admin"],
        }
        data = auth.extract_user_info_from_token(token_data={}, user_info=user_info)
        assert data["groups"] == ["team-a"]
        assert data["roles"] == ["admin"]

    def test_from_id_token_payload_when_no_userinfo(self):
        auth = OIDCAuthLib()
        id_token = _fake_jwt({"email": "bob@example.com", "name": "Bob"})
        data = auth.extract_user_info_from_token(
            token_data={"id_token": id_token}, user_info=None
        )
        assert data["email"] == "bob@example.com"
        assert data["name"] == "Bob"

    def test_falls_back_to_access_token_if_no_id_token(self):
        auth = OIDCAuthLib()
        access_token = _fake_jwt({"email": "carol@example.com"})
        data = auth.extract_user_info_from_token(
            token_data={"access_token": access_token}, user_info=None
        )
        assert data["email"] == "carol@example.com"

    def test_malformed_token_returns_empty_dict(self):
        auth = OIDCAuthLib()
        data = auth.extract_user_info_from_token(
            token_data={"id_token": "not-a-valid-jwt"}, user_info=None
        )
        assert data == {}

    def test_no_token_and_no_userinfo_returns_empty_dict(self):
        auth = OIDCAuthLib()
        assert auth.extract_user_info_from_token(token_data=None, user_info=None) == {}


class TestHandleOauthCallback:
    def test_invalid_state_returns_none(self, configured_auth, test_app):
        with test_app.test_request_context("/oidc/callback?state=wrong&code=abc"):
            from flask import session

            session["oidc_state"] = "expected-state"
            assert (
                configured_auth.handle_oauth_callback(__import__("flask").request)
                is None
            )

    def test_missing_code_returns_none(self, configured_auth, test_app):
        with test_app.test_request_context("/oidc/callback?state=s1"):
            from flask import session

            session["oidc_state"] = "s1"
            assert (
                configured_auth.handle_oauth_callback(__import__("flask").request)
                is None
            )

    def test_full_happy_path_returns_user_data(self, configured_auth, test_app):
        id_token = _fake_jwt({"email": "dave@example.com", "name": "Dave"})
        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "at-1",
            "id_token": id_token,
        }
        token_response.raise_for_status.return_value = None

        userinfo_response = MagicMock()
        userinfo_response.json.return_value = {
            "email": "dave@example.com",
            "name": "Dave",
        }
        userinfo_response.raise_for_status.return_value = None

        with test_app.test_request_context("/oidc/callback?state=s1&code=abc"):
            from flask import session

            session["oidc_state"] = "s1"
            with patch("requests.post", return_value=token_response), patch(
                "requests.get", return_value=userinfo_response
            ):
                user_data = configured_auth.handle_oauth_callback(
                    __import__("flask").request
                )

        assert user_data["email"] == "dave@example.com"

    def test_token_exchange_failure_returns_none(self, configured_auth, test_app):
        with test_app.test_request_context("/oidc/callback?state=s1&code=abc"):
            from flask import session

            session["oidc_state"] = "s1"
            with patch("requests.post", side_effect=Exception("boom")):
                assert (
                    configured_auth.handle_oauth_callback(__import__("flask").request)
                    is None
                )


class TestBuildLogoutUrl:
    def test_none_without_end_session_endpoint(self, test_app):
        with test_app.test_request_context():
            auth = OIDCAuthLib()
            auth.end_session_endpoint = None
            assert auth.build_logout_url() is None

    def test_bare_endpoint_without_params(self, configured_auth, test_app):
        with test_app.test_request_context():
            url = configured_auth.build_logout_url()
            assert url == "https://idp.example.com/logout"

    def test_includes_id_token_hint_from_session(self, configured_auth, test_app):
        with test_app.test_request_context():
            from flask import session

            session["oidc_id_token"] = "it-789"
            url = configured_auth.build_logout_url()
            assert "id_token_hint=it-789" in url
            # Consumed (popped) once used - not reusable afterwards
            assert "oidc_id_token" not in session

    def test_includes_post_logout_redirect_uri(self, configured_auth, test_app):
        with test_app.test_request_context():
            url = configured_auth.build_logout_url(
                post_logout_redirect_uri="https://app.example.com/login"
            )
            assert "post_logout_redirect_uri=https" in url


class TestRehost:
    def test_replaces_scheme_and_host_keeps_path_and_query(self):
        result = OIDCAuthLib._rehost(
            "http://internal-idp:8080/auth?foo=bar", "https://public-idp.example.com"
        )
        assert result == "https://public-idp.example.com/auth?foo=bar"

    def test_none_url_returns_none(self):
        assert OIDCAuthLib._rehost(None, "https://public-idp.example.com") is None
