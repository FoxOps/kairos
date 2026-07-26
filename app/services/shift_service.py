"""
Shift service for Kairos.

Business logic for shift creation/update/deletion. Routes stay thin:
they parse the request, call this service, and turn the result into a
flash message / redirect / JSON response.
"""

from datetime import date, datetime, timedelta

from flask_babel import gettext as _

from app import db
from app.models import Shift, ShiftType, User
from app.repositories.shift_repository import ShiftRepository
from app.services.audit_service import AuditService
from app.utils.helpers import (
    can_add_shift,
    check_shift_rule_violations,
    is_user_on_leave,
)


class ShiftService:
    """Business logic for shifts."""

    @staticmethod
    def list_paginated(
        page: int,
        per_page: int,
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type_id: int | None = None,
    ):
        return ShiftRepository.list_paginated(
            page, per_page, user_id, group_id, date_from, date_to, shift_type_id
        )

    @staticmethod
    def add_shifts_for_range(
        user: User, shift_type: ShiftType, start_date: date, end_date: date
    ) -> tuple[list[str], date | None]:
        """
        Create one shift per business day between start_date and end_date
        (inclusive) for the given user.

        Returns:
            (dates_added, conflicting_date) - if a date is in conflict,
            nothing is committed (same behavior as the original: objects
            already added to the session without a commit are rolled back
            at the end of the request).
        """
        current_date = start_date
        shifts_added = []

        while current_date <= end_date:
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            if not can_add_shift(user, current_date, shift_type):
                return [], current_date

            start_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=shift_type.start_hour
            )
            end_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=shift_type.end_hour
            )
            ShiftRepository.create(
                user.id, shift_type.id, start_time, end_time, current_date
            )
            shifts_added.append(current_date.strftime("%d/%m/%Y"))
            current_date += timedelta(days=1)

        db.session.commit()
        if shifts_added:
            AuditService.log(
                "shift.create",
                resource_type="Shift",
                details=f"{user.name}: {len(shifts_added)} shift(s), {shifts_added[0]}-{shifts_added[-1]}",
            )
        return shifts_added, None

    @staticmethod
    def delete_shift(shift_id: int) -> Shift | None:
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return None
        details = f"{shift.user.name} - {shift.date.strftime('%d/%m/%Y')}"
        ShiftRepository.delete(shift)
        db.session.commit()
        AuditService.log(
            "shift.delete", resource_type="Shift", resource_id=shift_id, details=details
        )
        return shift

    @staticmethod
    def delete_filtered(
        user_id: int | None = None,
        group_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type_id: int | None = None,
    ) -> int:
        """Bulk-deletes every Shift matching the given filters (no
        filters = matches everything, same as the old delete_all()) -
        backs the /schedule filter bar's "delete filtered result"
        action, replacing the old delete_all/delete_all_for_user/
        delete_for_day/delete_for_week."""
        count = ShiftRepository.delete_filtered(
            user_id, group_id, date_from, date_to, shift_type_id
        )
        if count > 0:
            db.session.commit()
            AuditService.log(
                "shift.bulk_delete",
                resource_type="Shift",
                details=(
                    f"{count} shift(s) - filters: user_id={user_id}, "
                    f"group_id={group_id}, date_from={date_from}, "
                    f"date_to={date_to}, shift_type_id={shift_type_id}"
                ),
            )
        return count

    @staticmethod
    def api_create(
        user: User, shift_type: ShiftType, start_time: datetime, end_time: datetime
    ) -> tuple[Shift | None, str | None]:
        """Create a shift from the drag & drop API. Returns (shift, error_message)."""
        on_date = start_time.date()
        if on_date.weekday() >= 5:
            return None, _("Impossible de créer un shift pour un week-end")

        if not can_add_shift(user, on_date, shift_type):
            return None, _("Conflit détecté pour ce shift")

        shift = ShiftRepository.create(
            user.id, shift_type.id, start_time, end_time, on_date
        )
        db.session.commit()
        AuditService.log(
            "shift.create",
            resource_type="Shift",
            resource_id=shift.id,
            details=f"{user.name} - {on_date.strftime('%d/%m/%Y')}",
        )
        return shift, None

    @staticmethod
    def api_update(
        shift_id: int, new_start: datetime, new_end: datetime
    ) -> tuple[Shift | None, str | None]:
        """Update a shift from the drag & drop API. Returns (shift, error_message)."""
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return None, _("Shift non trouvé")

        new_date = new_start.date()
        if new_date.weekday() >= 5:
            return None, _("Impossible de déplacer vers un week-end (samedi/dimanche)")

        conflict = ShiftRepository.find_conflict(
            shift.user_id, new_date, exclude_id=shift_id
        )
        if conflict:
            return (
                None,
                _(
                    "Un shift existe déjà pour %(name)s le %(date)s",
                    name=shift.user.name,
                    date=new_date.strftime("%d/%m/%Y"),
                ),
            )

        # Originally missing: the creation path (api_create/
        # add_shifts_for_range) goes through can_add_shift(), which also
        # checks leave - drag & drop didn't, and could drop a shift onto
        # a day the user is on leave.
        if is_user_on_leave(shift.user_id, new_date):
            return (
                None,
                _(
                    "%(name)s est en congé le %(date)s",
                    name=shift.user.name,
                    date=new_date.strftime("%d/%m/%Y"),
                ),
            )

        # Same class of gap as the leave check above, for the
        # configurable automation rules (staffing_limits,
        # rest_after_oncall, oncall_shift_overlap) - the creation path
        # already goes through can_add_shift(), which calls this too.
        violation = check_shift_rule_violations(
            shift.user, new_date, shift.shift_type, exclude_shift_id=shift_id
        )
        if violation is not None:
            return None, violation

        shift.start_time = new_start
        shift.end_time = new_end
        shift.date = new_date
        db.session.commit()
        AuditService.log(
            "shift.update",
            resource_type="Shift",
            resource_id=shift.id,
            details=f"{shift.user.name} -> {new_date.strftime('%d/%m/%Y')}",
        )
        return shift, None

    @staticmethod
    def api_delete(shift_id: int) -> bool:
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return False
        details = f"{shift.user.name} - {shift.date.strftime('%d/%m/%Y')}"
        ShiftRepository.delete(shift)
        db.session.commit()
        AuditService.log(
            "shift.delete", resource_type="Shift", resource_id=shift_id, details=details
        )
        return True
