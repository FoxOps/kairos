"""
User and Group repositories for Leviia Schedule.

Data access layer for User and Group models - no business logic, no
Flask request/response handling, just queries.
"""

from typing import List, Optional

from app import db
from app.models import User, Group


class UserRepository:
    """Data access for the User model."""

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_all() -> List[User]:
        return User.query.order_by(User.name).all()

    @staticmethod
    def get_for_schedule_group() -> List[User]:
        """Utilisateurs appartenant à un groupe participant au planning."""
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_schedule == True)
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def get_for_oncall_group() -> List[User]:
        """Utilisateurs appartenant à un groupe participant aux astreintes."""
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_oncall == True)
            .order_by(User.name)
            .all()
        )


class GroupRepository:
    """Data access for the Group model."""

    @staticmethod
    def get_by_id(group_id: int) -> Optional[Group]:
        return db.session.get(Group, group_id)

    @staticmethod
    def get_all() -> List[Group]:
        return Group.query.order_by(Group.name).all()
