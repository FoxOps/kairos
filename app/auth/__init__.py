"""
Module d'authentification pour Leviia Schedule.

Ce module contient les fonctionnalités d'authentification, y compris:
- Authentification basique (email/mot de passe)
- Authentification OIDC/SSO (optionnelle)
"""

from app.auth.oidc_auth import OIDCAuth
from app.auth.user_manager import UserManager

# Exporter les classes principales
__all__ = ['OIDCAuth', 'UserManager']
