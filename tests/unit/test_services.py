"""
Unit tests for app/services/.

The business layer, until now only exercised indirectly through the
HTTP route tests (tests/integration/) - only ScheduleService had a few
direct tests. These tests call the services directly, without going
through the Flask test client.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

from app import db
from app.models import Leave, Shift
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

    def test_visible_users_for_oncall_admin_sees_oncall_group(
        self, test_app, test_user, admin_user
    ):
        visible = UserService.visible_users_for_oncall(admin_user)
        assert test_user in visible

    def test_visible_users_for_oncall_regular_sees_only_self(self, test_app, test_user):
        visible = UserService.visible_users_for_oncall(test_user)
        assert visible == [test_user]

    def test_create_success(self, test_app, test_group):
        user, error, generated_password = UserService.create(
            "New", "new-svc@test.com", test_group.id, "Correct-Horse-9"
        )
        assert error is None
        assert user is not None
        assert generated_password is None
        assert UserRepository.get_by_email("new-svc@test.com") is not None

    def test_create_generates_password_when_blank(self, test_app, test_group):
        """A blank password no longer silently falls back to the old
        hardcoded "password123" - a strong random one is generated
        instead, returned once for the admin to hand to the user."""
        user, error, generated_password = UserService.create(
            "New", "generated-pw@test.com", test_group.id
        )
        assert error is None
        assert generated_password is not None
        assert len(generated_password) >= 16
        assert user.check_password(generated_password)
        assert user.must_change_password is True

    def test_create_writes_audit_log_entry(self, test_app, test_group):
        from app.models import AuditLog

        user, error, _generated_password = UserService.create(
            "New", "audit-create@test.com", test_group.id, "Correct-Horse-9"
        )
        assert error is None
        entry = AuditLog.query.filter_by(action="user.create").first()
        assert entry is not None
        assert entry.resource_id == user.id
        assert entry.details == "audit-create@test.com"

    def test_create_rejects_duplicate_email(self, test_app, test_user, test_group):
        user, error, _generated_password = UserService.create(
            "Dup", test_user.email, test_group.id
        )
        assert user is None
        assert error == "Un utilisateur avec cet email existe déjà."

    def test_create_rejects_weak_password(self, test_app, test_group):
        user, error, _generated_password = UserService.create(
            "New", "weak-pw@test.com", test_group.id, "short1"
        )
        assert user is None
        assert error is not None

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

    def test_update_rejects_weak_password(self, test_app, test_user, test_group):
        updated, error = UserService.update(
            test_user.id,
            test_user.name,
            test_user.email,
            test_group.id,
            False,
            "short1",
        )
        assert updated is None
        assert error is not None

    def test_update_password_forces_change_on_next_login(
        self, test_app, test_user, test_group
    ):
        """An admin resetting someone else's password is choosing it for
        them, unlike auth.update_profile's self-service change - must be
        forced to pick their own on next login."""
        updated, error = UserService.update(
            test_user.id,
            test_user.name,
            test_user.email,
            test_group.id,
            False,
            "Correct-Horse-9",
        )
        assert error is None
        assert updated.must_change_password is True

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

    def test_delete_blocked_by_swap_request_as_requester(
        self, test_app, test_user, second_user, test_swap_request, test_swap_shift
    ):
        """test_swap_request has test_user as requester_id (a NOT NULL FK
        to user.id) - deleting them without this check would raise an
        uncaught IntegrityError on Postgres/MySQL (both supported
        engines; SQLite's lack of FK enforcement is why this was never
        caught by the existing suite). test_swap_shift is reassigned to
        second_user first so the pre-existing Shift check doesn't mask
        this one (shift_id is itself a NOT NULL FK on SwapRequest, so
        the shift can't just be deleted) - simulates an
        already-approved swap, where the requester no longer owns any
        shift but the historical SwapRequest row still references
        them."""
        test_swap_shift.user_id = second_user.id
        db.session.commit()

        ok, error = UserService.delete(test_user.id)
        assert ok is False
        assert error is not None

    def test_delete_blocked_by_swap_request_as_target(
        self, test_app, second_user, test_swap_request
    ):
        ok, error = UserService.delete(second_user.id)
        assert ok is False
        assert error is not None

    def test_delete_blocked_by_swap_request_as_reviewer(
        self, test_app, admin_user, test_swap_request
    ):
        from app.models import SwapRequest

        test_swap_request.mark_reviewed(admin_user.id, SwapRequest.APPROVED)
        db.session.commit()

        ok, error = UserService.delete(admin_user.id)
        assert ok is False
        assert error is not None


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

    def test_delete_missing_group(self, test_app):
        """The route's own delete_group() already 404s on a missing id
        before ever calling GroupService.delete() (see
        admin_group_routes.py), so this "not found" return is only
        reachable by calling the service directly."""
        ok, error = GroupService.delete(999999)
        assert ok is False
        assert error is None


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

    def test_update_rejects_invalid_hour_range(self, test_app, test_shift_type):
        updated, error = ShiftTypeService.update(
            test_shift_type.id, "morning", "Matin", 5, 30
        )
        assert updated is None
        assert "comprises entre 0 et 23" in error

    def test_update_rejects_start_after_end(self, test_app, test_shift_type):
        updated, error = ShiftTypeService.update(
            test_shift_type.id, "morning", "Matin", 18, 8
        )
        assert updated is None
        assert "antérieure" in error

    def test_delete_success(self, test_app, test_shift_type):
        ok, error = ShiftTypeService.delete(test_shift_type.id)
        assert ok is True
        assert error is None

    def test_delete_missing(self, test_app):
        """The route's own delete_shift_type() already 404s on a missing
        id before ever calling ShiftTypeService.delete() (see
        admin_shift_type_routes.py), so this "not found" return is only
        reachable by calling the service directly."""
        ok, error = ShiftTypeService.delete(999999)
        assert ok is False
        assert error is None

    def test_delete_blocked_by_existing_shift(
        self, test_app, test_shift_type, test_shift
    ):
        ok, error = ShiftTypeService.delete(test_shift_type.id)
        assert ok is False
        assert "utilisé" in error

    def test_delete_blocked_by_automation_rule_reference(
        self, test_app, test_shift_type
    ):
        """A ShiftType referenced by a configured shift_slots rule
        (app/utils/automation/rules/shift_slots.py) must not be
        deletable - doing so would silently break slot resolution for
        whichever role referenced it."""
        from app.models import AutomationRule
        from app.utils.automation.rules import ShiftSlotsRule

        default_params = ShiftSlotsRule.resolve()
        AutomationRule.set(
            "shift_slots",
            {**default_params, "rotation_shift_type_id": test_shift_type.id},
        )

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
        assert len(ShiftRepository.list_for_user(test_user.id)) == 5

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

    def test_delete_filtered_no_filters_deletes_everything(self, test_app, test_shift):
        count = ShiftService.delete_filtered()
        assert count == 1
        assert ShiftRepository.count_all() == 0

    def test_delete_filtered_by_user_id(self, test_app, test_user, test_shift):
        count = ShiftService.delete_filtered(user_id=test_user.id)
        assert count == 1

    def test_delete_filtered_by_date_range(self, test_app, test_shift):
        count = ShiftService.delete_filtered(
            date_from=test_shift.date, date_to=test_shift.date
        )
        assert count == 1

    def test_delete_filtered_by_ids(self, test_app, test_shift):
        count = ShiftService.delete_filtered(ids=[test_shift.id])
        assert count == 1
        assert ShiftRepository.count_all() == 0

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

    def test_api_create_rejects_conflict(self, test_app, test_user, test_shift_type):
        weekday = _next_weekday()
        start = datetime.combine(weekday, datetime.min.time())
        ShiftService.api_create(
            test_user, test_shift_type, start, start + timedelta(hours=8)
        )

        shift, error = ShiftService.api_create(
            test_user, test_shift_type, start, start + timedelta(hours=8)
        )
        assert shift is None
        assert "Conflit" in error

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

    def test_api_update_backward_compat_no_reassignment(self, test_app, test_shift):
        """The drag/resize call site never sends new_user_id/
        new_shift_type_id - calling api_update() with only
        (id, start, end), as it always has, must leave the owner/type
        untouched."""
        original_user_id = test_shift.user_id
        original_shift_type_id = test_shift.shift_type_id
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time())

        shift, error = ShiftService.api_update(
            test_shift.id, new_start, new_start + timedelta(hours=8)
        )

        assert error is None
        assert shift.user_id == original_user_id
        assert shift.shift_type_id == original_shift_type_id

    def test_api_update_reassigns_user(
        self, test_app, test_user, second_user, test_shift
    ):
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time())
        shift, error = ShiftService.api_update(
            test_shift.id,
            new_start,
            new_start + timedelta(hours=8),
            new_user_id=second_user.id,
        )
        assert error is None
        assert shift.user_id == second_user.id

    def test_api_update_reassign_to_nonexistent_shift_type(self, test_app, test_shift):
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time())
        shift, error = ShiftService.api_update(
            test_shift.id,
            new_start,
            new_start + timedelta(hours=8),
            new_shift_type_id=999999,
        )
        assert shift is None
        assert "Type de shift non trouv" in error

    def test_api_update_reassigns_shift_type(
        self, test_app, test_shift, afternoon_shift_type
    ):
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time())
        shift, error = ShiftService.api_update(
            test_shift.id,
            new_start,
            new_start + timedelta(hours=8),
            new_shift_type_id=afternoon_shift_type.id,
        )
        assert error is None
        assert shift.shift_type_id == afternoon_shift_type.id

    def test_api_update_reassignment_rejects_conflict_for_new_user(
        self, test_app, test_user, second_user, test_shift, test_shift_type
    ):
        """The conflict/leave/rule checks must run against the *new*
        user being reassigned to, not the shift's original owner."""
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time())
        new_end = new_start + timedelta(hours=8)
        other_shift = ShiftRepository.create(
            second_user.id, test_shift_type.id, new_start, new_end, target_day
        )
        db.session.commit()

        shift, error = ShiftService.api_update(
            test_shift.id,
            new_start,
            new_end,
            new_user_id=second_user.id,
        )
        assert shift is None
        assert second_user.name in error
        assert db.session.get(Shift, other_shift.id) is not None

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

    def test_api_update_rejects_move_onto_overlapping_oncall(
        self, test_app, test_user, test_shift, test_shift_type
    ):
        """Regression test: the drag & drop path used to skip the new
        configurable automation-rule checks entirely - same class of
        gap as the pre-existing leave check above. oncall_shift_overlap
        no longer blocks by default (on-call coexists with shifts), so
        this test explicitly opts into the stricter behavior to keep
        exercising the drag & drop path's rule-check wiring."""
        from app.models import AutomationRule, OnCall

        AutomationRule.set("oncall_shift_overlap", {"block": True})
        target_day = _next_weekday()
        new_start = datetime.combine(target_day, datetime.min.time()).replace(
            hour=test_shift_type.start_hour
        )
        new_end = datetime.combine(target_day, datetime.min.time()).replace(
            hour=test_shift_type.end_hour
        )
        db.session.add(
            OnCall(
                user_id=test_user.id,
                start_time=new_start - timedelta(hours=1),
                end_time=new_end + timedelta(hours=1),
            )
        )
        db.session.commit()

        shift, error = ShiftService.api_update(test_shift.id, new_start, new_end)
        assert shift is None
        assert "astreinte" in error

    def test_api_update_rejects_move_when_staffing_max_reached(
        self, test_app, test_user, second_user, test_shift, test_shift_type
    ):
        from app.models import AutomationRule

        target_day = _next_weekday()
        AutomationRule.set("staffing_limits", {str(test_shift_type.id): {"max": 1}})
        other_shift = Shift(
            date=target_day,
            start_time=datetime.combine(target_day, datetime.min.time()),
            end_time=datetime.combine(target_day, datetime.max.time()),
            user_id=second_user.id,
            shift_type_id=test_shift_type.id,
        )
        db.session.add(other_shift)
        db.session.commit()

        new_start = datetime.combine(target_day, datetime.min.time()).replace(
            hour=test_shift_type.start_hour
        )
        new_end = datetime.combine(target_day, datetime.min.time()).replace(
            hour=test_shift_type.end_hour
        )
        shift, error = ShiftService.api_update(test_shift.id, new_start, new_end)
        assert shift is None
        assert "effectif maximum" in error

    def test_api_delete(self, test_app, test_shift):
        assert ShiftService.api_delete(test_shift.id) is True
        assert ShiftService.api_delete(test_shift.id) is False


