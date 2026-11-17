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
from app.utils.helpers import oncall_validation_error


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
        ids: list[int] | None = None,
    ):
        return OnCallRepository.list_paginated(
            page, per_page, user_id, group_id, date_from, date_to, ids
        )

    @staticmethod
    def add_oncall(
        user: User, start_date: datetime
    ) -> tuple[OnCall | None, str | None]:
        """
        Create a one-week on-call starting from the given anchor day
        (OnCallAnchorRule, default Friday 21:00, configurable per Group).

        Returns:
            (oncall, error_message)
        """
        from app.utils.automation.rules import OnCallAnchorRule

        anchor = OnCallAnchorRule.resolve(group=user.group)
        if start_date.weekday() != anchor["weekday"]:
            return None, _(
                "L'astreinte doit commencer le jour configuré pour ce groupe."
            )

        start_time = datetime.combine(start_date, datetime.min.time()).replace(
            hour=anchor["start_hour"]
        )
        end_time = datetime.combine(
            start_date + timedelta(days=7), datetime.min.time()
        ).replace(hour=anchor["end_hour"])

        # The exact rule that blocks it, not a generic message (audit F03:
        # spacing used to be skipped here entirely).
        error = oncall_validation_error(user, start_time, end_time)
        if error is not None:
            return None, error

        oncall = OnCallRepository.create(
            user.id, start_time, end_time, group_id=user.group_id
        )
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
        ids: list[int] | None = None,
    ) -> int:
        """Bulk-deletes every OnCall matching the given filters (no
        filters = matches everything, same as the old delete_all()) -
        backs the /oncall filter bar's "delete filtered result" action,
        replacing the old delete_all/delete_all_for_user. `ids`: backs
        the checkbox row-selection "delete selection" action - same
        entrypoint, just another filter dimension."""
        count = OnCallRepository.delete_filtered(
            user_id, group_id, date_from, date_to, ids
        )
        if count > 0:
            db.session.commit()
            AuditService.log(
                "oncall.bulk_delete",
                resource_type="OnCall",
                details=(
                    f"{count} on-call(s) - filters: user_id={user_id}, "
                    f"group_id={group_id}, date_from={date_from}, "
                    f"date_to={date_to}, ids={ids}"
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
        oncall_id: int,
        new_start: datetime,
        new_end: datetime,
        new_user_id: int | None = None,
    ) -> tuple[OnCall | None, str | None]:
        """Update an on-call from the drag & drop API, or from the
        calendar's click-to-edit modal (which can also reassign the
        on-call person - `new_user_id`, optional, default None = "keep
        current", so the drag/resize call site - which never sends it -
        is unaffected). Returns (oncall, error_message)."""
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return None, _("Astreinte non trouvée")

        if new_user_id is not None and new_user_id != oncall.user_id:
            effective_user = db.session.get(User, new_user_id)
            if not effective_user:
                return None, _("Utilisateur non trouvé")
        else:
            effective_user = oncall.user

        # Same validator as creation, against the *effective* user (the
        # reassignment target, if any) and that user's group's anchor
        # rule: positive duration, anchor day+hour, configured weekly
        # end, leave, overlapping on-call, spacing, shift overlap (audit
        # F03/F09: a move used to check the weekday only, so an end
        # before the start or a 14h gap to the next week went through).
        violation = oncall_validation_error(
            effective_user, new_start, new_end, exclude_oncall_id=oncall_id
        )
        if violation is not None:
            return None, violation

        # Captured before mutating - oncall.user reflects the *new* FK
        # once the relationship refreshes after commit.
        original_user_name = oncall.user.name

        oncall.start_time = new_start
        oncall.end_time = new_end
        oncall.user_id = effective_user.id
        oncall.group_id = effective_user.group_id
        db.session.commit()

        details = f"{original_user_name} -> {new_start.strftime('%d/%m/%Y')}"
        if effective_user.name != original_user_name:
            details += f", user {original_user_name}->{effective_user.name}"
        AuditService.log(
            "oncall.update",
            resource_type="OnCall",
            resource_id=oncall.id,
            details=details,
        )
        return oncall, None
