"""
Faux fournisseur OIDC minimal pour les tests E2E navigateur réel
(test_oidc_browser_flow.py).

But : exercer le vrai flux HTTP/navigateur (redirection vers l'IdP,
page de login réelle avec un clic, retour avec un code, échanges
serveur-à-serveur token/userinfo) sans dépendre de Docker (le projet a
déjà un service `oidc-mock` dans docker/docker-compose.yml, mais le
faire tourner ici ajouterait une dépendance Docker + réseau lourde pour
un test). Volontairement non conforme à la spec OIDC sur les points qui
n'affectent pas le code testé (pas de vérification stricte du code
d'autorisation, pas de signature JWT - app/auth/oidc_auth.py ne
vérifie jamais la signature d'un id_token, seulement son expiration).

Un seul utilisateur de test, en dur : voir MOCK_USER_EMAIL/MOCK_USER_NAME.
"""

import base64
import json
import time
from urllib.parse import urlencode

from flask import Flask, redirect, request

MOCK_AUTH_CODE = "mock-auth-code-123"  # noqa: S105 - code de test, pas un secret
MOCK_USER_EMAIL = "oidc-e2e-user@example.com"
MOCK_USER_NAME = "OIDC E2E User"


def _fake_jwt(payload: dict) -> str:
    """JWT non signé - oidc_auth.py décode le payload manuellement sans
    jamais vérifier de signature (voir extract_user_info_from_token)."""
    header = (
        base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    )
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fakesignature"


def create_mock_oidc_provider(port: int) -> Flask:
    """Crée le faux fournisseur OIDC, prêt à être lancé sur `port`."""
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
        """Page de "login" minimale - un vrai clic navigateur (Playwright),
        pas une redirection serveur directe, pour exercer un vrai
        aller-retour utilisateur comme un IdP réel le ferait."""
        redirect_uri = request.args.get("redirect_uri", "")
        state = request.args.get("state", "")
        return f"""
        <!doctype html>
        <html lang="fr">
        <body>
            <h1>Faux fournisseur OIDC (test)</h1>
            <p>Utilisateur : {MOCK_USER_EMAIL}</p>
            <form method="POST" action="/authorize/approve">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="state" value="{state}">
                <button type="submit" id="mock-idp-approve">Se connecter</button>
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
        return "Déconnecté (mock IdP)"

    return app
