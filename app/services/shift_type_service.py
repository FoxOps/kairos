"""
ShiftType service for Kairos.

Business logic for shift type creation/update/deletion (admin section).
"""

from flask_babel import gettext as _

from app import db
from app.models import ShiftType
from app.repositories.shift_repository import ShiftRepository, ShiftTypeRepository
from app.services.audit_service import AuditService


class ShiftTypeService:
    """Business logic for shift types."""

    @staticmethod
    def list_all() -> list[ShiftType]:
        return ShiftTypeRepository.get_all()

    @staticmethod
    def create(
        name: str, label: str, start_hour: int, end_hour: int
    ) -> tuple[ShiftType | None, str | None]:
        if ShiftTypeRepository.name_taken(name):
            return None, _("Un type de shift avec ce nom existe déjà.")

        if not (0 <= start_hour < 24) or not (0 <= end_hour < 24):
            return None, _("Les heures doivent être comprises entre 0 et 23.")
        if start_hour >= end_hour:
            return None, _("L'heure de début doit être antérieure à l'heure de fin.")

        shift_type = ShiftTypeRepository.create(name, label, start_hour, end_hour)
        db.session.commit()
        AuditService.log(
            "shift_type.create",
            resource_type="ShiftType",
            resource_id=shift_type.id,
            details=name,
        )
        return shift_type, None

    @staticmethod
    def update(
        shift_type_id: int, name: str, label: str, start_hour: int, end_hour: int
    ) -> tuple[ShiftType | None, str | None]:
        shift_type = ShiftTypeRepository.get_by_id(shift_type_id)
        if not shift_type:
            return None, None

        if ShiftTypeRepository.name_taken(name, exclude_id=shift_type_id):
            return None, _("Un type de shift avec ce nom existe déjà.")

        if not (0 <= start_hour < 24) or not (0 <= end_hour < 24):
            return None, _("Les heures doivent être comprises entre 0 et 23.")
        if start_hour >= end_hour:
            return None, _("L'heure de début doit être antérieure à l'heure de fin.")

        shift_type.name = name
        shift_type.label = label
        shift_type.start_hour = start_hour
        shift_type.end_hour = end_hour
        db.session.commit()
        AuditService.log(
            "shift_type.update",
            resource_type="ShiftType",
            resource_id=shift_type.id,
            details=name,
        )
        return shift_type, None

    @staticmethod
    def delete(shift_type_id: int) -> tuple[bool, str | None]:
        shift_type = ShiftTypeRepository.get_by_id(shift_type_id)
        if not shift_type:
            return False, None

        if ShiftRepository.exists_for_shift_type(shift_type_id):
            return (
                False,
                _(
                    "Impossible de supprimer ce type de shift : il est utilisé "
                    "dans des shifts existants."
                ),
            )

        deleted_name = shift_type.name
        ShiftTypeRepository.delete(shift_type)
        db.session.commit()
        AuditService.log(
            "shift_type.delete",
            resource_type="ShiftType",
            resource_id=shift_type_id,
            details=deleted_name,
        )
        return True, None
