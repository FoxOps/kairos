"""
OIDC/SSO authentication for Leviia Schedule using Authlib.

This module implements authentication via OpenID Connect with providers
like Keycloak, Okta, Auth0, etc. using the Authlib library.

Authlib is a modern, maintained library for OIDC authentication,
replacing the older flask-oidc library.
"""

import logging

from authlib.integrations.flask_client import OAuth
from flask import flash, session
from flask_login import login_user

from config_oidc import OIDCConfig

logger = logging.getLogger(__name__)


class OIDCAuthLib:
    """Class managing OIDC authentication with Authlib."""

    def __init__(self, app=None):
        """Initialize OIDC authentication with Authlib."""
        self.app = app
        self.oauth = None
        self.oidc_client = None
        self.authorization_endpoint = None
        self.token_endpoint = None
        self.userinfo_endpoint = None
        self.end_session_endpoint = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Flask application."""
        self.app = app
        self.oauth = OAuth(app)
        self._configure_oauth()

    def _configure_oauth(self):
        """Configure the OAuth/OIDC client."""
        if not self.oauth:
            logger.warning("OAuth is not initialized, cannot configure OIDC")
            return

        if not OIDCConfig.is_configured():
            logger.warning(
                "OIDC is not configured, skipping OAuth configuration. Check that OIDC_ENABLED=true, OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET and OIDC_REDIRECT_URI are set."
            )
            return

        try:
            issuer_url = OIDCConfig.ISSUER.rstrip("/")
            # OIDC_ISSUER must stay reachable by the browser (redirects).
            # If the OIDC provider isn't reachable by the container at that
            # same address (e.g. provider in the same docker-compose,
            # reachable internally via its service name), OIDC_INTERNAL_ISSUER
            # lets you specify the address to use for server-to-server calls
            # (discovery, token, userinfo).
            internal_issuer_url = (
                OIDCConfig.INTERNAL_ISSUER or OIDCConfig.ISSUER
            ).rstrip("/")
            server_metadata_url = (
                f"{internal_issuer_url}/.well-known/openid-configuration"
            )

            logger.info(f"Attempting OIDC configuration with issuer: {issuer_url}")
            logger.info(f"Discovery URL (internal): {server_metadata_url}")

            import requests

            try:
                response = requests.get(server_metadata_url, timeout=5)
                response.raise_for_status()
                discovery_doc = response.json()

                self.authorization_endpoint = discovery_doc.get(
                    "authorization_endpoint"
                )
                self.token_endpoint = discovery_doc.get("token_endpoint")
                self.userinfo_endpoint = discovery_doc.get("userinfo_endpoint")
                self.end_session_endpoint = discovery_doc.get("end_session_endpoint")

                if OIDCConfig.INTERNAL_ISSUER:
                    # The discovery document was fetched via the internal
                    # address, so all its endpoints reflect that host - some
                    # OIDC providers generate these URLs relative to the
                    # request host rather than their configured issuer.
                    # token/userinfo are called by this container: they stay
                    # as-is (already internal). authorization_endpoint and
                    # end_session_endpoint are both contacted by the browser
                    # (redirects): point them at the public issuer.
                    self.authorization_endpoint = self._rehost(
                        self.authorization_endpoint, issuer_url
                    )
                    self.end_session_endpoint = self._rehost(
                        self.end_session_endpoint, issuer_url
                    )

                logger.info(f"Authorization endpoint: {self.authorization_endpoint}")
                logger.info(f"Token endpoint: {self.token_endpoint}")
                logger.info(f"Userinfo endpoint: {self.userinfo_endpoint}")
                logger.info(f"End session endpoint: {self.end_session_endpoint}")

                logger.info("OIDC discovery document reachable")
            except requests.RequestException as e:
                logger.error(f"Could not reach the OIDC discovery document: {e}")
                logger.error(
                    f"Check that {server_metadata_url} is correct and reachable from this container"
                )
                logger.error(
                    "If using Docker, make sure the OIDC service is running and reachable (Docker service name or OIDC_INTERNAL_ISSUER)"
                )
                return

            self.oidc_client = self.oauth.register(
                name="oidc",
                server_metadata_url=server_metadata_url,
                client_kwargs={
                    "scope": OIDCConfig.SCOPE,
                },
            )

            self.oidc_client.client_id = OIDCConfig.CLIENT_ID
            self.oidc_client.client_secret = OIDCConfig.CLIENT_SECRET

            logger.info("Authlib OIDC client configured successfully")
            logger.debug(f"Client ID: {OIDCConfig.CLIENT_ID}")
            logger.debug(f"Issuer: {OIDCConfig.ISSUER}")
            logger.debug(f"Scope: {OIDCConfig.SCOPE}")
            logger.debug(f"Server metadata URL: {server_metadata_url}")

        except Exception as e:
            logger.error(f"Error configuring OAuth: {e}")
            self.oidc_client = None

    @staticmethod
    def _rehost(url, new_base_url):
        """Replace a URL's scheme+host while keeping its path/query."""
        if not url:
            return url
        from urllib.parse import urlsplit, urlunsplit

        new_parts = urlsplit(new_base_url)
        parts = urlsplit(url)
        return urlunsplit(
            (
                new_parts.scheme,
                new_parts.netloc,
                parts.path,
                parts.query,
                parts.fragment,
            )
        )

    def get_authorization_url(self, state=None, nonce=None):
        """Generate the OIDC authorization URL."""
        if not self.oidc_client:
            logger.error("OIDC client not configured. Check the OIDC configuration.")
            return None

        try:
            if not self.authorization_endpoint:
                logger.error("Authorization endpoint not available")
                return None

            if state is None:
                state = self._generate_state()
            if nonce is None:
                nonce = self._generate_nonce()

            # Store the state and nonce in the session
            session["oidc_state"] = state
            session["oidc_nonce"] = nonce

            logger.info(f"Generated state: {state}")
            logger.info(f"State stored in session: {session.get('oidc_state')}")

            from urllib.parse import urlencode

            params = {
                "response_type": "code",
                "client_id": OIDCConfig.CLIENT_ID,
                "redirect_uri": OIDCConfig.REDIRECT_URI,
                "scope": OIDCConfig.SCOPE,
                "state": state,
                "nonce": nonce,
            }

            return f"{self.authorization_endpoint}?{urlencode(params)}"

        except Exception as e:
            logger.error(f"Error generating the authorization URL: {e}")
            return None

    def _generate_state(self):
        """Generate a random state."""
        import secrets

        return secrets.token_urlsafe(32)

    def _generate_nonce(self):
        """Generate a random nonce."""
        import secrets

        return secrets.token_urlsafe(32)

    def exchange_code_for_token(self, code):
        """
        Exchange the authorization code for an OIDC token.
        """
        if not self.oidc_client:
            logger.error("OIDC client not configured")
            return None

        try:
            logger.info("Exchanging code for an OIDC token")

            import requests

            if not self.token_endpoint:
                logger.error("Token endpoint not available")
                return None

            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": OIDCConfig.REDIRECT_URI,
                "client_id": OIDCConfig.CLIENT_ID,
                "client_secret": OIDCConfig.CLIENT_SECRET,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            response = requests.post(
                self.token_endpoint, data=data, headers=headers, timeout=10
            )
            response.raise_for_status()

            token_data = response.json()

            # Store the id_token in the session for logout
            if "id_token" in token_data:
                session["oidc_id_token"] = token_data["id_token"]

            logger.info("OIDC token obtained successfully")
            return token_data

        except Exception as e:
            logger.error(f"Error exchanging the code for a token: {e}")
            return None

    def get_user_info(self, access_token):
        """Fetch user information from the OIDC provider."""
        if not self.oidc_client:
            logger.error("OIDC client not configured")
            return None

        try:
            logger.info("Fetching OIDC user information")

            import requests

            if not self.userinfo_endpoint:
                logger.error("Userinfo endpoint not available")
                return None

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            response = requests.get(self.userinfo_endpoint, headers=headers, timeout=10)
            response.raise_for_status()

            user_info = response.json()

            logger.info("OIDC user information fetched successfully")
            logger.debug(f"User info: {user_info}")
            return user_info

        except Exception as e:
            logger.error(f"Error fetching user information: {e}")
            return None

    def verify_token(self, token_data):
        """Verify the OIDC token's validity."""
        if not token_data:
            return False

        expires_at = token_data.get("expires_at")
        if expires_at:
            import time

            if time.time() > expires_at:
                logger.warning("OIDC token expired")
                return False

        return True

    def extract_user_info_from_token(self, token_data, user_info=None):
        """Extract user information from the OIDC token."""
        user_data = {}

        if user_info:
            email_claim = OIDCConfig.EMAIL_CLAIM
            if email_claim in user_info:
                user_data["email"] = user_info[email_claim]

            name_claim = OIDCConfig.NAME_CLAIM
            if name_claim in user_info:
                user_data["name"] = user_info[name_claim]

            username_claim = OIDCConfig.USERNAME_CLAIM
            if username_claim in user_info:
                user_data["username"] = user_info[username_claim]

            groups_claim = OIDCConfig.GROUPS_CLAIM
            if groups_claim and groups_claim in user_info:
                user_data["groups"] = user_info[groups_claim]

            roles_claim = OIDCConfig.ROLES_CLAIM
            if roles_claim and roles_claim in user_info:
                user_data["roles"] = user_info[roles_claim]

        elif token_data:
            import base64
            import json

            id_token = token_data.get("id_token") or token_data.get("access_token")
            if id_token:
                try:
                    parts = id_token.split(".")
                    if len(parts) >= 2:
                        payload = parts[1]
                        payload += "=" * (4 - len(payload) % 4)
                        decoded = base64.urlsafe_b64decode(payload)
                        token_payload = json.loads(decoded)

                        email_claim = OIDCConfig.EMAIL_CLAIM
                        if email_claim in token_payload:
                            user_data["email"] = token_payload[email_claim]

                        name_claim = OIDCConfig.NAME_CLAIM
                        if name_claim in token_payload:
                            user_data["name"] = token_payload[name_claim]

                        username_claim = OIDCConfig.USERNAME_CLAIM
                        if username_claim in token_payload:
                            user_data["username"] = token_payload[username_claim]

                        groups_claim = OIDCConfig.GROUPS_CLAIM
                        if groups_claim and groups_claim in token_payload:
                            user_data["groups"] = token_payload[groups_claim]

                        roles_claim = OIDCConfig.ROLES_CLAIM
                        if roles_claim and roles_claim in token_payload:
                            user_data["roles"] = token_payload[roles_claim]

                except Exception as e:
                    logger.error(f"Error decoding the token: {e}")

        return user_data

    def handle_oauth_callback(self, request):
        """Handle the OIDC callback after authentication."""
        logger.info(f"[callback] request.args: {dict(request.args)}")
        logger.info(f"[callback] session: {dict(session)}")

        # Verify the state
        state = request.args.get("state")
        session_state = session.get("oidc_state")

        logger.info(f"[callback] state received: {state}")
        logger.info(f"[callback] state in session: {session_state}")
        logger.info(f"[callback] state == session_state: {state == session_state}")

        if not state or state != session_state:
            logger.error("Invalid OIDC state")
            flash("Authentication error: invalid state", "danger")
            return None

        # Verify the code
        code = request.args.get("code")
        if not code:
            error = request.args.get("error", "Missing code")
            error_description = request.args.get("error_description", "")
            logger.error(f"OIDC error: {error} - {error_description}")
            flash(f"Authentication error: {error}", "danger")
            return None

        # Exchange the code for a token
        token_data = self.exchange_code_for_token(code)
        if not token_data:
            logger.error("Failed to exchange the code for a token")
            flash("Authentication error: failed to exchange the code", "danger")
            return None

        # Verify the token
        if not self.verify_token(token_data):
            logger.error("Invalid OIDC token")
            flash("Authentication error: invalid token", "danger")
            return None

        # Fetch user information
        access_token = token_data.get("access_token")
        user_info = None
        if access_token:
            user_info = self.get_user_info(access_token)

        # Extract user information
        user_data = self.extract_user_info_from_token(token_data, user_info)

        if not user_data or "email" not in user_data:
            logger.error("Could not extract the OIDC user's email")
            flash("Authentication error: could not fetch the email", "danger")
            return None

        return user_data

    def login_user(self, user_data):
        """Log in an OIDC user."""
        from app.auth.user_manager import UserManager

        user_manager = UserManager()

        # Sync or create the user
        user = user_manager.sync_user_from_oidc(user_data)

        if user:
            login_user(user)
            logger.info(f"OIDC user logged in: {user.email}")
            return user
        else:
            logger.error(f"Could not sync OIDC user: {user_data}")
            return None

    def build_logout_url(self, post_logout_redirect_uri=None):
        """
        Build the RP-initiated logout URL (end_session_endpoint).

        Without this, /logout only ends the local session: the session on
        the OIDC provider's side stays active, so the next redirect to the
        login screen silently re-authenticates the user via SSO (logout
        appears to do nothing).

        Args:
            post_logout_redirect_uri: URL the provider redirects to after
                logout (must be registered on the provider's side, e.g.
                PostLogoutRedirectUris)

        Returns:
            The provider's logout URL, or None if the endpoint isn't
            available (the provider doesn't offer it).
        """
        if not self.end_session_endpoint:
            return None

        from urllib.parse import urlencode

        params = {}
        id_token = session.pop("oidc_id_token", None)
        if id_token:
            params["id_token_hint"] = id_token
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri

        if not params:
            return self.end_session_endpoint

        return f"{self.end_session_endpoint}?{urlencode(params)}"


# Global instance
oidc_auth = OIDCAuthLib()
OIDCAuth = OIDCAuthLib
