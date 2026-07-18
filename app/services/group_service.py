"""
Group service for Kairos.

Business logic for group creation/update/deletion (admin section).
"""

from flask_babel import gettext as _

from app import db
from app.models import Group
from app.repositories.user_repository import GroupRepository, UserRepository
from app.services.audit_service import AuditService


class GroupService:
    """Business logic for groups."""

    @staticmethod
    def list_all() -> list[Group]:
        return GroupRepository.get_all()

    @staticmethod
    def create(
        name: str, is_part_of_schedule: bool, is_part_of_oncall: bool
    ) -> tuple[Group | None, str | None]:
        if GroupRepository.name_taken(name):
            return None, _("Un groupe avec ce nom existe déjà.")

        group = GroupRepository.create(name, is_part_of_schedule, is_part_of_oncall)
        db.session.commit()
        AuditService.log(
            "group.create", resource_type="Group", resource_id=group.id, details=name
        )
        return group, None

    @staticmethod
    def update(
        group_id: int, name: str, is_part_of_schedule: bool, is_part_of_oncall: bool
    ) -> tuple[Group | None, str | None]:
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return None, None

        if GroupRepository.name_taken(name, exclude_id=group_id):
            return None, _("Un groupe avec ce nom existe déjà.")

        group.name = name
        group.is_part_of_schedule = is_part_of_schedule
        group.is_part_of_oncall = is_part_of_oncall
        db.session.commit()
        AuditService.log(
            "group.update", resource_type="Group", resource_id=group.id, details=name
        )
        return group, None

    @staticmethod
    def delete(group_id: int) -> tuple[bool, str | None]:
        group = GroupRepository.get_by_id(group_id)
        if not group:
            return False, None

        if UserRepository.exists_for_group(group_id):
            return (
                False,
                _(
                    "Impossible de supprimer ce groupe : des utilisateurs y sont "
                    "associés."
                ),
            )

        deleted_name = group.name
        GroupRepository.delete(group)
        db.session.commit()
        AuditService.log(
            "group.delete",
            resource_type="Group",
            resource_id=group_id,
            details=deleted_name,
        )
        return True, None
