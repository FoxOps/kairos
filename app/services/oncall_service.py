"""
OnCall service for Kairos.

Business logic for on-call creation/update/deletion. Routes stay thin:
they parse the request, call this service, and turn the result into a
flash message / redirect / JSON response.
"""

from datetime import date, datetime, timedelta

from flask_babel import gettext as _

from app import db
from app.models import OnCall, User
from app.repositories.oncall_repository import OnCallRepository
from app.services.audit_service import AuditService
from app.utils.helpers import (
    _get_overlapping_leave,
    can_add_oncall,
    check_oncall_rule_violations,
)


class OnCallService:
    """Business logic for on-call duties."""

    @staticmethod
    def list_paginated(
        page: int,
        per_page: int,
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        return OnCallRepository.list_paginated(
            page, per_page, user_id, group_id, date_from, date_to
        )

    @staticmethod
    def add_oncall(
        user: User, start_date: datetime
    ) -> tuple[OnCall | None, str | None]:
        """
        Create a one-week on-call starting from the given Friday 9pm.

        Returns:
            (oncall, error_message)
        """
        if start_date.weekday() != 4:
            return None, _("L'astreinte doit commencer un vendredi.")

        start_time = datetime.combine(start_date, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)

        if not can_add_oncall(user, start_time, end_time):
            return (
                None,
                _(
                    "Impossible d'ajouter cette astreinte (période déjà couverte "
                    "ou congé sur la période)."
                ),
            )

        oncall = OnCallRepository.create(user.id, start_time, end_time)
        db.session.commit()
        AuditService.log(
            "oncall.create",
            resource_type="OnCall",
            resource_id=oncall.id,
            details=f"{user.name} - {start_date.strftime('%d/%m/%Y')}",
        )
        return oncall, None

    @staticmethod
    def delete_oncall(oncall_id: int) -> OnCall | None:
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return None
        details = f"{oncall.user.name} - {oncall.start_time.strftime('%d/%m/%Y')}"
        OnCallRepository.delete(oncall)
        db.session.commit()
        AuditService.log(
            "oncall.delete",
            resource_type="OnCall",
            resource_id=oncall_id,
            details=details,
        )
        return oncall

    @staticmethod
    def delete_filtered(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Bulk-deletes every OnCall matching the given filters (no
        filters = matches everything, same as the old delete_all()) -
        backs the /oncall filter bar's "delete filtered result" action,
        replacing the old delete_all/delete_all_for_user."""
        count = OnCallRepository.delete_filtered(user_id, group_id, date_from, date_to)
        if count > 0:
            db.session.commit()
            AuditService.log(
                "oncall.bulk_delete",
                resource_type="OnCall",
                details=(
                    f"{count} on-call(s) - filters: user_id={user_id}, "
                    f"group_id={group_id}, date_from={date_from}, date_to={date_to}"
                ),
            )
        return count

    @staticmethod
    def api_delete(oncall_id: int) -> bool:
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return False
        details = f"{oncall.user.name} - {oncall.start_time.strftime('%d/%m/%Y')}"
        OnCallRepository.delete(oncall)
        db.session.commit()
        AuditService.log(
            "oncall.delete",
            resource_type="OnCall",
            resource_id=oncall_id,
            details=details,
        )
        return True

    @staticmethod
    def api_update(
        oncall_id: int, new_start: datetime, new_end: datetime
    ) -> tuple[OnCall | None, str | None]:
        """Update an on-call from the drag & drop API. Returns (oncall, error_message)."""
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return None, _("Astreinte non trouvée")

        if new_start.weekday() != 4:
            return None, _("L'astreinte doit commencer un vendredi")

        conflict = OnCallRepository.find_conflict(
            oncall.user_id, new_start, new_end, exclude_id=oncall_id
        )
        if conflict:
            return (
                None,
                _(
                    "Une astreinte existe déjà pour %(name)s pendant cette période",
                    name=oncall.user.name,
                ),
            )

        # Originally missing: the creation path (add_oncall) goes through
        # can_add_oncall(), which also checks leave over the period - drag
        # & drop didn't (same class of bug as ShiftService.api_update).
        if _get_overlapping_leave(oncall.user_id, new_start.date(), new_end.date()):
            return (
                None,
                _(
                    "%(name)s est en congé pendant cette période",
                    name=oncall.user.name,
                ),
            )

        # Same class of gap, for the configurable oncall_shift_overlap
        # rule - the creation path (add_oncall) already goes through
        # can_add_oncall(), which calls this too.
        violation = check_oncall_rule_violations(
            oncall.user, new_start, new_end, exclude_oncall_id=oncall_id
        )
        if violation is not None:
            return None, violation

        oncall.start_time = new_start
        oncall.end_time = new_end
        db.session.commit()
        AuditService.log(
            "oncall.update",
            resource_type="OnCall",
            resource_id=oncall.id,
            details=f"{oncall.user.name} -> {new_start.strftime('%d/%m/%Y')}",
        )
        return oncall, None
