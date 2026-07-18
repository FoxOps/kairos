"""
Authentication module for Kairos.

This module contains the authentication features, including:
- Basic authentication (email/password)
- OIDC/SSO authentication (optional) using Authlib
- Permission decorators
"""

from app.auth.decorators import admin_required, user_owns_resource
from app.auth.oidc_auth import OIDCAuthLib as OIDCAuth
from app.auth.user_manager import UserManager

# Export the main classes and functions
__all__ = ["OIDCAuth", "UserManager", "admin_required", "user_owns_resource"]
