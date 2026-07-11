"""
User service for Leviia Schedule.

Business logic around which users a given viewer is allowed to see/pick
from (admins see everyone relevant, regular users only see themselves).
"""

from typing import List

from app.models import User
from app.repositories.user_repository import UserRepository


class UserService:
    """Logique métier pour les utilisateurs."""

    @staticmethod
    def list_all() -> List[User]:
        return UserRepository.get_all()

    @staticmethod
    def list_for_schedule() -> List[User]:
        return UserRepository.get_for_schedule_group()

    @staticmethod
    def list_for_oncall() -> List[User]:
        return UserRepository.get_for_oncall_group()

    @staticmethod
    def visible_users_for_leave(current_user: User) -> List[User]:
        """Un admin voit tout le monde, un utilisateur normal ne se voit que lui-même."""
        if current_user.is_admin:
            return UserRepository.get_all()
        return [current_user]

    @staticmethod
    def visible_users_for_schedule(current_user: User) -> List[User]:
        """Un admin voit les utilisateurs du planning, un utilisateur normal ne se voit que lui-même."""
        if current_user.is_admin:
            return UserRepository.get_for_schedule_group()
        return [current_user]
