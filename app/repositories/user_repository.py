"""
User and Group repositories for Leviia Schedule.

Data access layer for User and Group models - no business logic, no
Flask request/response handling, just queries.
"""

from app import db
from app.models import Group, User


class UserRepository:
    """Data access for the User model."""

    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_by_ics_token(token: str) -> User | None:
        return User.query.filter_by(ics_token=token).first()

    @staticmethod
    def get_all() -> list[User]:
        return User.query.order_by(User.name).all()

    @staticmethod
    def get_for_schedule_group() -> list[User]:
        """Utilisateurs appartenant à un groupe participant au planning."""
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_schedule.is_(True))
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def get_for_oncall_group() -> list[User]:
        """Utilisateurs appartenant à un groupe participant aux astreintes."""
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_oncall.is_(True))
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def email_taken(email: str, exclude_id: int | None = None) -> bool:
        query = User.query.filter(User.email == email)
        if exclude_id is not None:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def exists_for_group(group_id: int) -> bool:
        return User.query.filter_by(group_id=group_id).first() is not None

    @staticmethod
    def create(name: str, email: str, group_id: int) -> User:
        user = User(name=name, email=email, group_id=group_id)
        db.session.add(user)
        return user

    @staticmethod
    def delete(user: User) -> None:
        db.session.delete(user)


class GroupRepository:
    """Data access for the Group model."""

    @staticmethod
    def get_by_id(group_id: int) -> Group | None:
        return db.session.get(Group, group_id)

    @staticmethod
    def get_all() -> list[Group]:
        return Group.query.order_by(Group.name).all()

    @staticmethod
    def name_taken(name: str, exclude_id: int | None = None) -> bool:
        query = Group.query.filter(Group.name == name)
        if exclude_id is not None:
            query = query.filter(Group.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def create(name: str, is_part_of_schedule: bool, is_part_of_oncall: bool) -> Group:
        group = Group(
            name=name,
            is_part_of_schedule=is_part_of_schedule,
            is_part_of_oncall=is_part_of_oncall,
        )
        db.session.add(group)
        return group

    @staticmethod
    def delete(group: Group) -> None:
        db.session.delete(group)
