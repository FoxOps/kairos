"""Tests unitaires pour app/auth/user_manager.py (UserManager, sync OIDC)."""

import pytest

from app import db
from app.auth.user_manager import UserManager
from app.models import Group, User
from config_oidc import OIDCConfig


@pytest.fixture
def user_manager():
    return UserManager()


class TestSyncUserFromOidcInvalidData:
    def test_none_user_data_returns_none(self, test_app, user_manager):
        assert user_manager.sync_user_from_oidc(None) is None

    def test_missing_email_returns_none(self, test_app, user_manager):
        assert user_manager.sync_user_from_oidc({"name": "No Email"}) is None


class TestSyncUserFromOidcNewUser:
    def test_creates_new_user_with_default_group(self, test_app, user_manager):
        user = user_manager.sync_user_from_oidc(
            {"email": "new-oidc-user@example.com", "name": "New OIDC User"}
        )

        assert user is not None
        assert user.email == "new-oidc-user@example.com"
        assert user.name == "New OIDC User"
        assert user.is_admin is False
        assert user.password_hash is None

        default_group = Group.query.filter_by(name="Defaut").first()
        assert default_group is not None
        assert user.group_id == default_group.id

    def test_reuses_existing_default_group(self, test_app, user_manager):
        existing_default = Group(name="Defaut")
        db.session.add(existing_default)
        db.session.commit()

        user = user_manager.sync_user_from_oidc(
            {"email": "another@example.com", "name": "Another"}
        )

        assert user.group_id == existing_default.id
        assert Group.query.filter_by(name="Defaut").count() == 1

    def test_falls_back_to_username_when_no_name_claim(self, test_app, user_manager):
        user = user_manager.sync_user_from_oidc(
            {"email": "user2@example.com", "username": "user2handle"}
        )
        assert user.name == "user2handle"

    def test_falls_back_to_email_local_part_when_no_name_or_username(
        self, test_app, user_manager
    ):
        user = user_manager.sync_user_from_oidc({"email": "justme@example.com"})
        assert user.name == "justme"

    def test_roles_claim_admin_grants_is_admin(
        self, test_app, user_manager, monkeypatch
    ):
        monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "roles")
        user = user_manager.sync_user_from_oidc(
            {
                "email": "admin-oidc@example.com",
                "name": "Admin OIDC",
                "roles": ["admin"],
            }
        )
        assert user.is_admin is True

    def test_roles_claim_without_admin_does_not_grant_admin(
        self, test_app, user_manager, monkeypatch
    ):
        monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "roles")
        user = user_manager.sync_user_from_oidc(
            {"email": "user-oidc@example.com", "name": "User OIDC", "roles": ["viewer"]}
        )
        assert user.is_admin is False

    def test_roles_claim_accepts_single_string_not_just_list(
        self, test_app, user_manager, monkeypatch
    ):
        monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "roles")
        user = user_manager.sync_user_from_oidc(
            {
                "email": "single-role@example.com",
                "name": "Single Role",
                "roles": "admin",
            }
        )
        assert user.is_admin is True


class TestSyncUserFromOidcExistingUser:
    def test_updates_name_of_existing_user(self, test_app, test_group, user_manager):
        existing = User(
            name="Old Name", email="existing@example.com", group_id=test_group.id
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

        user = user_manager.sync_user_from_oidc(
            {"email": "existing@example.com", "name": "Updated Name"}
        )

        assert user.id == existing_id
        assert user.name == "Updated Name"
        assert User.query.count() == 1

    def test_does_not_touch_password_hash_of_local_user(
        self, test_app, test_group, user_manager
    ):
        existing = User(
            name="Local User", email="local@example.com", group_id=test_group.id
        )
        existing.set_password("supersecret")
        db.session.add(existing)
        db.session.commit()
        original_hash = existing.password_hash

        user = user_manager.sync_user_from_oidc(
            {"email": "local@example.com", "name": "Local User"}
        )

        assert user.password_hash == original_hash
        assert user.check_password("supersecret") is True

    def test_existing_admin_role_can_be_granted_via_oidc_sync(
        self, test_app, test_group, user_manager, monkeypatch
    ):
        monkeypatch.setattr(OIDCConfig, "ROLES_CLAIM", "roles")
        existing = User(
            name="Promoted User",
            email="promoted@example.com",
            group_id=test_group.id,
            is_admin=False,
        )
        db.session.add(existing)
        db.session.commit()

        user = user_manager.sync_user_from_oidc(
            {
                "email": "promoted@example.com",
                "name": "Promoted User",
                "roles": ["admin"],
            }
        )

        assert user.is_admin is True
