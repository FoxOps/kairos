"""
Leave service for Leviia Schedule.

Business logic for leave creation/update/deletion, including the
automatic shift rebalance that follows any leave change. Routes stay
thin: they parse the request, call this service, and turn the result
into a flash message / redirect / JSON response.
"""

from datetime import date

from app import db
from app.models import Leave, User
from app.repositories.leave_repository import LeaveRepository
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.helpers import can_add_leave
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LeaveService:
    """Logique métier pour les congés."""

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return LeaveRepository.list_paginated(page, per_page)

    @staticmethod
    def list_in_window(window_start: date, window_end: date) -> list[Leave]:
        return LeaveRepository.list_in_window(window_start, window_end)

    @staticmethod
    def add_leave(
        user: User, start_date: date, end_date: date
    ) -> tuple[Leave | None, list | None]:
        """
        Crée un congé pour l'utilisateur donné, puis rééquilibre
        automatiquement les shifts affectés.

        Returns:
            (leave, regenerated_shifts) si succès, (None, None) sinon.
            regenerated_shifts peut être une liste vide si le
            rééquilibrage n'a rien eu à recalculer, ou None si le
            rééquilibrage lui-même a échoué (le congé est quand même créé).
        """
        if not can_add_leave(user, start_date, end_date):
            return None, None

        leave = LeaveRepository.create(user.id, start_date, end_date)
        db.session.commit()

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, regenerated_shifts

    @staticmethod
    def delete_leave(leave_id: int) -> tuple[Leave | None, list | None]:
        """Returns (leave_supprime, regenerated_shifts)."""
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return None, None

        LeaveRepository.delete(leave)
        db.session.commit()

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, regenerated_shifts

    @staticmethod
    def api_update(
        leave_id: int, new_start_date: date, new_end_date: date
    ) -> tuple[Leave | None, str | None, bool]:
        """Met à jour un congé depuis l'API drag & drop.

        Returns:
            (leave, error_message, rebalance_failed). rebalance_failed est
            True si le congé a bien été mis à jour mais que le
            rééquilibrage automatique des shifts a échoué.
        """
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return None, "Congé non trouvé", False

        if new_end_date < new_start_date:
            return None, "La date de fin doit être après la date de début", False

        conflict = LeaveRepository.find_conflict(
            leave.user_id, new_start_date, new_end_date, exclude_id=leave_id
        )
        if conflict:
            return (
                None,
                f"Un congé existe déjà pour {leave.user.name} pendant cette période",
                False,
            )

        leave.start_date = new_start_date
        leave.end_date = new_end_date
        db.session.commit()

        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return leave, None, regenerated_shifts is None

    @staticmethod
    def api_delete(leave_id: int) -> tuple[bool, bool]:
        """Returns (deleted, rebalance_failed)."""
        leave = LeaveRepository.get_by_id(leave_id)
        if not leave:
            return False, False
        LeaveRepository.delete(leave)
        db.session.commit()
        regenerated_shifts = LeaveService._rebalance_after_leave(leave)
        return True, regenerated_shifts is None

    @staticmethod
    def _rebalance_after_leave(leave: Leave) -> list | None:
        """Rééquilibre les shifts affectés par un congé. None si échec."""
        try:
            regenerated_shifts, _messages = (
                AdvancedShiftAutomation.rebalance_after_leave(leave, dry_run=False)
            )
            return regenerated_shifts
        except Exception:
            logger.exception(
                "Échec du rééquilibrage automatique des shifts après congé id=%s",
                leave.id,
            )
            return None
