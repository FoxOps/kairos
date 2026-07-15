"""
Tests unitaires pour app/repositories/.

The data-access layer, until now only exercised indirectly through the
HTTP route tests (tests/integration/). These tests call the
repositories directly, without going through the Flask test client.
"""

from datetime import date, datetime, timedelta

from app import db
from app.repositories.leave_repository import LeaveRepository
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository, ShiftTypeRepository
from app.repositories.user_repository import GroupRepository, UserRepository


class TestUserRepository:
    def test_get_by_id_found(self, test_app, test_user):
        assert UserRepository.get_by_id(test_user.id).email == test_user.email

    def test_get_by_id_not_found(self, test_app):
        assert UserRepository.get_by_id(999999) is None

    def test_get_by_email(self, test_app, test_user):
        assert UserRepository.get_by_email(test_user.email).id == test_user.id
        assert UserRepository.get_by_email("nobody@nowhere.com") is None

    def test_get_by_ics_token(self, test_app, test_user):
        test_user.ics_token = "some-token"
        db.session.commit()
        assert UserRepository.get_by_ics_token("some-token").id == test_user.id
        assert UserRepository.get_by_ics_token("wrong-token") is None

    def test_get_all_ordered_by_name(self, test_app, test_group):
        UserRepository.create("Zoe", "zoe@test.com", test_group.id)
        UserRepository.create("Amy", "amy@test.com", test_group.id)
        db.session.commit()
        names = [u.name for u in UserRepository.get_all()]
        assert names == sorted(names)

    def test_get_for_schedule_group_excludes_other_groups(
        self, test_app, test_group, group_not_in_schedule
    ):
        UserRepository.create("In Schedule", "in@test.com", test_group.id)
        UserRepository.create(
            "Not In Schedule", "out@test.com", group_not_in_schedule.id
        )
        db.session.commit()
        emails = [u.email for u in UserRepository.get_for_schedule_group()]
        assert "in@test.com" in emails
        assert "out@test.com" not in emails

    def test_get_for_oncall_group_excludes_other_groups(
        self, test_app, test_group, group_not_in_schedule
    ):
        UserRepository.create("In Oncall", "in-oc@test.com", test_group.id)
        UserRepository.create(
            "Not In Oncall", "out-oc@test.com", group_not_in_schedule.id
        )
        db.session.commit()
        emails = [u.email for u in UserRepository.get_for_oncall_group()]
        assert "in-oc@test.com" in emails
        assert "out-oc@test.com" not in emails

    def test_email_taken(self, test_app, test_user):
        assert UserRepository.email_taken(test_user.email) is True
        assert UserRepository.email_taken("free@test.com") is False

    def test_email_taken_excludes_own_id(self, test_app, test_user):
        assert (
            UserRepository.email_taken(test_user.email, exclude_id=test_user.id)
            is False
        )

    def test_exists_for_group(self, test_app, test_group, group_not_in_schedule):
        assert UserRepository.exists_for_group(test_group.id) is False
        UserRepository.create("Someone", "someone@test.com", test_group.id)
        db.session.commit()
        assert UserRepository.exists_for_group(test_group.id) is True
        assert UserRepository.exists_for_group(group_not_in_schedule.id) is False

    def test_create_and_delete(self, test_app, test_group):
        user = UserRepository.create("New User", "new@test.com", test_group.id)
        db.session.commit()
        assert UserRepository.get_by_id(user.id) is not None

        UserRepository.delete(user)
        db.session.commit()
        assert UserRepository.get_by_id(user.id) is None


class TestGroupRepository:
    def test_get_by_id(self, test_app, test_group):
        assert GroupRepository.get_by_id(test_group.id).name == test_group.name
        assert GroupRepository.get_by_id(999999) is None

    def test_get_all_ordered_by_name(self, test_app):
        GroupRepository.create("Zeta", True, True)
        GroupRepository.create("Alpha", True, True)
        db.session.commit()
        names = [g.name for g in GroupRepository.get_all()]
        assert names == sorted(names)

    def test_name_taken(self, test_app, test_group):
        assert GroupRepository.name_taken(test_group.name) is True
        assert GroupRepository.name_taken("Unused Name") is False

    def test_name_taken_excludes_own_id(self, test_app, test_group):
        assert (
            GroupRepository.name_taken(test_group.name, exclude_id=test_group.id)
            is False
        )

    def test_create_and_delete(self, test_app):
        group = GroupRepository.create("Temp Group", False, True)
        db.session.commit()
        assert GroupRepository.get_by_id(group.id) is not None
        assert group.is_part_of_schedule is False
        assert group.is_part_of_oncall is True

        GroupRepository.delete(group)
        db.session.commit()
        assert GroupRepository.get_by_id(group.id) is None


