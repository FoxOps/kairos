"""
Leave service for Leviia Schedule.

Business logic for leave creation/update/deletion, including the
automatic shift rebalance that follows any leave change. Routes stay
thin: they parse the request, call this service, and turn the result
into a flash message / redirect / JSON response.
"""

from datetime import date

from flask_babel import gettext as _

from app import db
from app.models import Leave, User
from app.repositories.leave_repository import LeaveRepository
from app.services.app_notification_service import AppNotificationService
from app.services.apprise_notification_service import AppriseNotificationService
from app.services.audit_service import AuditService
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.helpers import can_add_leave, leave_keeps_minimum_headcount
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LeaveService:
    """Business logic for leaves."""

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return LeaveRepository.list_paginated(page, per_page)

    @staticmethod
    def add_leave(
        user: User, start_date: date, end_date: date
    ) -> tuple[Leave | None, list | None]:
        """
        Create a leave for the given user, then automatically rebalance
        the affected shifts.

        Returns:
            (leave, regenerated_shifts) on success, (None, None) otherwise.
            regenerated_shifts can be an empty list if the rebalance had
            nothing to recompute, or None if the rebalance itself failed
            (the leave is created regardless).
        """
        if not can_add_leave(user, start_date, end_date):
            return None, None

        leave = LeaveRepository.create(user.id, start_date, end_date)
        db.session.commit()
        AuditService.log(
            "leave.create",
            resource_type="Leave",
            resource_id=leave.id,
            details=f"{user.name}: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        )

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, regenerated_shifts

    @staticmethod
    def delete_leave(leave_id: int) -> tuple[Leave | None, list | None]:
        """Returns (deleted_leave, regenerated_shifts)."""
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return None, None

        details = f"{leave.user.name}: {leave.start_date.strftime('%d/%m/%Y')} - {leave.end_date.strftime('%d/%m/%Y')}"
        LeaveRepository.delete(leave)
        db.session.commit()
        AuditService.log(
            "leave.delete", resource_type="Leave", resource_id=leave_id, details=details
        )

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, regenerated_shifts

    @staticmethod
    def api_update(
        leave_id: int, new_start_date: date, new_end_date: date
    ) -> tuple[Leave | None, str | None, bool]:
        """Update a leave from the drag & drop API.

        Returns:
            (leave, error_message, rebalance_failed). rebalance_failed is
            True if the leave was updated successfully but the automatic
            shift rebalance failed.
        """
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return None, _("Congé non trouvé"), False

        if new_end_date < new_start_date:
            return None, _("La date de fin doit être après la date de début"), False

        conflict = LeaveRepository.find_conflict(
            leave.user_id, new_start_date, new_end_date, exclude_id=leave_id
        )
        if conflict:
            return (
                None,
                _(
                    "Un congé existe déjà pour %(name)s pendant cette période",
                    name=leave.user.name,
                ),
                False,
            )

        if not leave_keeps_minimum_headcount(
            leave.user, new_start_date, new_end_date, exclude_leave_id=leave_id
        ):
            return (
                None,
                _(
                    "Impossible : l'effectif disponible tomberait à 0 sur au moins "
                    "un jour de cette période"
                ),
                False,
            )

        leave.start_date = new_start_date
        leave.end_date = new_end_date
        db.session.commit()
        AuditService.log(
            "leave.update",
            resource_type="Leave",
            resource_id=leave.id,
            details=f"{leave.user.name}: {new_start_date.strftime('%d/%m/%Y')} - {new_end_date.strftime('%d/%m/%Y')}",
        )

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, None, regenerated_shifts is None

    @staticmethod
    def api_delete(leave_id: int) -> tuple[bool, bool]:
        """Returns (deleted, rebalance_failed)."""
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return False, False
        details = f"{leave.user.name}: {leave.start_date.strftime('%d/%m/%Y')} - {leave.end_date.strftime('%d/%m/%Y')}"
        LeaveRepository.delete(leave)
        db.session.commit()
        AuditService.log(
            "leave.delete", resource_type="Leave", resource_id=leave_id, details=details
        )
        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return True, regenerated_shifts is None

    @staticmethod
    def _rebalance_after_leave(leave: Leave) -> list | None:
        """Rebalance the shifts affected by a leave. None on failure."""
        try:
            regenerated_shifts, _messages, unfilled_oncall_dates = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)
            )
            # rebalance_after_leave's own commit() already succeeded at
            # this point (an exception would have skipped straight to
            # the except branch below) - safe to notify now, never
            # before (see AppNotificationService.notify_admins_oncall_gap()).
            if unfilled_oncall_dates:
                AppNotificationService.notify_admins_oncall_gap(unfilled_oncall_dates)
                AppriseNotificationService.notify(
                    "system",
                    _("Génération d'astreintes incomplète"),
                    _(
                        "Aucun utilisateur disponible dans le respect du délai "
                        "légal de 2 semaines pour : %(dates)s (rééquilibrage "
                        "après congé). Assignation manuelle nécessaire dans "
                        "/admin/automation.",
                        dates=", ".join(
                            d.strftime("%d/%m/%Y") for d in unfilled_oncall_dates
                        ),
                    ),
                )
            return regenerated_shifts
        except Exception:
            logger.exception(
                "Échec du rééquilibrage automatique des shifts après congé id=%s",
                leave.id,
            )
            return None
