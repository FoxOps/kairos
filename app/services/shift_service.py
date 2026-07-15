"""
Shift service for Leviia Schedule.

Business logic for shift creation/update/deletion. Routes stay thin:
they parse the request, call this service, and turn the result into a
flash message / redirect / JSON response.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Shift, ShiftType, User
from app.repositories.shift_repository import ShiftRepository
from app.utils.helpers import can_add_shift, is_user_on_leave


class ShiftService:
    """Business logic for shifts."""

    @staticmethod
    def list_paginated(page: int, per_page: int):
        return ShiftRepository.list_paginated(page, per_page)

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

            if not can_add_shift(user, current_date, shift_type.name):
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
        return shifts_added, None

    @staticmethod
    def delete_shift(shift_id: int) -> Shift | None:
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return None
        ShiftRepository.delete(shift)
        db.session.commit()
        return shift

    @staticmethod
    def delete_all() -> int:
        count = ShiftRepository.count_all()
        if count > 0:
            ShiftRepository.delete_all()
            db.session.commit()
        return count

    @staticmethod
    def delete_all_for_user(user_id: int) -> int:
        count = ShiftRepository.count_for_user(user_id)
        if count > 0:
            ShiftRepository.delete_for_user(user_id)
            db.session.commit()
        return count

    @staticmethod
    def delete_for_day(on_date: date) -> int:
        count = ShiftRepository.count_for_date(on_date)
        if count > 0:
            ShiftRepository.delete_for_date(on_date)
            db.session.commit()
        return count

    @staticmethod
    def delete_for_week(monday: date) -> int:
        dates = [monday + timedelta(days=day) for day in range(5)]
        count = ShiftRepository.count_for_dates(dates)
        if count > 0:
            ShiftRepository.delete_for_dates(dates)
            db.session.commit()
        return count

    @staticmethod
    def api_create(
        user: User, shift_type: ShiftType, start_time: datetime, end_time: datetime
    ) -> tuple[Shift | None, str | None]:
        """Create a shift from the drag & drop API. Returns (shift, error_message)."""
        on_date = start_time.date()
        if on_date.weekday() >= 5:
            return None, "Impossible de créer un shift pour un week-end"

        if not can_add_shift(user, on_date, shift_type.name):
            return None, "Conflit détecté pour ce shift"

        shift = ShiftRepository.create(
            user.id, shift_type.id, start_time, end_time, on_date
        )
        db.session.commit()
        return shift, None

    @staticmethod
    def api_update(
        shift_id: int, new_start: datetime, new_end: datetime
    ) -> tuple[Shift | None, str | None]:
        """Update a shift from the drag & drop API. Returns (shift, error_message)."""
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return None, "Shift non trouvé"

        new_date = new_start.date()
        if new_date.weekday() >= 5:
            return None, "Impossible de déplacer vers un week-end (samedi/dimanche)"

        conflict = ShiftRepository.find_conflict(
            shift.user_id, new_date, exclude_id=shift_id
        )
        if conflict:
            return (
                None,
                f"Un shift existe déjà pour {shift.user.name} le {new_date.strftime('%d/%m/%Y')}",
            )

        # Originally missing: the creation path (api_create/
        # add_shifts_for_range) goes through can_add_shift(), which also
        # checks leave - drag & drop didn't, and could drop a shift onto
        # a day the user is on leave.
        if is_user_on_leave(shift.user_id, new_date):
            return (
                None,
                f"{shift.user.name} est en congé le {new_date.strftime('%d/%m/%Y')}",
            )

        shift.start_time = new_start
        shift.end_time = new_end
        shift.date = new_date
        db.session.commit()
        return shift, None

    @staticmethod
    def api_delete(shift_id: int) -> bool:
        shift = ShiftRepository.get_by_id(shift_id)
        if not shift:
            return False
        ShiftRepository.delete(shift)
        db.session.commit()
        return True
