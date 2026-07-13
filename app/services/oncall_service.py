"""
OnCall service for Leviia Schedule.

Business logic for on-call creation/update/deletion. Routes stay thin:
they parse the request, call this service, and turn the result into a
flash message / redirect / JSON response.
"""

from datetime import datetime, timedelta

from app import db
from app.models import OnCall, User
from app.repositories.oncall_repository import OnCallRepository
from app.utils.helpers import can_add_oncall


class OnCallService:
    """Logique métier pour les astreintes."""

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return OnCallRepository.list_paginated(page, per_page)

    @staticmethod
    def list_in_window(window_start: datetime, window_end: datetime) -> list[OnCall]:
        return OnCallRepository.list_in_window(window_start, window_end)

    @staticmethod
    def add_oncall(
        user: User, start_date: datetime
    ) -> tuple[OnCall | None, str | None]:
        """
        Crée une astreinte d'une semaine à partir du vendredi 21h donné.

        Returns:
            (oncall, error_message)
        """
        if start_date.weekday() != 4:
            return None, "L'astreinte doit commencer un vendredi."

        start_time = datetime.combine(start_date, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)

        if not can_add_oncall(user, start_time, end_time):
            return (
                None,
                "Impossible d'ajouter cette astreinte (période déjà couverte ou congé sur la période).",
            )

        oncall = OnCallRepository.create(user.id, start_time, end_time)
        db.session.commit()
        return oncall, None

    @staticmethod
    def delete_oncall(oncall_id: int) -> OnCall | None:
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return None
        OnCallRepository.delete(oncall)
        db.session.commit()
        return oncall

    @staticmethod
    def delete_all() -> int:
        count = OnCallRepository.count_all()
        if count > 0:
            OnCallRepository.delete_all()
            db.session.commit()
        return count

    @staticmethod
    def delete_all_for_user(user_id: int) -> int:
        count = OnCallRepository.count_for_user(user_id)
        if count > 0:
            OnCallRepository.delete_for_user(user_id)
            db.session.commit()
        return count

    @staticmethod
    def api_delete(oncall_id: int) -> bool:
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return False
        OnCallRepository.delete(oncall)
        db.session.commit()
        return True

    @staticmethod
    def api_update(
        oncall_id: int, new_start: datetime, new_end: datetime
    ) -> tuple[OnCall | None, str | None]:
        """Met à jour une astreinte depuis l'API drag & drop. Returns (oncall, error_message)."""
        oncall = OnCallRepository.get_by_id(oncall_id)
        if not oncall:
            return None, "Astreinte non trouvée"

        if new_start.weekday() != 4:
            return None, "L'astreinte doit commencer un vendredi"

        conflict = OnCallRepository.find_conflict(
            oncall.user_id, new_start, new_end, exclude_id=oncall_id
        )
        if conflict:
            return (
                None,
                f"Une astreinte existe déjà pour {oncall.user.name} pendant cette période",
            )

        oncall.start_time = new_start
        oncall.end_time = new_end
        db.session.commit()
        return oncall, None
