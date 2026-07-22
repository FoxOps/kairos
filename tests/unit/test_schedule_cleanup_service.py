"""Tests for ScheduleCleanupService (retention-based purge of past
shifts/on-calls, Setting schedule_retention_days)."""

from datetime import date, datetime, timedelta

from app import db
from app.models import OnCall, Shift
from app.services import SettingsService
from app.services.schedule_cleanup_service import ScheduleCleanupService


def _make_shift(user_id, shift_type_id, on_date):
    shift = Shift(
        user_id=user_id,
        shift_type_id=shift_type_id,
        date=on_date,
        start_time=datetime.combine(on_date, datetime.min.time()).replace(hour=9),
        end_time=datetime.combine(on_date, datetime.min.time()).replace(hour=17),
    )
    db.session.add(shift)
    return shift


class TestScheduleCleanupService:
    def test_skips_when_retention_is_zero(self, test_app, test_user, test_shift_type):
        with test_app.app_context():
            SettingsService.set_schedule_retention_days(0)
            _make_shift(test_user.id, test_shift_type.id, date(2020, 1, 1))
            db.session.commit()

            result = ScheduleCleanupService.purge_old_data()

            assert result.skipped is True
            assert Shift.query.count() == 1

    def test_deletes_only_past_shifts_beyond_retention(
        self, test_app, test_user, test_shift_type
    ):
        with test_app.app_context():
            SettingsService.set_schedule_retention_days(30)
            old_shift = _make_shift(
                test_user.id, test_shift_type.id, date.today() - timedelta(days=60)
            )
            recent_shift = _make_shift(
                test_user.id, test_shift_type.id, date.today() - timedelta(days=10)
            )
            db.session.commit()
            old_id, recent_id = old_shift.id, recent_shift.id

            result = ScheduleCleanupService.purge_old_data()

            assert result.skipped is False
            assert result.shifts_deleted == 1
            assert db.session.get(Shift, old_id) is None
            assert db.session.get(Shift, recent_id) is not None

    def test_keeps_oncall_whose_end_time_is_still_after_cutoff(
        self, test_app, test_user
    ):
        """Gated on end_time, not start_time: an on-call that *started*
        before the cutoff but only *ends* after it (its 7-day span
        straddles the cutoff) must be kept - using start_time instead
        would delete it a week too early."""
        with test_app.app_context():
            SettingsService.set_schedule_retention_days(30)
            now = datetime.now()
            cutoff = now - timedelta(days=30)

            straddling_start = cutoff - timedelta(days=3)
            straddling = OnCall(
                user_id=test_user.id,
                start_time=straddling_start,
                end_time=straddling_start + timedelta(days=7),
            )
            db.session.add(straddling)

            truly_old_start = cutoff - timedelta(days=60)
            truly_old = OnCall(
                user_id=test_user.id,
                start_time=truly_old_start,
                end_time=truly_old_start + timedelta(days=7),
            )
            db.session.add(truly_old)
            db.session.commit()
            straddling_id, truly_old_id = straddling.id, truly_old.id

            result = ScheduleCleanupService.purge_old_data()

            assert result.oncalls_deleted == 1
            assert db.session.get(OnCall, truly_old_id) is None
            assert db.session.get(OnCall, straddling_id) is not None

    def test_default_retention_is_365_when_never_configured(
        self, test_app, test_user, test_shift_type
    ):
        with test_app.app_context():
            _make_shift(
                test_user.id, test_shift_type.id, date.today() - timedelta(days=400)
            )
            db.session.commit()

            result = ScheduleCleanupService.purge_old_data()

            assert result.retention_days == 365
            assert result.shifts_deleted == 1