class TestOnCallService:
    def test_add_oncall_rejects_wrong_anchor_weekday(self, test_app, test_user):
        """Default OnCallAnchorRule (unconfigured) = Friday."""
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        start = datetime.combine(not_friday, datetime.min.time())
        oncall, error = OnCallService.add_oncall(test_user, start)
        assert oncall is None
        assert "jour configuré" in error

    def test_add_oncall_accepts_configured_non_friday_anchor(self, test_app, test_user):
        """Same fix as OnCallService.api_update() - add_oncall() must
        also respect the group's own configured OnCallAnchorRule
        instead of hardcoding Friday, or a group configured for a
        different day could never create an on-call at all."""
        from app.models import AutomationRule

        AutomationRule.set(
            "oncall_anchor",
            {"weekday": 2, "start_hour": 21, "end_hour": 7},  # Wednesday
            group=test_user.group,
        )
        db.session.commit()

        wednesday = date.today()
        while wednesday.weekday() != 2:
            wednesday += timedelta(days=1)
        start = datetime.combine(wednesday, datetime.min.time())

        oncall, error = OnCallService.add_oncall(test_user, start)
        assert error is None
        assert oncall is not None
        assert oncall.start_time.hour == 21

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

    def test_add_oncall_rejects_when_period_already_covered(self, test_app, test_user):
        friday = _next_friday()
        start = datetime.combine(friday, datetime.min.time())
        OnCallService.add_oncall(test_user, start)

        oncall, error = OnCallService.add_oncall(test_user, start)
        assert oncall is None
        assert "Impossible" in error

    def test_api_delete_success_and_missing(self, test_app, test_oncall):
        assert OnCallService.api_delete(test_oncall.id) is True
        assert OnCallService.api_delete(test_oncall.id) is False

    def test_delete_oncall(self, test_app, test_oncall):
        deleted = OnCallService.delete_oncall(test_oncall.id)
        assert deleted is not None
        assert OnCallRepository.get_by_id(test_oncall.id) is None

    def test_delete_oncall_missing(self, test_app):
        assert OnCallService.delete_oncall(999999) is None

    def test_delete_filtered_no_filters_deletes_everything(self, test_app, test_oncall):
        assert OnCallService.delete_filtered() == 1

    def test_delete_filtered_by_user_id(self, test_app, test_user, test_oncall):
        assert OnCallService.delete_filtered(user_id=test_user.id) == 1

    def test_delete_filtered_by_ids(self, test_app, test_oncall):
        assert OnCallService.delete_filtered(ids=[test_oncall.id]) == 1

    def test_api_update_rejects_wrong_anchor_weekday(self, test_app, test_oncall):
        """Default OnCallAnchorRule (unconfigured) = Friday - moving to
        any other weekday must still be rejected."""
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        new_start = datetime.combine(not_friday, datetime.min.time())
        oncall, error = OnCallService.api_update(
            test_oncall.id, new_start, new_start + timedelta(days=7)
        )
        assert oncall is None
        assert "jour configuré" in error

    def test_api_update_accepts_configured_non_friday_anchor(
        self, test_app, test_user, test_oncall
    ):
        """Real bug fix: api_update() used to hardcode weekday()!=4
        regardless of the group's own configured OnCallAnchorRule - the
        exact day a real generation run would use for this group must
        be accepted here too, not rejected as "not a Friday"."""
        from app.models import AutomationRule

        AutomationRule.set(
            "oncall_anchor",
            {"weekday": 2, "start_hour": 21, "end_hour": 7},  # Wednesday
            group=test_user.group,
        )
        db.session.commit()

        wednesday = date.today()
        while wednesday.weekday() != 2:
            wednesday += timedelta(days=1)
        new_start = datetime.combine(wednesday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)

        oncall, error = OnCallService.api_update(test_oncall.id, new_start, new_end)
        assert error is None
        assert oncall.start_time == new_start

    def test_api_update_missing(self, test_app):
        oncall, error = OnCallService.api_update(999999, datetime.now(), datetime.now())
        assert oncall is None
        assert error == "Astreinte non trouvée"

    def test_api_update_backward_compat_no_reassignment(self, test_app, test_oncall):
        """The drag/resize call site never sends new_user_id - calling
        api_update() with only (id, start, end) must leave the owner
        untouched."""
        original_user_id = test_oncall.user_id
        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)

        oncall, error = OnCallService.api_update(test_oncall.id, new_start, new_end)

        assert error is None
        assert oncall.user_id == original_user_id

    def test_api_update_reassigns_user(self, test_app, second_user, test_oncall):
        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)

        oncall, error = OnCallService.api_update(
            test_oncall.id, new_start, new_end, new_user_id=second_user.id
        )
        assert error is None
        assert oncall.user_id == second_user.id

    def test_api_update_reassign_to_nonexistent_user(self, test_app, test_oncall):
        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)

        oncall, error = OnCallService.api_update(
            test_oncall.id, new_start, new_end, new_user_id=999999
        )
        assert oncall is None
        assert "Utilisateur non trouv" in error

    def test_api_update_reassignment_rejects_conflict_for_new_user(
        self, test_app, second_user, test_oncall
    ):
        from app.models import OnCall

        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)
        db.session.add(
            OnCall(user_id=second_user.id, start_time=new_start, end_time=new_end)
        )
        db.session.commit()

        oncall, error = OnCallService.api_update(
            test_oncall.id, new_start, new_end, new_user_id=second_user.id
        )
        assert oncall is None
        assert second_user.name in error

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

    def test_api_update_rejects_move_onto_overlapping_shift(
        self, test_app, test_user, test_oncall, test_shift_type
    ):
        """Regression test: same class of gap as the leave check above,
        for the configurable oncall_shift_overlap rule.
        oncall_shift_overlap no longer blocks by default (on-call
        coexists with shifts), so this test explicitly opts into the
        stricter behavior to keep exercising the drag & drop path's
        rule-check wiring."""
        from app.models import AutomationRule

        AutomationRule.set("oncall_shift_overlap", {"block": True})
        friday = _next_friday()
        new_start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        new_end = new_start + timedelta(days=7, hours=-14)
        db.session.add(
            Shift(
                date=friday,
                start_time=datetime.combine(friday, datetime.min.time()).replace(
                    hour=test_shift_type.start_hour
                ),
                end_time=datetime.combine(friday, datetime.min.time()).replace(
                    hour=test_shift_type.end_hour
                ),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
        )
        db.session.commit()

        oncall, error = OnCallService.api_update(test_oncall.id, new_start, new_end)
        assert oncall is None
        assert "shift" in error


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

    def test_delete_filtered_no_filters_deletes_everything(self, test_app, test_leave):
        count = LeaveService.delete_filtered()
        assert count == 1
        assert LeaveRepository.get_by_id(test_leave.id) is None

    def test_delete_filtered_by_user_id(self, test_app, test_user, test_leave):
        count = LeaveService.delete_filtered(user_id=test_user.id)
        assert count == 1

    def test_delete_filtered_by_ids(self, test_app, test_leave):
        count = LeaveService.delete_filtered(ids=[test_leave.id])
        assert count == 1
        assert LeaveRepository.get_by_id(test_leave.id) is None

    def test_add_leave_notifies_admins_on_oncall_gap(
        self, test_app, admin_user, test_user, second_user
    ):
        """Regression test: when rebalance_after_leave() reports Friday
        dates left unassigned (legal 2-week on-call spacing constraint,
        see AdvancedShiftAutomation.rebalance_after_leave), LeaveService
        must notify admins - but only after rebalance_after_leave's own
        commit has actually succeeded (it always has, by the time this
        return value is available)."""
        from app.models import AppNotification

        gap_date = date(2026, 8, 21)
        with patch(
            "app.services.leave_service.AdvancedShiftAutomation.rebalance_after_leave",
            return_value=([], ["some message"], [gap_date], [], [], []),
        ):
            LeaveService.add_leave(
                test_user, date.today(), date.today() + timedelta(days=2)
            )

        notifs = AppNotification.query.filter_by(
            user_id=admin_user.id, notification_type="oncall_generation_gap"
        ).all()
        assert len(notifs) == 1
        assert "21/08/2026" in notifs[0].message

    def test_add_leave_notifies_admins_on_failed_shift_dates(
        self, test_app, admin_user, test_user, second_user
    ):
        """Bug hunt regression: a per-day shift regeneration failure
        (isolated to that day, see AdvancedShiftAutomation.
        rebalance_after_leave's docstring) must still reach admins,
        distinctly from the "no eligible user" oncall-gap case above -
        this one means an unexpected error happened, not just a
        legal-constraint gap."""
        from app.models import AppNotification

        failed_date = date(2026, 8, 21)
        with patch(
            "app.services.leave_service.AdvancedShiftAutomation.rebalance_after_leave",
            return_value=([], ["some message"], [], [failed_date], [], []),
        ):
            LeaveService.add_leave(
                test_user, date.today(), date.today() + timedelta(days=2)
            )

        notifs = AppNotification.query.filter_by(
            user_id=admin_user.id, notification_type="shift_generation_gap"
        ).all()
        assert len(notifs) == 1
        assert "21/08/2026" in notifs[0].message

    def test_add_leave_notifies_admins_on_failed_oncall_period(
        self, test_app, admin_user, test_user, second_user
    ):
        """Bug hunt regression: a failure in the on-call regeneration
        section itself (isolated from the shift days, see
        AdvancedShiftAutomation.rebalance_after_leave's docstring) must
        still reach admins."""
        from app.models import AppNotification

        period_start = date(2026, 8, 1)
        period_end = date(2026, 9, 1)
        with patch(
            "app.services.leave_service.AdvancedShiftAutomation.rebalance_after_leave",
            return_value=(
                [],
                ["some message"],
                [],
                [],
                [period_start, period_end],
                [],
            ),
        ):
            LeaveService.add_leave(
                test_user, date.today(), date.today() + timedelta(days=2)
            )

        notifs = AppNotification.query.filter_by(
            user_id=admin_user.id, notification_type="oncall_generation_gap"
        ).all()
        assert len(notifs) == 1
        assert "01/08/2026" in notifs[0].message
        assert "01/09/2026" in notifs[0].message

    def test_add_leave_notifies_admins_on_unfilled_shift_dates(
        self, test_app, admin_user, test_user, second_user
    ):
        """Real user report: rebalance_after_leave() reporting a day with
        zero shifts because no one was available (a business-rule case,
        not an exception) must reach admins too - previously invisible
        to LeaveService, unlike the equivalent on-call gap case above."""
        from app.models import AppNotification

        unfilled_date = date(2026, 8, 21)
        with patch(
            "app.services.leave_service.AdvancedShiftAutomation.rebalance_after_leave",
            return_value=([], ["some message"], [], [], [], [unfilled_date]),
        ):
            LeaveService.add_leave(
                test_user, date.today(), date.today() + timedelta(days=2)
            )

        notifs = AppNotification.query.filter_by(
            user_id=admin_user.id, notification_type="shift_generation_gap"
        ).all()
        assert len(notifs) == 1
        assert "21/08/2026" in notifs[0].message

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

    def test_rebalance_after_leave_exception_is_caught(self, test_app, test_leave):
        """_rebalance_after_leave()'s own except branch - only reached
        by a failure in AdvancedShiftAutomation.rebalance_after_leave's
        setup step itself (its per-day/per-section failures are already
        isolated and reported without raising, see the method's own
        docstring), so exercised here via a direct mock."""
        with patch(
            "app.services.leave_service.AdvancedShiftAutomation.rebalance_after_leave",
            side_effect=RuntimeError("boom"),
        ):
            deleted, rebalance_failed = LeaveService.api_delete(test_leave.id)
        assert deleted is True
        assert rebalance_failed is True

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

    def test_api_update_rejects_conflict(self, test_app, test_user, test_leave):
        """Moving a different leave onto test_leave's own dates - a
        different branch than test_api_update_rejects_end_before_start
        above."""
        other_leave = Leave(
            user_id=test_user.id,
            start_date=test_leave.start_date + timedelta(days=30),
            end_date=test_leave.end_date + timedelta(days=30),
        )
        db.session.add(other_leave)
        db.session.commit()

        leave, error, rebalance_failed = LeaveService.api_update(
            other_leave.id, test_leave.start_date, test_leave.end_date
        )
        assert leave is None
        assert "existe déjà" in error
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

    def test_export_shifts_all_scope_filters_by_group_ids(
        self, test_app, test_group, test_user, test_shift, second_user, test_shift_type
    ):
        """group_ids only applies on scope='all' - test_user (test_group)
        stays in, second_user (a different group) is excluded."""
        from datetime import timedelta

        from app import db
        from app.models import Group, Shift

        other_group = Group(name="Other Group Export Scope")
        db.session.add(other_group)
        db.session.commit()
        second_user.group_id = other_group.id
        db.session.commit()

        other_shift = Shift(
            user_id=second_user.id,
            shift_type_id=test_shift_type.id,
            date=test_shift.date + timedelta(days=1),
            start_time=test_shift.start_time + timedelta(days=1),
            end_time=test_shift.end_time + timedelta(days=1),
        )
        db.session.add(other_shift)
        db.session.commit()

        ics = ExportService.export_shifts("all", test_user, group_ids=[test_group.id])
        assert test_user.name in ics
        assert second_user.name not in ics

    def test_export_shifts_my_scope_ignores_group_ids(
        self, test_app, test_user, test_shift
    ):
        """scope='my' always means the token's own user's events,
        regardless of any group_ids passed alongside it."""
        ics = ExportService.export_shifts("my", test_user, group_ids=[999999])
        assert test_user.name in ics

    def test_export_shifts_all_scope_no_group_ids_is_unfiltered(
        self, test_app, test_group, test_user, test_shift, second_user, test_shift_type
    ):
        """group_ids=None (the default, no param) stays fully
        unfiltered - backward compat for already-copied export URLs."""
        from datetime import timedelta

        from app import db
        from app.models import Group, Shift

        other_group = Group(name="Other Group Export Unfiltered")
        db.session.add(other_group)
        db.session.commit()
        second_user.group_id = other_group.id
        db.session.commit()

        other_shift = Shift(
            user_id=second_user.id,
            shift_type_id=test_shift_type.id,
            date=test_shift.date + timedelta(days=1),
            start_time=test_shift.start_time + timedelta(days=1),
            end_time=test_shift.end_time + timedelta(days=1),
        )
        db.session.add(other_shift)
        db.session.commit()

        ics = ExportService.export_shifts("all", test_user)
        assert test_user.name in ics
        assert second_user.name in ics


class TestScheduleService:
    def test_get_calendar_events_uses_default_180_day_window(
        self, test_app, test_user, test_shift
    ):
        """get_calendar_events() - kept for callers that don't need a
        specific range (see its own docstring), currently only used
        via this default-window convenience wrapper around
        get_calendar_events_for_range()."""
        from app.services.schedule_service import ScheduleService

        events = ScheduleService.get_calendar_events(test_user)
        assert any(e["id"] == f"shift-{test_shift.id}" for e in events)
