"""
User management for OIDC authentication.

This module handles syncing users between the OIDC provider and
Leviia Schedule's local database.
"""

import logging

from app import db
from app.models import Group, User
from config_oidc import OIDCConfig

logger = logging.getLogger(__name__)


class UserManager:
    """Class managing OIDC users."""

    def sync_user_from_oidc(self, user_data):
        """Sync a user from OIDC data.

        Args:
            user_data: Dictionary containing the OIDC user information

        Returns:
            User: The synced user, or None on error
        """
        if not user_data or "email" not in user_data:
            logger.error("Invalid OIDC user data: missing email")
            return None

        email = user_data["email"]
        # Use 'name' as the primary field, falling back to 'username' or email
        name = user_data.get("name") or user_data.get("username") or email.split("@")[0]

        logger.info(f"[OIDC Sync] Starting sync for: {email}")

        # Look up the existing user by email
        user = User.query.filter_by(email=email).first()

        if user:
            logger.info(f"[OIDC Sync] Existing user found: {email} (ID: {user.id})")
            # Update the existing user
            user.name = name or user.name

            # If the user has no password (OIDC user), don't set one
            if not user.password_hash:
                pass  # OIDC users have no local password

            # Sync groups if configured
            if OIDCConfig.GROUPS_CLAIM and "groups" in user_data:
                self._sync_user_groups(user, user_data["groups"])

            # Sync roles if configured
            if OIDCConfig.ROLES_CLAIM and "roles" in user_data:
                self._sync_user_roles(user, user_data["roles"])

            db.session.commit()
            logger.info(f"Updated existing OIDC user: {email}")
            return user
        else:
            # Create a new user
            # OIDC users don't get a local password since they
            # authenticate via OIDC
            user = User(
                email=email,
                name=name,
                is_admin=False,  # OIDC users are not admin by default
            )

            # Find the default group
            default_group = Group.query.filter_by(name="Defaut").first()
            if not default_group:
                default_group = Group(name="Defaut")
                db.session.add(default_group)
                db.session.commit()
            user.group_id = default_group.id

            # Sync groups if configured
            if OIDCConfig.GROUPS_CLAIM and "groups" in user_data:
                self._sync_user_groups(user, user_data["groups"])

            # Sync roles if configured
            if OIDCConfig.ROLES_CLAIM and "roles" in user_data:
                self._sync_user_roles(user, user_data["roles"])

            db.session.add(user)
            db.session.commit()
            logger.info(f"[OIDC Sync] New OIDC user created: {email} (ID: {user.id})")
            return user

    def _sync_user_groups(self, user, oidc_groups):
        """Sync the user's groups with their OIDC groups.

        Args:
            user: User to sync
            oidc_groups: List of the user's OIDC groups
        """
        if not isinstance(oidc_groups, list):
            oidc_groups = [oidc_groups]

        # For now, we only log the OIDC groups
        # 1. Create local groups matching the OIDC groups
        logger.info(f"OIDC groups for {user.email}: {oidc_groups}")

        # OIDC groups could be used for additional authorization

    def _sync_user_roles(self, user, oidc_roles):
        """Sync the user's roles with their OIDC roles.

        Args:
            user: User to sync
            oidc_roles: List of the user's OIDC roles
        """
        if not isinstance(oidc_roles, list):
            oidc_roles = [oidc_roles]

        # Check whether the user has the admin role
        if "admin" in [role.lower() for role in oidc_roles]:
            user.is_admin = True
            logger.info(f"Admin role granted to {user.email} via OIDC")

        logger.info(f"OIDC roles for {user.email}: {oidc_roles}")

        # OIDC roles could be used for additional authorization
