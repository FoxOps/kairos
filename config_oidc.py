"""
Configuration OIDC/SSO pour Leviia Schedule.

Ce module contient la configuration pour l'authentification OIDC (OpenID Connect)
avec des fournisseurs comme Keycloak, Okta, Auth0, etc.

L'authentification OIDC est optionnelle et peut être activée via des variables d'environnement.
"""

import os
from config import get_bool_from_env


class OIDCConfig:
    """Configuration OIDC/SSO."""
    
    # Variables de classe initialisées à None
    ENABLED = None
    ISSUER = None
    CLIENT_ID = None
    CLIENT_SECRET = None
    REDIRECT_URI = None
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
        """Charge la configuration depuis les variables d'environnement."""
        cls.ENABLED = get_bool_from_env("OIDC_ENABLED", False)
        cls.ISSUER = os.environ.get("OIDC_ISSUER") or ""
        cls.CLIENT_ID = os.environ.get("OIDC_CLIENT_ID") or ""
        cls.CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET") or ""
        cls.REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI") or ""
        cls.EMAIL_CLAIM = os.environ.get("OIDC_EMAIL_CLAIM") or "email"
        cls.NAME_CLAIM = os.environ.get("OIDC_NAME_CLAIM") or "name"
        cls.USERNAME_CLAIM = os.environ.get("OIDC_USERNAME_CLAIM") or "preferred_username"
        cls.GROUPS_CLAIM = os.environ.get("OIDC_GROUPS_CLAIM") or ""
        cls.ROLES_CLAIM = os.environ.get("OIDC_ROLES_CLAIM") or ""
        cls.SIGNATURE_ALGORITHMS = os.environ.get("OIDC_SIGNATURE_ALGORITHMS") or "RS256"
        cls.SCOPE = os.environ.get("OIDC_SCOPE") or "openid profile email"
        cls.DISABLE_BASIC_AUTH = get_bool_from_env("OIDC_DISABLE_BASIC_AUTH", True)
    
    @classmethod
    def is_configured(cls):
        """Vérifie si OIDC est correctement configuré."""
        return (
            cls.ENABLED and 
            cls.ISSUER and 
            cls.CLIENT_ID and 
            cls.CLIENT_SECRET and 
            cls.REDIRECT_URI
        )
    
    @classmethod
    def get_config_dict(cls):
        """Retourne un dictionnaire avec la configuration OIDC."""
        return {
            'OIDC_ENABLED': cls.ENABLED,
            'OIDC_ISSUER': cls.ISSUER,
            'OIDC_CLIENT_ID': cls.CLIENT_ID,
            'OIDC_CLIENT_SECRET': cls.CLIENT_SECRET,
            'OIDC_REDIRECT_URI': cls.REDIRECT_URI,
            'OIDC_EMAIL_CLAIM': cls.EMAIL_CLAIM,
            'OIDC_NAME_CLAIM': cls.NAME_CLAIM,
            'OIDC_USERNAME_CLAIM': cls.USERNAME_CLAIM,
            'OIDC_GROUPS_CLAIM': cls.GROUPS_CLAIM,
            'OIDC_ROLES_CLAIM': cls.ROLES_CLAIM,
            'OIDC_SIGNATURE_ALGORITHMS': cls.SIGNATURE_ALGORITHMS,
            'OIDC_SCOPE': cls.SCOPE,
            'OIDC_DISABLE_BASIC_AUTH': cls.DISABLE_BASIC_AUTH,
        }


# Charger la configuration au moment de l'import
OIDCConfig.load_config()