class TestShiftTypeRepository:
    def test_get_by_id(self, test_app, test_shift_type):
        assert ShiftTypeRepository.get_by_id(test_shift_type.id).name == "morning"
        assert ShiftTypeRepository.get_by_id(999999) is None

    def test_name_taken(self, test_app, test_shift_type):
        assert ShiftTypeRepository.name_taken("morning") is True
        assert ShiftTypeRepository.name_taken("nonexistent") is False

    def test_create_and_delete(self, test_app):
        shift_type = ShiftTypeRepository.create("evening", "Soir", 18, 22)
        db.session.commit()
        assert ShiftTypeRepository.get_by_id(shift_type.id) is not None

        ShiftTypeRepository.delete(shift_type)
        db.session.commit()
        assert ShiftTypeRepository.get_by_id(shift_type.id) is None


class TestShiftRepository:
    def test_get_by_id(self, test_app, test_shift):
        assert ShiftRepository.get_by_id(test_shift.id) is not None
        assert ShiftRepository.get_by_id(999999) is None

    def test_list_for_user(self, test_app, test_user, test_shift):
        shifts = ShiftRepository.list_for_user(test_user.id)
        assert len(shifts) == 1
        assert shifts[0].id == test_shift.id

    def test_find_conflict(self, test_app, test_user, test_shift):
        conflict = ShiftRepository.find_conflict(test_user.id, test_shift.date)
        assert conflict is not None
        assert conflict.id == test_shift.id

    def test_find_conflict_excludes_own_id(self, test_app, test_user, test_shift):
        conflict = ShiftRepository.find_conflict(
            test_user.id, test_shift.date, exclude_id=test_shift.id
        )
        assert conflict is None

    def test_find_conflict_none_on_different_date(
        self, test_app, test_user, test_shift
    ):
        other_date = test_shift.date + timedelta(days=1)
        assert ShiftRepository.find_conflict(test_user.id, other_date) is None

    def test_count_all_and_for_user(self, test_app, test_user, test_shift):
        assert ShiftRepository.count_all() == 1
        assert ShiftRepository.count_for_user(test_user.id) == 1

    def test_exists_for_user(self, test_app, test_user, second_user, test_shift):
        assert ShiftRepository.exists_for_user(test_user.id) is True
        assert ShiftRepository.exists_for_user(second_user.id) is False

    def test_exists_for_shift_type(
        self, test_app, test_shift_type, afternoon_shift_type, test_shift
    ):
        assert ShiftRepository.exists_for_shift_type(test_shift_type.id) is True
        assert ShiftRepository.exists_for_shift_type(afternoon_shift_type.id) is False

    def test_delete_in_date_range(
        self, test_app, test_user, test_shift_type, test_shift
    ):
        deleted = ShiftRepository.delete_in_date_range(test_shift.date, test_shift.date)
        db.session.commit()
        assert deleted == 1
        assert ShiftRepository.get_by_id(test_shift.id) is None

    def test_delete_all(self, test_app, test_shift):
        ShiftRepository.delete_all()
        db.session.commit()
        assert ShiftRepository.count_all() == 0

    def test_delete_for_user(self, test_app, test_user, test_shift):
        ShiftRepository.delete_for_user(test_user.id)
        db.session.commit()
        assert ShiftRepository.count_for_user(test_user.id) == 0

    def test_create(self, test_app, test_user, test_shift_type):
        start = datetime.combine(date.today(), datetime.min.time())
        end = start + timedelta(hours=8)
        shift = ShiftRepository.create(
            test_user.id, test_shift_type.id, start, end, date.today()
        )
        db.session.commit()
        assert ShiftRepository.get_by_id(shift.id) is not None


