"""
Minimal fake OIDC provider for the real-browser E2E tests
(test_oidc_browser_flow.py).

Purpose: exercise the real HTTP/browser flow (redirect to the IdP, a
real login page with a click, return with a code, server-to-server
token/userinfo exchanges) without depending on Docker (the project
already has an `oidc-mock` service in docker/docker-compose.yml, but
running it here would add a heavy Docker + network dependency for a
test). Deliberately non-compliant with the OIDC spec on points that
don't affect the code under test (no strict authorization-code check,
no JWT signature - app/auth/oidc_auth.py never verifies an id_token's
signature, only its expiration).

A single hardcoded test user: see MOCK_USER_EMAIL/MOCK_USER_NAME.
"""

import base64
import json
import time
from urllib.parse import urlencode

from flask import Flask, redirect, request

MOCK_AUTH_CODE = "mock-auth-code-123"  # noqa: S105 - test code, not a secret
MOCK_USER_EMAIL = "oidc-e2e-user@example.com"
MOCK_USER_NAME = "OIDC E2E User"


def _fake_jwt(payload: dict) -> str:
    """An unsigned JWT - oidc_auth.py decodes the payload manually
    without ever checking a signature (see extract_user_info_from_token)."""
    header = (
        base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    )
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fakesignature"


def create_mock_oidc_provider(port: int) -> Flask:
    """Create the fake OIDC provider, ready to run on `port`."""
    app = Flask(__name__)
    base_url = f"http://127.0.0.1:{port}"

    @app.route("/.well-known/openid-configuration")
    def discovery():
        return {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "userinfo_endpoint": f"{base_url}/userinfo",
            "end_session_endpoint": f"{base_url}/logout",
            "jwks_uri": f"{base_url}/jwks",
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["none"],
        }

    @app.route("/authorize")
    def authorize():
        """A minimal "login" page - a real browser click (Playwright),
        not a direct server redirect, to exercise a real user round
        trip the way a real IdP would."""
        redirect_uri = request.args.get("redirect_uri", "")
        state = request.args.get("state", "")
        return f"""
        <!doctype html>
        <html lang="fr">
        <body>
            <h1>Fake OIDC Provider (test)</h1>
            <p>User: {MOCK_USER_EMAIL}</p>
            <form method="POST" action="/authorize/approve">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="state" value="{state}">
                <button type="submit" id="mock-idp-approve">Log in</button>
            </form>
        </body>
        </html>
        """

    @app.route("/authorize/approve", methods=["POST"])
    def authorize_approve():
        redirect_uri = request.form.get("redirect_uri", "")
        state = request.form.get("state", "")
        params = urlencode({"code": MOCK_AUTH_CODE, "state": state})
        return redirect(f"{redirect_uri}?{params}")

    @app.route("/token", methods=["POST"])
    def token():
        id_token = _fake_jwt(
            {
                "email": MOCK_USER_EMAIL,
                "name": MOCK_USER_NAME,
                "preferred_username": "oidc-e2e-user",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
            }
        )
        return {
            "access_token": "mock-access-token",
            "id_token": id_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": time.time() + 3600,
        }

    @app.route("/userinfo")
    def userinfo():
        return {
            "email": MOCK_USER_EMAIL,
            "name": MOCK_USER_NAME,
            "preferred_username": "oidc-e2e-user",
        }

    @app.route("/logout")
    def logout():
        post_logout = request.args.get("post_logout_redirect_uri")
        if post_logout:
            return redirect(post_logout)
        return "Logged out (mock IdP)"

    return app
