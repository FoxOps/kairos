"""
OIDC/SSO configuration for Leviia Schedule.

This module contains the configuration for OIDC (OpenID Connect)
authentication with providers like Keycloak, Okta, Auth0, etc.

OIDC authentication is optional and can be enabled via environment
variables.

NOTE: This module does not depend on python-dotenv. Environment
variables must be set directly in the system environment (via Docker, a
mounted .env file, etc.) before this module is imported.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_bool_from_env(env_var, default=False):
    """Convert an environment variable to a boolean.

    Accepts: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
    """
    value = os.environ.get(env_var)
    if value is None:
        return default

    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "y", "on"):
        return True
    elif value_lower in ("false", "0", "no", "n", "off"):
        return False
    else:
        logger.warning(
            f"Unrecognized value for {env_var}: '{value}'. Using default: {default}"
        )
        return default


class OIDCConfig:
    """OIDC/SSO configuration."""

    # Class variables initialized to None
    ENABLED = None
    ISSUER = None
    INTERNAL_ISSUER = None
    CLIENT_ID = None
    CLIENT_SECRET = None
    REDIRECT_URI = None
    POST_LOGOUT_REDIRECT_URI = None
    EMAIL_CLAIM = None
    NAME_CLAIM = None
    USERNAME_CLAIM = None
    GROUPS_CLAIM = None
    ROLES_CLAIM = None
    SIGNATURE_ALGORITHMS = None
    SCOPE = None
    DISABLE_BASIC_AUTH = None

    @classmethod
    def load_config(cls):
        """Load the configuration from environment variables.

        NOTE: This module assumes the environment variables are already
        set (via Docker, .env file, etc.) and does not depend on
        python-dotenv.
        """
        cls.ENABLED = get_bool_from_env("OIDC_ENABLED", False)
        cls.ISSUER = os.environ.get("OIDC_ISSUER") or ""
        # Host used by the container for server-to-server calls
        # (token_endpoint, userinfo_endpoint, end_session_endpoint) once
        # the issuer is discovered. Useful when OIDC_ISSUER points to an
        # address reachable by the browser (LAN/public domain) but not
        # by the container (e.g. OIDC provider in the same
        # docker-compose, reachable internally via its service name).
        # Empty by default: the discovery document's endpoints are used
        # as-is.
        cls.INTERNAL_ISSUER = os.environ.get("OIDC_INTERNAL_ISSUER") or ""
        cls.CLIENT_ID = os.environ.get("OIDC_CLIENT_ID") or ""
        cls.CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET") or ""
        cls.REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI") or ""
        # URL the OIDC provider redirects to after an RP-initiated
        # logout (must be registered on the provider's side, e.g.
        # PostLogoutRedirectUris). Empty by default: the
        # post_logout_redirect_uri parameter is simply omitted.
        cls.POST_LOGOUT_REDIRECT_URI = (
            os.environ.get("OIDC_POST_LOGOUT_REDIRECT_URI") or ""
        )
        cls.EMAIL_CLAIM = os.environ.get("OIDC_EMAIL_CLAIM") or "email"
        cls.NAME_CLAIM = os.environ.get("OIDC_NAME_CLAIM") or "name"
        cls.USERNAME_CLAIM = (
            os.environ.get("OIDC_USERNAME_CLAIM") or "preferred_username"
        )
        cls.GROUPS_CLAIM = os.environ.get("OIDC_GROUPS_CLAIM") or ""
        cls.ROLES_CLAIM = os.environ.get("OIDC_ROLES_CLAIM") or ""
        cls.SIGNATURE_ALGORITHMS = (
            os.environ.get("OIDC_SIGNATURE_ALGORITHMS") or "RS256"
        )
        cls.SCOPE = os.environ.get("OIDC_SCOPE") or "openid profile email"
        cls.DISABLE_BASIC_AUTH = get_bool_from_env("OIDC_DISABLE_BASIC_AUTH", True)

        # Debug logging
        logger.info(f"OIDC Config loaded - ENABLED: {cls.ENABLED}")
        logger.info(f"OIDC Config loaded - ISSUER: '{cls.ISSUER}'")
        logger.info(f"OIDC Config loaded - CLIENT_ID: '{cls.CLIENT_ID}'")
        logger.info(
            f"OIDC Config loaded - CLIENT_SECRET: {'***' if cls.CLIENT_SECRET else 'empty'}"
        )
        logger.info(f"OIDC Config loaded - REDIRECT_URI: '{cls.REDIRECT_URI}'")
        logger.info(f"OIDC Config loaded - is_configured: {cls.is_configured()}")

    @classmethod
    def is_configured(cls):
        """Check whether OIDC is properly configured."""
        return (
            bool(cls.ENABLED)
            and bool(cls.ISSUER)
            and bool(cls.CLIENT_ID)
            and bool(cls.CLIENT_SECRET)
            and bool(cls.REDIRECT_URI)
        )

    @classmethod
    def get_config_dict(cls):
        """Return a dictionary with the OIDC configuration."""
        return {
            "OIDC_ENABLED": cls.ENABLED,
            "OIDC_ISSUER": cls.ISSUER,
            "OIDC_CLIENT_ID": cls.CLIENT_ID,
            "OIDC_CLIENT_SECRET": cls.CLIENT_SECRET,
            "OIDC_REDIRECT_URI": cls.REDIRECT_URI,
            "OIDC_EMAIL_CLAIM": cls.EMAIL_CLAIM,
            "OIDC_NAME_CLAIM": cls.NAME_CLAIM,
            "OIDC_USERNAME_CLAIM": cls.USERNAME_CLAIM,
            "OIDC_GROUPS_CLAIM": cls.GROUPS_CLAIM,
            "OIDC_ROLES_CLAIM": cls.ROLES_CLAIM,
            "OIDC_SIGNATURE_ALGORITHMS": cls.SIGNATURE_ALGORITHMS,
            "OIDC_SCOPE": cls.SCOPE,
            "OIDC_DISABLE_BASIC_AUTH": cls.DISABLE_BASIC_AUTH,
        }


# Load the configuration at import time
# NOTE: This loads the configuration once, but it will be reloaded in
# __init__.py after Flask has loaded its own configuration
OIDCConfig.load_config()