class TestLeaveRepository:
    def test_get_by_id(self, test_app, test_leave):
        assert LeaveRepository.get_by_id(test_leave.id) is not None
        assert LeaveRepository.get_by_id(999999) is None

    def test_list_for_user(self, test_app, test_user, test_leave):
        leaves = LeaveRepository.list_for_user(test_user.id)
        assert len(leaves) == 1
        assert leaves[0].id == test_leave.id

    def test_find_conflict_overlapping(self, test_app, test_user, test_leave):
        conflict = LeaveRepository.find_conflict(
            test_user.id, test_leave.start_date, test_leave.end_date
        )
        assert conflict is not None

    def test_find_conflict_excludes_own_id(self, test_app, test_user, test_leave):
        conflict = LeaveRepository.find_conflict(
            test_user.id,
            test_leave.start_date,
            test_leave.end_date,
            exclude_id=test_leave.id,
        )
        assert conflict is None

    def test_find_conflict_none_outside_range(self, test_app, test_user, test_leave):
        far_future = test_leave.end_date + timedelta(days=30)
        conflict = LeaveRepository.find_conflict(test_user.id, far_future, far_future)
        assert conflict is None

    def test_count_and_exists_for_user(
        self, test_app, test_user, second_user, test_leave
    ):
        assert LeaveRepository.count_for_user(test_user.id) == 1
        assert LeaveRepository.exists_for_user(test_user.id) is True
        assert LeaveRepository.exists_for_user(second_user.id) is False

    def test_create_and_delete(self, test_app, test_user):
        leave = LeaveRepository.create(
            test_user.id, date.today(), date.today() + timedelta(days=2)
        )
        db.session.commit()
        assert LeaveRepository.get_by_id(leave.id) is not None

        LeaveRepository.delete(leave)
        db.session.commit()
        assert LeaveRepository.get_by_id(leave.id) is None


class TestOnCallRepository:
    def test_get_by_id(self, test_app, test_oncall):
        assert OnCallRepository.get_by_id(test_oncall.id) is not None
        assert OnCallRepository.get_by_id(999999) is None

    def test_list_for_user(self, test_app, test_user, test_oncall):
        oncalls = OnCallRepository.list_for_user(test_user.id)
        assert len(oncalls) == 1
        assert oncalls[0].id == test_oncall.id

    def test_find_conflict_overlapping(self, test_app, test_user, test_oncall):
        conflict = OnCallRepository.find_conflict(
            test_user.id, test_oncall.start_time, test_oncall.end_time
        )
        assert conflict is not None

    def test_find_conflict_excludes_own_id(self, test_app, test_user, test_oncall):
        conflict = OnCallRepository.find_conflict(
            test_user.id,
            test_oncall.start_time,
            test_oncall.end_time,
            exclude_id=test_oncall.id,
        )
        assert conflict is None

    def test_count_and_exists_for_user(
        self, test_app, test_user, second_user, test_oncall
    ):
        assert OnCallRepository.count_all() == 1
        assert OnCallRepository.count_for_user(test_user.id) == 1
        assert OnCallRepository.exists_for_user(test_user.id) is True
        assert OnCallRepository.exists_for_user(second_user.id) is False

    def test_list_overlapping_range(self, test_app, test_oncall):
        oncalls = OnCallRepository.list_overlapping_range(
            test_oncall.start_time.date(), test_oncall.end_time.date()
        )
        assert len(oncalls) == 1

    def test_delete_overlapping_range(self, test_app, test_oncall):
        deleted = OnCallRepository.delete_overlapping_range(
            test_oncall.start_time.date(), test_oncall.end_time.date()
        )
        db.session.commit()
        assert deleted == 1
        assert OnCallRepository.get_by_id(test_oncall.id) is None

    def test_delete_all(self, test_app, test_oncall):
        OnCallRepository.delete_all()
        db.session.commit()
        assert OnCallRepository.count_all() == 0

    def test_delete_for_user(self, test_app, test_user, test_oncall):
        OnCallRepository.delete_for_user(test_user.id)
        db.session.commit()
        assert OnCallRepository.count_for_user(test_user.id) == 0

    def test_create_and_delete(self, test_app, test_user):
        start = datetime.now()
        end = start + timedelta(days=7)
        oncall = OnCallRepository.create(test_user.id, start, end)
        db.session.commit()
        assert OnCallRepository.get_by_id(oncall.id) is not None

        OnCallRepository.delete(oncall)
        db.session.commit()
        assert OnCallRepository.get_by_id(oncall.id) is None
