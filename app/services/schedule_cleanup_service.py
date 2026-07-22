"""
Schedule cleanup service for Kairos.

Purges shifts/on-calls older than the admin-configured retention window
(SettingsService.get_schedule_retention_days(), default 365, 0 = never)
so the database doesn't accumulate years of past schedule data for no
real use - nothing in the app reads a shift/on-call once it's this far
in the past (the calendar's own display window is far narrower, see
ScheduleService). Called by scripts/cleanup_schedule_data.py (cron,
daily) - not exposed as an admin-UI-triggered action, unlike backups/
audit-log purge, since there's no legitimate reason to run it on demand
outside the retention window an admin already configured.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app import db
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.settings_service import SettingsService


@dataclass
class CleanupResult:
    retention_days: int
    shifts_deleted: int = 0
    oncalls_deleted: int = 0
    skipped: bool = False


class ScheduleCleanupService:
    """Retention-based purge of past shifts/on-calls."""

    @staticmethod
    def purge_old_data() -> CleanupResult:
        retention_days = SettingsService.get_schedule_retention_days()
        if retention_days <= 0:
            return CleanupResult(retention_days=retention_days, skipped=True)

        cutoff_date = date.today() - timedelta(days=retention_days)
        cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())

        shifts_deleted = ShiftRepository.delete_older_than(cutoff_date)
        oncalls_deleted = OnCallRepository.delete_older_than(cutoff_datetime)
        db.session.commit()

        return CleanupResult(
            retention_days=retention_days,
            shifts_deleted=shifts_deleted,
            oncalls_deleted=oncalls_deleted,
        )
