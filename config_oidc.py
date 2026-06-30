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
    
    # Activer l'authentification OIDC/SSO
    ENABLED = get_bool_from_env("OIDC_ENABLED", False)
    
    # URL du fournisseur OIDC (ex: Keycloak, Okta, etc.)
    # Exemple pour Keycloak: https://keycloak.example.com/realms/myrealm
    ISSUER = os.environ.get("OIDC_ISSUER") or ""
    
    # Client ID pour l'application OIDC
    CLIENT_ID = os.environ.get("OIDC_CLIENT_ID") or ""
    
    # Client Secret pour l'application OIDC
    CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET") or ""
    
    # URL de redirection après l'authentification OIDC
    # Doit correspondre à l'URL configurée dans le fournisseur OIDC
    REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI") or ""
    
    # Nom du claim pour l'email dans le token OIDC (par défaut: email)
    EMAIL_CLAIM = os.environ.get("OIDC_EMAIL_CLAIM") or "email"
    
    # Nom du claim pour le nom dans le token OIDC (par défaut: name)
    NAME_CLAIM = os.environ.get("OIDC_NAME_CLAIM") or "name"
    
    # Nom du claim pour le nom d'utilisateur dans le token OIDC (par défaut: preferred_username)
    USERNAME_CLAIM = os.environ.get("OIDC_USERNAME_CLAIM") or "preferred_username"
    
    # Nom du claim pour les groupes dans le token OIDC (optionnel)
    # Si défini, les groupes seront synchronisés avec les groupes locaux
    GROUPS_CLAIM = os.environ.get("OIDC_GROUPS_CLAIM") or ""
    
    # Nom du claim pour les rôles dans le token OIDC (optionnel)
    # Si défini, les rôles seront synchronisés avec les rôles locaux
    ROLES_CLAIM = os.environ.get("OIDC_ROLES_CLAIM") or ""
    
    # Algorithme de signature du token OIDC (par défaut: RS256)
    SIGNATURE_ALGORITHMS = os.environ.get("OIDC_SIGNATURE_ALGORITHMS") or "RS256"
    
    # Scope OIDC (par défaut: openid profile email)
    SCOPE = os.environ.get("OIDC_SCOPE") or "openid profile email"
    
    # Si vrai, l'authentification basique est désactivée lorsque OIDC est activé
    DISABLE_BASIC_AUTH = get_bool_from_env("OIDC_DISABLE_BASIC_AUTH", True)
    
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
