"""
User service for Leviia Schedule.

Business logic around which users a given viewer is allowed to see/pick
from (admins see everyone relevant, regular users only see themselves),
plus admin CRUD on users.
"""

from flask_babel import gettext as _

from app import db
from app.models import User
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository


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
        name: str, email: str, group_id: int, password: str = ""
    ) -> tuple[User | None, str | None]:
        if UserRepository.email_taken(email):
            return None, _("Un utilisateur avec cet email existe déjà.")

        user = UserRepository.create(name, email, group_id)
        user.set_password(password or "password123")
        db.session.commit()
        return user, None

    @staticmethod
    def update(
        user_id: int,
        name: str,
        email: str,
        group_id: int,
        is_admin: bool,
        password: str = "",
    ) -> tuple[User | None, str | None]:
        user = UserRepository.get_by_id(user_id)
        if not user:
            return None, None

        if UserRepository.email_taken(email, exclude_id=user_id):
            return None, _("Un utilisateur avec cet email existe déjà.")

        user.name = name
        user.email = email
        user.group_id = group_id
        user.is_admin = is_admin
        if password:
            user.set_password(password)
        db.session.commit()
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

        UserRepository.delete(user)
        db.session.commit()
        return True, None
