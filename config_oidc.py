"""
Configuration OIDC/SSO pour Leviia Schedule.

Ce module contient la configuration pour l'authentification OIDC (OpenID Connect)
avec des fournisseurs comme Keycloak, Okta, Auth0, etc.

L'authentification OIDC est optionnelle et peut être activée via des variables d'environnement.

NOTE: Ce module ne dépend pas de python-dotenv. Les variables d'environnement doivent
être définies directement dans l'environnement du système (via Docker, .env file monté,
etc.) avant l'import de ce module.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_bool_from_env(env_var, default=False):
    """Convertit une variable d'environnement en booléen.

    Accepte: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
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
            f"Valeur non reconnue pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}"
        )
        return default


class OIDCConfig:
    """Configuration OIDC/SSO."""

    # Variables de classe initialisées à None
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
        """Charge la configuration depuis les variables d'environnement.

        NOTE: Ce module suppose que les variables d'environnement sont déjà définies
        (via Docker, .env file, etc.) et ne dépend pas de python-dotenv.
        """
        cls.ENABLED = get_bool_from_env("OIDC_ENABLED", False)
        cls.ISSUER = os.environ.get("OIDC_ISSUER") or ""
        # Hôte utilisé par le conteneur pour les appels serveur-à-serveur
        # (token_endpoint, userinfo_endpoint, end_session_endpoint) une fois
        # l'issuer découvert. Utile quand OIDC_ISSUER pointe vers une adresse
        # joignable par le navigateur (LAN/domaine public) mais pas par le
        # conteneur (ex: fournisseur OIDC dans le même docker-compose,
        # joignable en interne via son nom de service). Vide par défaut :
        # les endpoints du document de découverte sont utilisés tels quels.
        cls.INTERNAL_ISSUER = os.environ.get("OIDC_INTERNAL_ISSUER") or ""
        cls.CLIENT_ID = os.environ.get("OIDC_CLIENT_ID") or ""
        cls.CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET") or ""
        cls.REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI") or ""
        # URL vers laquelle le fournisseur OIDC redirige après une
        # déconnexion RP-initiated (doit être enregistrée côté fournisseur,
        # ex: PostLogoutRedirectUris). Vide par défaut : le paramètre
        # post_logout_redirect_uri est simplement omis.
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

        # Log pour débogage
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
        """Vérifie si OIDC est correctement configuré."""
        # ✅ CORRECTION: Convertir chaque variable en booléen explicitement
        return (
            bool(cls.ENABLED)
            and bool(cls.ISSUER)
            and bool(cls.CLIENT_ID)
            and bool(cls.CLIENT_SECRET)
            and bool(cls.REDIRECT_URI)
        )

    @classmethod
    def get_config_dict(cls):
        """Retourne un dictionnaire avec la configuration OIDC."""
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


# Charger la configuration au moment de l'import
# NOTE: Cela charge la configuration une première fois, mais elle sera rechargée
# dans __init__.py après que Flask ait chargé sa configuration
OIDCConfig.load_config()
