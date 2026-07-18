"""
Export service for Kairos.

Business logic for ICS export: resolving the exporting user (session or
ICS token), applying the all/my scope filter, and generating the ICS
content. Routes stay thin: they parse the request, call this service,
and turn the result into an HTTP response.
"""

from flask_login import current_user

from app.models import User
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.services.settings_service import SettingsService
from app.utils.export.ics_exporter import export_to_ics

VALID_SCOPES = ("all", "my")


class ExportService:
    """Business logic for ICS export."""

    @staticmethod
    def normalize_scope(scope: str | None) -> str:
        return scope if scope in VALID_SCOPES else "all"

    @staticmethod
    def resolve_user(token: str | None) -> User | None:
        """User for the export: authenticated session takes priority,
        otherwise the ICS token."""
        if current_user.is_authenticated:
            return current_user
        if token:
            return UserRepository.get_by_ics_token(token)
        return None

    @staticmethod
    def export_shifts(scope: str, user: User) -> str:
        shifts = (
            ShiftRepository.list_for_user(user.id)
            if scope == "my"
            else ShiftRepository.list_all_with_user()
        )
        return export_to_ics(
            shifts,
            f"Kairos - Shifts ({'All' if scope == 'all' else 'My'})",
            tz_name=SettingsService.get_default_timezone(),
        )

    @staticmethod
    def export_oncall(scope: str, user: User) -> str:
        on_calls = (
            OnCallRepository.list_for_user(user.id)
            if scope == "my"
            else OnCallRepository.list_all_with_user()
        )
        return export_to_ics(
            on_calls,
            f"Kairos - OnCall ({'All' if scope == 'all' else 'My'})",
            tz_name=SettingsService.get_default_timezone(),
        )

    @staticmethod
    def export_leaves(scope: str, user: User) -> str:
        leaves = (
            LeaveRepository.list_for_user(user.id)
            if scope == "my"
            else LeaveRepository.list_all_with_user()
        )
        return export_to_ics(
            leaves,
            f"Kairos - Leaves ({'All' if scope == 'all' else 'My'})",
            tz_name=SettingsService.get_default_timezone(),
        )
