"""
User service for Kairos.

Business logic around which users a given viewer is allowed to see/pick
from (admins see everyone relevant, regular users only see themselves),
plus admin CRUD on users.
"""

import secrets

from flask_babel import gettext as _

from app import db
from app.models import User
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.utils.helpers.password_helpers import check_password_strength


class UserService:
    """Business logic for users."""

    @staticmethod
    def list_all() -> list[User]:
        return UserRepository.get_all()

    @staticmethod
    def list_for_schedule() -> list[User]:
        return UserRepository.get_for_schedule_group()

    @staticmethod
    def list_for_oncall() -> list[User]:
        return UserRepository.get_for_oncall_group()

    @staticmethod
    def visible_users_for_leave(current_user: User) -> list[User]:
        """An admin sees everyone, a regular user only sees themselves."""
        if current_user.is_admin:
            return UserRepository.get_all()
        return [current_user]

    @staticmethod
    def visible_users_for_schedule(current_user: User) -> list[User]:
        """An admin sees the schedule's users, a regular user only sees themselves."""
        if current_user.is_admin:
            return UserRepository.get_for_schedule_group()
        return [current_user]

    @staticmethod
    def create(
        name: str, email: str, group_id: int, password: str = ""  # nosec B107
    ) -> tuple[User | None, str | None, str | None]:
        """Returns (user, error, generated_password). generated_password
        is set only when the caller left `password` blank - a random
        strong password is generated instead of the old hardcoded
        "password123" fallback (itself now too weak to pass
        check_password_strength()), shown to the admin exactly once
        (same one-time-reveal pattern as ServiceAccount tokens) so they
        can hand it to the new user. Either way the account is created
        with must_change_password=True: a password chosen *for* the
        user, not by them, must be replaced on first login."""
        if UserRepository.email_taken(email):
            return None, _("Un utilisateur avec cet email existe déjà."), None

        generated_password = None
        effective_password = password
        if password:
            error = check_password_strength(password, name=name, email=email)
            if error:
                return None, error, None
        else:
            generated_password = secrets.token_urlsafe(16)
            effective_password = generated_password

        user = UserRepository.create(name, email, group_id)
        user.set_password(effective_password)
        user.must_change_password = True
        db.session.commit()
        AuditService.log(
            "user.create", resource_type="User", resource_id=user.id, details=email
        )
        return user, None, generated_password

    @staticmethod
    def update(
        user_id: int,
        name: str,
        email: str,
        group_id: int,
        is_admin: bool,
        password: str = "",  # nosec B107
    ) -> tuple[User | None, str | None]:
        user = UserRepository.get_by_id(user_id)
        if not user:
            return None, None

        if UserRepository.email_taken(email, exclude_id=user_id):
            return None, _("Un utilisateur avec cet email existe déjà.")

        if password:
            error = check_password_strength(password, name=name, email=email)
            if error:
                return None, error

        user.name = name
        user.email = email
        user.group_id = group_id
        user.is_admin = is_admin
        if password:
            user.set_password(password)
            # An admin is choosing this password on the user's behalf
            # (unlike auth.update_profile's self-service change, which
            # clears the flag itself right after) - force them to pick
            # their own on next login.
            user.must_change_password = True
        db.session.commit()
        AuditService.log(
            "user.update", resource_type="User", resource_id=user.id, details=email
        )
        return user, None

    @staticmethod
    def delete(user_id: int) -> tuple[bool, str | None]:
        user = UserRepository.get_by_id(user_id)
        if not user:
            return False, None

        if (
            ShiftRepository.exists_for_user(user_id)
            or OnCallRepository.exists_for_user(user_id)
            or LeaveRepository.exists_for_user(user_id)
        ):
            return (
                False,
                _(
                    "Impossible de supprimer cet utilisateur : il a des shifts, "
                    "astreintes ou congés associés."
                ),
            )

        deleted_email = user.email
        UserRepository.delete(user)
        db.session.commit()
        AuditService.log(
            "user.delete",
            resource_type="User",
            resource_id=user_id,
            details=deleted_email,
        )
        return True, None
