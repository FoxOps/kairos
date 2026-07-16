"""
Unit tests for app/services/.

The business layer, until now only exercised indirectly through the
HTTP route tests (tests/integration/) - only ScheduleService had a few
direct tests. These tests call the services directly, without going
through the Flask test client.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.services.export_service import ExportService
from app.services.group_service import GroupService
from app.services.leave_service import LeaveService
from app.services.oncall_service import OnCallService
from app.services.shift_service import ShiftService
from app.services.shift_type_service import ShiftTypeService
from app.services.user_service import UserService


def _next_friday(from_date=None):
    d = from_date or date.today()
    days_ahead = (4 - d.weekday()) % 7
    days_ahead = days_ahead or 7
    return d + timedelta(days=days_ahead)


def _next_weekday(from_date=None):
    """Next business day (Monday-Friday) strictly after from_date."""
    d = (from_date or date.today()) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


class TestUserService:
    def test_list_all(self, test_app, test_user, admin_user):
        users = UserService.list_all()
        emails = [u.email for u in users]
        assert test_user.email in emails
        assert admin_user.email in emails

    def test_visible_users_for_leave_admin_sees_everyone(
        self, test_app, test_user, admin_user
    ):
        visible = UserService.visible_users_for_leave(admin_user)
        assert len(visible) >= 2

    def test_visible_users_for_leave_regular_sees_only_self(
        self, test_app, test_user, admin_user
    ):
        visible = UserService.visible_users_for_leave(test_user)
        assert visible == [test_user]

    def test_visible_users_for_schedule_regular_sees_only_self(
        self, test_app, test_user
    ):
        visible = UserService.visible_users_for_schedule(test_user)
        assert visible == [test_user]

    def test_create_success(self, test_app, test_group):
        user, error = UserService.create(
            "New", "new-svc@test.com", test_group.id, "pw123"
        )
        assert error is None
        assert user is not None
        assert UserRepository.get_by_email("new-svc@test.com") is not None

    def test_create_writes_audit_log_entry(self, test_app, test_group):
        from app.models import AuditLog

        user, error = UserService.create(
            "New", "audit-create@test.com", test_group.id, "pw123"
        )
        assert error is None
        entry = AuditLog.query.filter_by(action="user.create").first()
        assert entry is not None
        assert entry.resource_id == user.id
        assert entry.details == "audit-create@test.com"

    def test_create_rejects_duplicate_email(self, test_app, test_user, test_group):
        user, error = UserService.create("Dup", test_user.email, test_group.id)
        assert user is None
        assert error == "Un utilisateur avec cet email existe déjà."

    def test_update_success(self, test_app, test_user, test_group):
        updated, error = UserService.update(
            test_user.id, "Renamed", "renamed@test.com", test_group.id, True
        )
        assert error is None
        assert updated.name == "Renamed"
        assert updated.is_admin is True

    def test_update_rejects_duplicate_email(
        self, test_app, test_user, second_user, test_group
    ):
        updated, error = UserService.update(
            test_user.id, test_user.name, second_user.email, test_group.id, False
        )
        assert updated is None
        assert error == "Un utilisateur avec cet email existe déjà."

    def test_update_missing_user_returns_none_none(self, test_app, test_group):
        updated, error = UserService.update(
            999999, "X", "x@test.com", test_group.id, False
        )
        assert updated is None
        assert error is None

    def test_delete_success(self, test_app, test_user):
        ok, error = UserService.delete(test_user.id)
        assert ok is True
        assert error is None
        assert UserRepository.get_by_id(test_user.id) is None

    def test_delete_blocked_by_existing_shift(self, test_app, test_user, test_shift):
        ok, error = UserService.delete(test_user.id)
        assert ok is False
        assert "shifts" in error

    def test_delete_missing_user(self, test_app):
        ok, error = UserService.delete(999999)
        assert ok is False
        assert error is None


class TestGroupService:
    def test_create_success(self, test_app):
        group, error = GroupService.create("New Group", True, False)
        assert error is None
        assert group.is_part_of_schedule is True
        assert group.is_part_of_oncall is False

    def test_delete_writes_audit_log_entry(self, test_app):
        from app.models import AuditLog

        group, _error = GroupService.create("To Delete", False, False)
        group_id = group.id

        ok, error = GroupService.delete(group_id)
        assert ok is True
        assert error is None

        entry = AuditLog.query.filter_by(action="group.delete").first()
        assert entry is not None
        assert entry.resource_id == group_id
        assert entry.details == "To Delete"

    def test_create_rejects_duplicate_name(self, test_app, test_group):
        group, error = GroupService.create(test_group.name, True, True)
        assert group is None
        assert error == "Un groupe avec ce nom existe déjà."

    def test_update_success(self, test_app, test_group):
        updated, error = GroupService.update(
            test_group.id, "Renamed Group", False, False
        )
        assert error is None
        assert updated.name == "Renamed Group"

    def test_update_missing_group(self, test_app):
        updated, error = GroupService.update(999999, "X", True, True)
        assert updated is None
        assert error is None

    def test_delete_success(self, test_app, test_group):
        ok, error = GroupService.delete(test_group.id)
        assert ok is True
        assert error is None

    def test_delete_blocked_by_existing_user(self, test_app, test_group, test_user):
        ok, error = GroupService.delete(test_group.id)
        assert ok is False
        assert "utilisateurs" in error


class TestShiftTypeService:
    def test_create_success(self, test_app):
        shift_type, error = ShiftTypeService.create("night", "Nuit", 22, 23)
        assert error is None
        assert shift_type.name == "night"

    def test_create_writes_audit_log_entry(self, test_app):
        from app.models import AuditLog

        shift_type, _error = ShiftTypeService.create("night2", "Nuit2", 22, 23)

        entry = AuditLog.query.filter_by(action="shift_type.create").first()
        assert entry is not None
        assert entry.resource_id == shift_type.id
        assert entry.details == "night2"

    def test_create_rejects_duplicate_name(self, test_app, test_shift_type):
        shift_type, error = ShiftTypeService.create("morning", "Matin bis", 8, 16)
        assert shift_type is None
        assert "existe déjà" in error

    def test_create_rejects_invalid_hour_range(self, test_app):
        shift_type, error = ShiftTypeService.create("bad", "Bad", 5, 30)
        assert shift_type is None
        assert "comprises entre 0 et 23" in error

    def test_create_rejects_start_after_end(self, test_app):
        shift_type, error = ShiftTypeService.create("bad2", "Bad2", 18, 8)
        assert shift_type is None
        assert "antérieure" in error

    def test_update_success(self, test_app, test_shift_type):
        updated, error = ShiftTypeService.update(
            test_shift_type.id, "morning2", "Matin 2", 6, 14
        )
        assert error is None
        assert updated.name == "morning2"

    def test_update_missing(self, test_app):
        updated, error = ShiftTypeService.update(999999, "x", "X", 8, 16)
        assert updated is None
        assert error is None

    def test_delete_success(self, test_app, test_shift_type):
        ok, error = ShiftTypeService.delete(test_shift_type.id)
        assert ok is True
        assert error is None

    def test_delete_blocked_by_existing_shift(
        self, test_app, test_shift_type, test_shift
    ):
        ok, error = ShiftTypeService.delete(test_shift_type.id)
        assert ok is False
        assert "utilisé" in error


class TestShiftService:
    def test_add_shifts_for_range_skips_weekends(
        self, test_app, test_user, test_shift_type
    ):
        monday = date.today()
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        friday = monday + timedelta(days=4)

        added, conflict_date = ShiftService.add_shifts_for_range(
            test_user, test_shift_type, monday, friday
        )
        assert conflict_date is None
        assert len(added) == 5
        assert ShiftRepository.count_for_user(test_user.id) == 5

    def test_add_shifts_for_range_writes_audit_log_entry(
        self, test_app, test_user, test_shift_type
    ):
        from app.models import AuditLog

        weekday = _next_weekday()
        ShiftService.add_shifts_for_range(test_user, test_shift_type, weekday, weekday)

        entry = AuditLog.query.filter_by(action="shift.create").first()
        assert entry is not None
        assert test_user.name in entry.details

    def test_add_shifts_for_range_conflict_rolls_back(
        self, test_app, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        start = datetime.combine(weekday, datetime.min.time())
        ShiftRepository.create(
            test_user.id, test_shift_type.id, start, start + timedelta(hours=8), weekday
        )
        db.session.commit()

        added, conflict_date = ShiftService.add_shifts_for_range(
            test_user, test_shift_type, weekday, weekday
        )
        assert conflict_date == weekday
        assert added == []

    def test_delete_shift(self, test_app, test_shift):
        deleted = ShiftService.delete_shift(test_shift.id)
        assert deleted is not None
        assert ShiftRepository.get_by_id(test_shift.id) is None

    def test_delete_shift_missing(self, test_app):
        assert ShiftService.delete_shift(999999) is None

    def test_delete_all(self, test_app, test_shift):
        count = ShiftService.delete_all()
        assert count == 1
        assert ShiftRepository.count_all() == 0

    def test_delete_all_for_user(self, test_app, test_user, test_shift):
        count = ShiftService.delete_all_for_user(test_user.id)
        assert count == 1

    def test_delete_for_day(self, test_app, test_shift):
        count = ShiftService.delete_for_day(test_shift.date)
        assert count == 1

    def test_api_create_rejects_weekend(self, test_app, test_user, test_shift_type):
        saturday = date.today()
        while saturday.weekday() != 5:
            saturday += timedelta(days=1)
        start = datetime.combine(saturday, datetime.min.time())
        shift, error = ShiftService.api_create(
            test_user, test_shift_type, start, start + timedelta(hours=8)
        )
        assert shift is None
        assert "week-end" in error

    def test_api_create_success(self, test_app, test_user, test_shift_type):
        weekday = _next_weekday()
        start = datetime.combine(weekday, datetime.min.time())
        shift, error = ShiftService.api_create(
            test_user, test_shift_type, start, start + timedelta(hours=8)
        )
        assert error is None
        assert shift is not None

    def test_api_update_rejects_weekend(self, test_app, test_shift):
        saturday = date.today()
        while saturday.weekday() != 5:
            saturday += timedelta(days=1)
        new_start = datetime.combine(saturday, datetime.min.time())
        shift, error = ShiftService.api_update(
            test_shift.id, new_start, new_start + timedelta(hours=8)
        )
        assert shift is None
        assert "week-end" in error

    def test_api_update_missing_shift(self, test_app):
        shift, error = ShiftService.api_update(999999, datetime.now(), datetime.now())
        assert shift is None
        assert error == "Shift non trouvé"

    def test_api_update_rejects_move_onto_leave(self, test_app, test_user, test_shift):
        """Regression test: unlike api_create, api_update (drag & drop)
        used to skip leave revalidation and could drop a shift on a day
        the user is on leave."""
        target_day = _next_weekday()
        db.session.add(
            Leave(user_id=test_user.id, start_date=target_day, end_date=target_day)
        )
        db.session.commit()

        new_start = datetime.combine(target_day, datetime.min.time())
        shift, error = ShiftService.api_update(
            test_shift.id, new_start, new_start + timedelta(hours=8)
        )
        assert shift is None
        assert "congé" in error

    def test_api_delete(self, test_app, test_shift):
        assert ShiftService.api_delete(test_shift.id) is True
        assert ShiftService.api_delete(test_shift.id) is False


class TestOnCallService:
    def test_add_oncall_rejects_non_friday(self, test_app, test_user):
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        start = datetime.combine(not_friday, datetime.min.time())
        oncall, error = OnCallService.add_oncall(test_user, start)
        assert oncall is None
        assert "vendredi" in error

    def test_add_oncall_success(self, test_app, test_user):
        friday = _next_friday()
        start = datetime.combine(friday, datetime.min.time())
        oncall, error = OnCallService.add_oncall(test_user, start)
        assert error is None
        assert oncall is not None
        assert oncall.start_time.hour == 21

    def test_add_oncall_writes_audit_log_entry(self, test_app, test_user):
        from app.models import AuditLog

        friday = _next_friday()
        start = datetime.combine(friday, datetime.min.time())
        oncall, _error = OnCallService.add_oncall(test_user, start)

        entry = AuditLog.query.filter_by(action="oncall.create").first()
        assert entry is not None
        assert entry.resource_id == oncall.id

    def test_delete_oncall(self, test_app, test_oncall):
        deleted = OnCallService.delete_oncall(test_oncall.id)
        assert deleted is not None
        assert OnCallRepository.get_by_id(test_oncall.id) is None

    def test_delete_oncall_missing(self, test_app):
        assert OnCallService.delete_oncall(999999) is None

    def test_delete_all(self, test_app, test_oncall):
        assert OnCallService.delete_all() == 1

    def test_delete_all_for_user(self, test_app, test_user, test_oncall):
        assert OnCallService.delete_all_for_user(test_user.id) == 1

    def test_api_update_rejects_non_friday(self, test_app, test_oncall):
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        new_start = datetime.combine(not_friday, datetime.min.time())
        oncall, error = OnCallService.api_update(
            test_oncall.id, new_start, new_start + timedelta(days=7)
        )
        assert oncall is None
        assert "vendredi" in error

    def test_api_update_missing(self, test_app):
        oncall, error = OnCallService.api_update(999999, datetime.now(), datetime.now())
        assert oncall is None
        assert error == "Astreinte non trouvée"

    def test_api_update_rejects_move_onto_leave(self, test_app, test_user, test_oncall):
        """Regression test: same bug as ShiftService.api_update, on the
        on-call side - drag & drop used to skip leave revalidation."""
        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)
        db.session.add(
            Leave(
                user_id=test_user.id,
                start_date=new_start.date(),
                end_date=new_end.date(),
            )
        )
        db.session.commit()

        oncall, error = OnCallService.api_update(test_oncall.id, new_start, new_end)
        assert oncall is None
        assert "congé" in error


class TestLeaveService:
    def test_add_leave_success(self, test_app, test_user, second_user):
        leave, regenerated = LeaveService.add_leave(
            test_user, date.today(), date.today() + timedelta(days=2)
        )
        assert leave is not None
        assert LeaveRepository.get_by_id(leave.id) is not None

    def test_add_leave_writes_audit_log_entry(self, test_app, test_user, second_user):
        from app.models import AuditLog

        leave, _regenerated = LeaveService.add_leave(
            test_user, date.today(), date.today() + timedelta(days=2)
        )

        entry = AuditLog.query.filter_by(action="leave.create").first()
        assert entry is not None
        assert entry.resource_id == leave.id

    def test_add_leave_conflict_returns_none(self, test_app, test_user, test_leave):
        leave, regenerated = LeaveService.add_leave(
            test_user, test_leave.start_date, test_leave.end_date
        )
        assert leave is None
        assert regenerated is None

    def test_delete_leave(self, test_app, test_leave):
        deleted, regenerated = LeaveService.delete_leave(test_leave.id)
        assert deleted is not None
        assert LeaveRepository.get_by_id(test_leave.id) is None

    def test_delete_leave_missing(self, test_app):
        deleted, regenerated = LeaveService.delete_leave(999999)
        assert deleted is None
        assert regenerated is None

    def test_api_update_rejects_end_before_start(self, test_app, test_leave):
        leave, error, rebalance_failed = LeaveService.api_update(
            test_leave.id,
            test_leave.start_date,
            test_leave.start_date - timedelta(days=1),
        )
        assert leave is None
        assert "après" in error
        assert rebalance_failed is False

    def test_api_update_missing(self, test_app):
        leave, error, rebalance_failed = LeaveService.api_update(
            999999, date.today(), date.today()
        )
        assert leave is None
        assert error == "Congé non trouvé"
        assert rebalance_failed is False

    def test_api_delete(self, test_app, test_leave):
        deleted, rebalance_failed = LeaveService.api_delete(test_leave.id)
        assert deleted is True
        assert rebalance_failed is False
        deleted, rebalance_failed = LeaveService.api_delete(test_leave.id)
        assert deleted is False
        assert rebalance_failed is False

    def test_api_update_rejected_when_dropping_headcount_to_zero(
        self, test_app, test_leave
    ):
        """Regression test: api_update must also reject a leave move that
        would drop the headcount to 0 (test_leave belongs to the only
        schedule-eligible user in this test)."""
        new_start = date(2023, 12, 20)
        new_end = date(2023, 12, 20)
        leave, error, rebalance_failed = LeaveService.api_update(
            test_leave.id, new_start, new_end
        )
        assert leave is None
        assert "effectif" in error
        assert rebalance_failed is False


class TestExportService:
    def test_normalize_scope_valid(self):
        assert ExportService.normalize_scope("my") == "my"
        assert ExportService.normalize_scope("all") == "all"

    def test_normalize_scope_invalid_defaults_to_all(self):
        assert ExportService.normalize_scope("bogus") == "all"
        assert ExportService.normalize_scope(None) == "all"

    def test_export_shifts_my_scope(self, test_app, test_user, test_shift):
        ics = ExportService.export_shifts("my", test_user)
        assert "BEGIN:VCALENDAR" in ics

    def test_export_shifts_all_scope(self, test_app, test_user, test_shift):
        ics = ExportService.export_shifts("all", test_user)
        assert "BEGIN:VCALENDAR" in ics

    def test_export_oncall(self, test_app, test_user, test_oncall):
        ics = ExportService.export_oncall("my", test_user)
        assert "BEGIN:VCALENDAR" in ics

    def test_export_leaves(self, test_app, test_user, test_leave):
        ics = ExportService.export_leaves("my", test_user)
        assert "BEGIN:VCALENDAR" in ics
