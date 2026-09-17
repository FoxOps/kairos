"""
Rate-limit enforcement tests for the public API (app/api/rate_limit.py,
app/api/errors.py). TestingConfig hardcodes RATE_LIMIT_ENABLED=False
(app/config/testing.py) so the shared test_app fixture never exercises
real enforcement - these tests build their own app instance with
limiting explicitly re-enabled and a small API_RATE_LIMIT, the same
"mutate env/config then create_app()" pattern test_app itself uses for
OIDC_ENABLED, then tear it back down. Deliberately NOT using test_app/
service_account_client (both assume limiting stays off).
"""

import pytest

from app import create_app, db, limiter
from app.services.service_account_service import ServiceAccountService


@pytest.fixture
def rate_limited_app():
    """A fresh app with rate limiting enabled and a small,
    easy-to-breach API_RATE_LIMIT. limiter is a module-level singleton
    (app/__init__.py) shared across every app instance in this process
    - explicitly restored to disabled afterward so later tests (which
    assume it's off, like test_app) aren't affected."""
    app = create_app("app.config.TestingConfig")
    app.config["API_RATE_LIMIT"] = "3 per minute"
    limiter.enabled = True
    # ServiceAccount ids restart at 1 in each fresh in-memory test DB, but
    # the memory:// counter storage backing `limiter` is a process-lifetime
    # singleton (not reset by db.drop_all()) - without clearing it here, a
    # previous test's exhausted "service_account:1" counter would leak
    # into this test's freshly-created id=1 account.
    limiter.reset()
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()
    limiter.enabled = False
    limiter.reset()


def _make_client(app, name="svc"):
    with app.app_context():
        sa, token = ServiceAccountService.create_account(name)
    client = app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


class TestDefaultRateLimit:
    def test_default_applies_when_api_rate_limit_unset(self, rate_limited_app):
        """Default config (no API_RATE_LIMIT override at all) still
        rate-limits - app.config falls back to Config.API_RATE_LIMIT's
        own default ("60 per minute, 1000 per day"), so a handful of
        requests must never 429 under the real default."""
        rate_limited_app.config.pop("API_RATE_LIMIT", None)
        from app.config.base import Config

        rate_limited_app.config["API_RATE_LIMIT"] = Config.API_RATE_LIMIT
        client = _make_client(rate_limited_app)
        for _ in range(5):
            response = client.get("/api/v1/shift-types/")
            assert response.status_code == 200


class TestCustomRateLimit:
    def test_custom_limit_is_enforced(self, rate_limited_app):
        client = _make_client(rate_limited_app)
        statuses = [client.get("/api/v1/shift-types/").status_code for _ in range(4)]
        assert statuses[:3] == [200, 200, 200]
        assert statuses[3] == 429

    def test_429_uses_documented_error_envelope(self, rate_limited_app):
        client = _make_client(rate_limited_app)
        for _ in range(3):
            client.get("/api/v1/shift-types/")
        response = client.get("/api/v1/shift-types/")
        assert response.status_code == 429
        body = response.get_json()
        assert body["error"]["code"] == "rate_limited"
        assert "message" in body["error"]


class TestPerServiceAccountIsolation:
    def test_two_accounts_have_independent_quotas(self, rate_limited_app):
        client_a = _make_client(rate_limited_app, "a")
        client_b = _make_client(rate_limited_app, "b")

        for _ in range(3):
            assert client_a.get("/api/v1/shift-types/").status_code == 200
        assert client_a.get("/api/v1/shift-types/").status_code == 429

        # A different ServiceAccount, same tiny limit, must not be
        # affected by account A's breach - independent quota, not a
        # shared/global one.
        assert client_b.get("/api/v1/shift-types/").status_code == 200
