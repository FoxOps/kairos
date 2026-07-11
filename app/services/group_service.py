"""
Group service for Leviia Schedule.

Business logic for group creation/update/deletion (admin section).
"""

from typing import List, Optional, Tuple

from app import db
from app.models import Group
from app.repositories.user_repository import GroupRepository, UserRepository


class GroupService:
    """Logique métier pour les groupes."""

    @staticmethod
    def list_all() -> List[Group]:
        return GroupRepository.get_all()

    @staticmethod
    def create(name: str, is_part_of_schedule: bool, is_part_of_oncall: bool) -> Tuple[Optional[Group], Optional[str]]:
        if GroupRepository.name_taken(name):
            return None, "Un groupe avec ce nom existe déjà."

        group = GroupRepository.create(name, is_part_of_schedule, is_part_of_oncall)
        db.session.commit()
        return group, None

    @staticmethod
    def update(
        group_id: int, name: str, is_part_of_schedule: bool, is_part_of_oncall: bool
    ) -> Tuple[Optional[Group], Optional[str]]:
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return None, None

        if GroupRepository.name_taken(name, exclude_id=group_id):
            return None, "Un groupe avec ce nom existe déjà."

        group.name = name
        group.is_part_of_schedule = is_part_of_schedule
        group.is_part_of_oncall = is_part_of_oncall
        db.session.commit()
        return group, None

    @staticmethod
    def delete(group_id: int) -> Tuple[bool, Optional[str]]:
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return False, None

        if UserRepository.exists_for_group(group_id):
            return False, "Impossible de supprimer ce groupe : des utilisateurs y sont associés."

        GroupRepository.delete(group)
        db.session.commit()
        return True, None
