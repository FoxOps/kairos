"""
Tests for the ServiceAccount model (app/models/service_account.py):
token generation/hashing, validity rules, and secret exposure.
"""

from datetime import datetime, timedelta, timezone

from app.models.service_account import TOKEN_PREFIX, ServiceAccount


class TestGenerateToken:
    def test_token_has_expected_prefix(self):
        full_token, prefix, token_hash = ServiceAccount.generate_token()
        assert full_token.startswith(TOKEN_PREFIX)
        assert prefix.startswith(TOKEN_PREFIX)

    def test_tokens_are_unique(self):
        token_a, _, hash_a = ServiceAccount.generate_token()
        token_b, _, hash_b = ServiceAccount.generate_token()
        assert token_a != token_b
        assert hash_a != hash_b

    def test_hash_matches_hash_token(self):
        full_token, _, token_hash = ServiceAccount.generate_token()
        assert ServiceAccount.hash_token(full_token) == token_hash

    def test_prefix_never_contains_full_secret(self):
        full_token, prefix, _ = ServiceAccount.generate_token()
        assert len(prefix) < len(full_token)


class TestIsValid:
    def test_active_no_expiry_is_valid(self):
        sa = ServiceAccount(
            name="Test", token_prefix="ksak_test", token_hash="x", is_active=True
        )
        assert sa.is_valid() is True

    def test_inactive_is_invalid(self):
        sa = ServiceAccount(
            name="Test", token_prefix="ksak_test", token_hash="x", is_active=False
        )
        assert sa.is_valid() is False

    def test_active_future_expiry_is_valid(self):
        sa = ServiceAccount(
            name="Test",
            token_prefix="ksak_test",
            token_hash="x",
            is_active=True,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(days=1),
        )
        assert sa.is_valid() is True

    def test_active_past_expiry_is_invalid(self):
        sa = ServiceAccount(
            name="Test",
            token_prefix="ksak_test",
            token_hash="x",
            is_active=True,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(days=1),
        )
        assert sa.is_valid() is False


class TestToDict:
    def test_to_dict_never_exposes_token_hash(self):
        sa = ServiceAccount(
            name="Test", token_prefix="ksak_test", token_hash="secret-hash"
        )
        data = sa.to_dict()
        assert "token_hash" not in data

    def test_to_dict_exposes_token_prefix(self):
        sa = ServiceAccount(
            name="Test", token_prefix="ksak_test", token_hash="secret-hash"
        )
        data = sa.to_dict()
        assert data["token_prefix"] == "ksak_test"
