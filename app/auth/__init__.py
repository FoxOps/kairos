"""
Module d'authentification pour Leviia Schedule.

Ce module contient les fonctionnalités d'authentification, y compris:
- Authentification basique (email/mot de passe)
- Authentification OIDC/SSO (optionnelle) utilisant Authlib
- Décorateurs pour les permissions
"""

from app.auth.decorators import admin_required, user_owns_resource
from app.auth.oidc_auth import OIDCAuthLib as OIDCAuth
from app.auth.user_manager import UserManager

# Exporter les classes et fonctions principales
__all__ = ["OIDCAuth", "UserManager", "admin_required", "user_owns_resource"]
