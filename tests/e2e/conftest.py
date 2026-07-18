"""
Fixtures for the real-browser E2E tests (test_browser_flows.py).

This module must never make collecting tests/e2e/ as a whole fail if
playwright isn't installed - test_user_flows.py (E2E via the Flask test
client, no browser) must keep running normally in this environment.
That's why playwright isn't imported at module level here: every
fixture that needs it does its own `pytest.importorskip`, which only
skips the tests that request it (test_browser_flows.py), not the rest
of the e2e/ directory.
"""

import os
import socket
import threading
import time

import pytest


def _free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(host: str, port: int, timeout: float = 10.0) -> None:
    """Wait until a TCP port accepts connections, or raise TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Server did not start after {timeout}s on {host}:{port}")


ADMIN_EMAIL = "e2e-admin@kairos.local"
ADMIN_PASSWORD = (
    "e2e-password-123"  # noqa: S105 - synthetic test credential, not a real secret
)


@pytest.fixture(scope="module")
def live_server_url():
    """Launch a real Flask server (thread, free port) with Talisman
    actually active - not TestingConfig, which disables Talisman and
    therefore the CSP. Without this, CSP bugs would stay invisible even
    with a real browser (see report/E2E Playwright - Tests navigateur
    réel.md for the context: that's exactly the point of this test
    suite).
    """
    pytest.importorskip("playwright")

    from flask_talisman import Talisman

    from app import CSP_POLICY, compress, create_app, db
    from app.models import Group, User

    app = create_app("app.config.TestingConfig")
    # CSRF disabled here: this tests browser rendering/behavior (JS,
    # CSS, CSP), not CSRF protection - already covered by
    # tests/integration/test_security.py.
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TALISMAN_FORCE_HTTPS"] = True
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP_POLICY,
    )
    compress.init_app(app)

    with app.app_context():
        db.drop_all()
        db.create_all()

        group = Group(
            name="E2E Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        admin = User(
            name="E2E Admin", email=ADMIN_EMAIL, group_id=group.id, is_admin=True
        )
        admin.set_password(ADMIN_PASSWORD)
        admin.generate_ics_token()
        db.session.add(admin)
        db.session.commit()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=port, use_reloader=False, debug=False
        ),
        daemon=True,
    )
    server_thread.start()
    _wait_until_up("127.0.0.1", port)

    yield base_url

    # Daemon thread: stops with the test process, no explicit teardown
    # needed (the blocking app.run() has no clean stop method on the
    # Werkzeug dev server side).


@pytest.fixture
def logged_in_page(live_server_url, page):
    """A Playwright page already logged in as admin (a real form, no
    directly-injected cookie - this verifies the login flow actually
    works in the browser)."""
    page.goto(f"{live_server_url}/login")
    page.fill('input[name="email"]', ADMIN_EMAIL)
    page.fill('input[name="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    return page


@pytest.fixture(scope="module")
def oidc_live_servers():
    """Launch a real Flask server (the app) AND a fake OIDC provider
    (tests/e2e/oidc_mock_provider.py), both in threads on free ports, to
    exercise the full SSO flow through a real browser - redirect to the
    IdP, a real login page with a click, return with a code,
    server-to-server exchanges (discovery, token, userinfo), session
    establishment, just like a real IdP.

    Returns (app_base_url, idp_base_url).
    """
    pytest.importorskip("playwright")

    from tests.e2e.oidc_mock_provider import create_mock_oidc_provider

    idp_port = _free_port()
    idp_app = create_mock_oidc_provider(idp_port)
    idp_thread = threading.Thread(
        target=lambda: idp_app.run(
            host="127.0.0.1", port=idp_port, use_reloader=False, debug=False
        ),
        daemon=True,
    )
    idp_thread.start()
    _wait_until_up("127.0.0.1", idp_port)
    idp_base_url = f"http://127.0.0.1:{idp_port}"

    app_port = _free_port()
    app_base_url = f"http://127.0.0.1:{app_port}"

    oidc_env = {
        "OIDC_ENABLED": "true",
        "OIDC_ISSUER": idp_base_url,
        "OIDC_CLIENT_ID": "e2e-client",
        "OIDC_CLIENT_SECRET": "e2e-secret",
        "OIDC_REDIRECT_URI": f"{app_base_url}/oidc/callback",
        "OIDC_DISABLE_BASIC_AUTH": "true",
    }
    original_env = {k: os.environ.get(k) for k in oidc_env}
    os.environ.update(oidc_env)

    from config_oidc import OIDCConfig

    OIDCConfig.load_config()

    from flask_talisman import Talisman

    from app import CSP_POLICY, create_app, db

    # create_app() reads OIDCConfig (already up to date above) and,
    # since OIDC_ENABLED+is_configured() are true, calls
    # oidc_auth.init_app(), which makes a real HTTP discovery request to
    # idp_base_url - so the fake provider must already be running at
    # this point (done above).
    app = create_app("app.config.TestingConfig")
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TALISMAN_FORCE_HTTPS"] = True
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP_POLICY,
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    app_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=app_port, use_reloader=False, debug=False
        ),
        daemon=True,
    )
    app_thread.start()
    _wait_until_up("127.0.0.1", app_port)

    yield app_base_url, idp_base_url

    for k, v in original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    OIDCConfig.load_config()
