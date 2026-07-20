"""
Regression test for a real bug found via a live pentest: app/__init__.py
used to set app.config["RATELIMIT_DEFAULT"] *after* limiter.init_app(app)
had already run. Flask-Limiter reads RATELIMIT_DEFAULT from app.config at
init_app() time to build its default-limit rules (see
flask_limiter.Limiter.init_app()'s source) - setting it afterward silently
never applied any limit at all, regardless of RATE_LIMIT_ENABLED/
RATE_LIMIT_DEFAULT being configured. Confirmed live: 60 back-to-back
requests to a real running instance all returned 200 before the fix.

TestingConfig disables rate limiting entirely (RATE_LIMIT_ENABLED=False)
for every other test in this suite, so this needs its own app instance
with it force-enabled, built the same way tests/e2e/conftest.py's
live_server_url re-enables Talisman on top of TestingConfig.

Uses the real default limit ("200 per day, 50 per hour", TestingConfig
doesn't override RATE_LIMIT_DEFAULT) rather than a tighter test-only
value: `limiter` is a module-level singleton shared by every app built
in this process (see app/__init__.py's own module-level `app =
create_app()` fallback instance) - once its default-limits group has
been populated by the *first* app that successfully configured one,
Flask-Limiter's own init_app() leaves that group as-is for every later
app (`if not self.limit_manager._default_limits and conf_limits: ...`),
so a tighter RATE_LIMIT_DEFAULT set here would be silently ignored.
"""

from app.config.testing import TestingConfig


def test_default_rate_limit_actually_throttles_requests(monkeypatch):
    monkeypatch.setattr(TestingConfig, "RATE_LIMIT_ENABLED", True)

    from app import create_app, db

    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()

        client = app.test_client()
        # The real default is "50 per hour" - 51 requests must trip it.
        statuses = [client.get("/health").status_code for _ in range(51)]

        db.drop_all()

    assert statuses.count(200) == 50
    assert 429 in statuses, (
        "the 51st request should have been throttled - if this fails, "
        "RATELIMIT_DEFAULT is being read before it's set in app.config "
        "again (see app/__init__.py's ordering of limiter.init_app() vs "
        "the RATE_LIMIT_ENABLED block)"
    )
