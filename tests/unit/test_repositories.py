"""
Unit tests for app/repositories/.

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

    def test_get_rotation_eligible_excludes_group_in_neither(self, test_app):
        """Only groups flagged for shift scheduling and/or on-call
        rotation - a group in neither (e.g. a leftover seed group no
        one assigns shifts to) is excluded, unlike get_all()."""
        schedule_only = GroupRepository.create("Schedule Only", True, False)
        oncall_only = GroupRepository.create("Oncall Only", False, True)
        both = GroupRepository.create("Both", True, True)
        neither = GroupRepository.create("Neither", False, False)
        db.session.commit()

        eligible_ids = {g.id for g in GroupRepository.get_rotation_eligible()}
        assert schedule_only.id in eligible_ids
        assert oncall_only.id in eligible_ids
        assert both.id in eligible_ids
        assert neither.id not in eligible_ids

    def test_get_rotation_eligible_ordered_by_name(self, test_app):
        GroupRepository.create("Zeta", True, False)
        GroupRepository.create("Alpha", False, True)
        db.session.commit()
        names = [g.name for g in GroupRepository.get_rotation_eligible()]
        assert names == sorted(names)


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

    def test_list_all_with_user_no_group_filter(self, test_app, test_shift):
        assert [s.id for s in ShiftRepository.list_all_with_user()] == [test_shift.id]

    def test_list_all_with_user_filters_by_group_ids(
        self, test_app, test_group, test_shift
    ):
        """group_ids=None (the ICS export URL's existing shape, no param)
        stays fully unfiltered - the backward-compat guarantee for every
        already-copied/subscribed export URL."""
        from app.models import Group

        other_group = Group(name="Other Group AllWithUser")
        db.session.add(other_group)
        db.session.commit()

        assert [
            s.id for s in ShiftRepository.list_all_with_user(group_ids=[test_group.id])
        ] == [test_shift.id]
        assert ShiftRepository.list_all_with_user(group_ids=[other_group.id]) == []

    def test_list_in_window_no_group_filter(self, test_app, test_shift):
        window_start = datetime.combine(test_shift.date, datetime.min.time())
        window_end = datetime.combine(test_shift.date, datetime.max.time())
        shifts = ShiftRepository.list_in_window(window_start, window_end)
        assert [s.id for s in shifts] == [test_shift.id]

    def test_list_in_window_filters_by_group_ids(
        self, test_app, test_group, test_shift
    ):
        from app.models import Group

        other_group = Group(name="Other Group Window")
        db.session.add(other_group)
        db.session.commit()

        window_start = datetime.combine(test_shift.date, datetime.min.time())
        window_end = datetime.combine(test_shift.date, datetime.max.time())

        assert (
            len(
                ShiftRepository.list_in_window(
                    window_start, window_end, group_ids=[test_group.id]
                )
            )
            == 1
        )
        assert (
            ShiftRepository.list_in_window(
                window_start, window_end, group_ids=[other_group.id]
            )
            == []
        )

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

    def test_count_all(self, test_app, test_shift):
        assert ShiftRepository.count_all() == 1

    def test_count_for_group(self, test_app, test_group, test_shift):
        from werkzeug.security import generate_password_hash

        from app.models import Group, User

        other_group = Group(name="Other")
        db.session.add(other_group)
        db.session.commit()
        other_user = User(
            name="Other",
            email="other-shift-group@test.com",
            password_hash=generate_password_hash("x"),
            is_admin=False,
            group_id=other_group.id,
        )
        db.session.add(other_user)
        db.session.commit()

        assert ShiftRepository.count_for_group(test_group.id) == 1
        assert ShiftRepository.count_for_group(other_group.id) == 0

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

    def test_delete_in_date_range_uses_a_single_bulk_delete(
        self, test_app, test_user, test_shift_type, test_shift, monkeypatch
    ):
        """Regression guard: this used to fetch every matching row into
        Python objects and call db.session.delete() once per row - now a
        single bulk DELETE ... WHERE (see ShiftRepository.delete_in_date_range())."""
        calls = []
        monkeypatch.setattr(db.session, "delete", lambda obj: calls.append(obj))

        deleted = ShiftRepository.delete_in_date_range(test_shift.date, test_shift.date)

        assert deleted == 1
        assert calls == []

    def test_create(self, test_app, test_user, test_shift_type):
        start = datetime.combine(date.today(), datetime.min.time())
        end = start + timedelta(hours=8)
        shift = ShiftRepository.create(
            test_user.id, test_shift_type.id, start, end, date.today()
        )
        db.session.commit()
        assert ShiftRepository.get_by_id(shift.id) is not None

    def test_list_dates_for_user(self, test_app, test_user, test_shift):
        dates = ShiftRepository.list_dates_for_user(test_user.id)
        assert dates == [test_shift.date]

    def test_list_dates_for_user_empty(self, test_app, test_user):
        assert ShiftRepository.list_dates_for_user(test_user.id) == []

    def test_list_paginated_no_filters_returns_everything(
        self, test_app, test_user, test_shift
    ):
        page = ShiftRepository.list_paginated(1, 10)
        assert page.total == 1

    def test_list_paginated_filters_by_user_id(
        self, test_app, test_user, second_user, test_shift
    ):
        assert ShiftRepository.list_paginated(1, 10, user_id=test_user.id).total == 1
        assert ShiftRepository.list_paginated(1, 10, user_id=second_user.id).total == 0

    def test_list_paginated_filters_by_group_id(self, test_app, test_group, test_shift):

        from app.models import Group

        other_group = Group(name="Other Group Paginated")
        db.session.add(other_group)
        db.session.commit()

        assert ShiftRepository.list_paginated(1, 10, group_id=test_group.id).total == 1
        assert ShiftRepository.list_paginated(1, 10, group_id=other_group.id).total == 0

    def test_list_paginated_filters_by_date_range(self, test_app, test_shift):
        today = test_shift.date
        assert (
            ShiftRepository.list_paginated(1, 10, date_from=today, date_to=today).total
            == 1
        )
        assert (
            ShiftRepository.list_paginated(
                1, 10, date_from=today + timedelta(days=1)
            ).total
            == 0
        )
        assert (
            ShiftRepository.list_paginated(
                1, 10, date_to=today - timedelta(days=1)
            ).total
            == 0
        )

    def test_list_paginated_filters_by_shift_type_id(
        self, test_app, test_shift_type, afternoon_shift_type, test_shift
    ):
        assert (
            ShiftRepository.list_paginated(
                1, 10, shift_type_id=test_shift_type.id
            ).total
            == 1
        )
        assert (
            ShiftRepository.list_paginated(
                1, 10, shift_type_id=afternoon_shift_type.id
            ).total
            == 0
        )

    def test_delete_filtered_no_filters_deletes_everything(self, test_app, test_shift):
        deleted = ShiftRepository.delete_filtered()
        db.session.commit()
        assert deleted == 1
        assert ShiftRepository.count_all() == 0

    def test_delete_filtered_by_user_id_only_deletes_matching(
        self, test_app, test_user, second_user, test_shift_type, test_shift
    ):
        test_shift_id = test_shift.id
        other_shift = ShiftRepository.create(
            second_user.id,
            test_shift_type.id,
            datetime.combine(date.today(), datetime.min.time()),
            datetime.combine(date.today(), datetime.max.time()),
            date.today(),
        )
        db.session.commit()
        other_shift_id = other_shift.id

        deleted = ShiftRepository.delete_filtered(user_id=test_user.id)
        db.session.commit()

        assert deleted == 1
        assert ShiftRepository.get_by_id(test_shift_id) is None
        assert ShiftRepository.get_by_id(other_shift_id) is not None

    def test_delete_filtered_by_date_range(self, test_app, test_shift):
        deleted = ShiftRepository.delete_filtered(
            date_from=test_shift.date + timedelta(days=1)
        )
        db.session.commit()
        assert deleted == 0
        assert ShiftRepository.get_by_id(test_shift.id) is not None

    def test_delete_filtered_by_ids_only_deletes_selected(
        self, test_app, test_user, second_user, test_shift_type, test_shift
    ):
        test_shift_id = test_shift.id
        other_shift = ShiftRepository.create(
            second_user.id,
            test_shift_type.id,
            datetime.combine(date.today(), datetime.min.time()),
            datetime.combine(date.today(), datetime.max.time()),
            date.today(),
        )
        db.session.commit()
        other_shift_id = other_shift.id

        deleted = ShiftRepository.delete_filtered(ids=[test_shift_id])
        db.session.commit()

        assert deleted == 1
        assert ShiftRepository.get_by_id(test_shift_id) is None
        assert ShiftRepository.get_by_id(other_shift_id) is not None

    def test_list_paginated_filters_by_ids(
        self, test_app, test_user, second_user, test_shift_type, test_shift
    ):
        other_shift = ShiftRepository.create(
            second_user.id,
            test_shift_type.id,
            datetime.combine(date.today(), datetime.min.time()),
            datetime.combine(date.today(), datetime.max.time()),
            date.today(),
        )
        db.session.commit()

        assert ShiftRepository.list_paginated(1, 10, ids=[test_shift.id]).total == 1
        assert (
            ShiftRepository.list_paginated(
                1, 10, ids=[test_shift.id, other_shift.id]
            ).total
            == 2
        )


class TestLeaveRepository:
    def test_get_by_id(self, test_app, test_leave):
        assert LeaveRepository.get_by_id(test_leave.id) is not None
        assert LeaveRepository.get_by_id(999999) is None

    def test_list_for_user(self, test_app, test_user, test_leave):
        leaves = LeaveRepository.list_for_user(test_user.id)
        assert len(leaves) == 1
        assert leaves[0].id == test_leave.id

    def test_list_all_with_user_filters_by_group_ids(
        self, test_app, test_group, test_leave
    ):
        from app.models import Group

        other_group = Group(name="Other Group Leave AllWithUser")
        db.session.add(other_group)
        db.session.commit()

        assert [
            leave.id
            for leave in LeaveRepository.list_all_with_user(group_ids=[test_group.id])
        ] == [test_leave.id]
        assert LeaveRepository.list_all_with_user(group_ids=[other_group.id]) == []
        assert [leave.id for leave in LeaveRepository.list_all_with_user()] == [
            test_leave.id
        ]

    def test_list_in_window_filters_by_group_ids(
        self, test_app, test_group, test_leave
    ):
        from app.models import Group

        other_group = Group(name="Other Group Leave Window")
        db.session.add(other_group)
        db.session.commit()

        assert (
            len(
                LeaveRepository.list_in_window(
                    test_leave.start_date,
                    test_leave.end_date,
                    group_ids=[test_group.id],
                )
            )
            == 1
        )
        assert (
            LeaveRepository.list_in_window(
                test_leave.start_date,
                test_leave.end_date,
                group_ids=[other_group.id],
            )
            == []
        )

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

    def test_list_spans_for_user(self, test_app, test_user, test_leave):
        spans = LeaveRepository.list_spans_for_user(test_user.id)
        assert spans == [(test_leave.start_date, test_leave.end_date)]

    def test_list_spans_for_user_empty(self, test_app, test_user):
        assert LeaveRepository.list_spans_for_user(test_user.id) == []

    def test_list_paginated_filters_by_user_id(
        self, test_app, test_user, second_user, test_leave
    ):
        assert LeaveRepository.list_paginated(1, 10, user_id=test_user.id).total == 1
        assert LeaveRepository.list_paginated(1, 10, user_id=second_user.id).total == 0

    def test_list_paginated_filters_by_group_id(self, test_app, test_group, test_leave):
        from app.models import Group

        other_group = Group(name="Other Group Leave Paginated")
        db.session.add(other_group)
        db.session.commit()

        assert LeaveRepository.list_paginated(1, 10, group_id=test_group.id).total == 1
        assert LeaveRepository.list_paginated(1, 10, group_id=other_group.id).total == 0

    def test_list_paginated_filters_by_date_range_overlap(self, test_app, test_leave):
        assert (
            LeaveRepository.list_paginated(
                1, 10, date_from=test_leave.start_date, date_to=test_leave.start_date
            ).total
            == 1
        )
        assert (
            LeaveRepository.list_paginated(
                1, 10, date_from=test_leave.end_date + timedelta(days=1)
            ).total
            == 0
        )
        assert (
            LeaveRepository.list_paginated(
                1, 10, date_to=test_leave.start_date - timedelta(days=1)
            ).total
            == 0
        )

    def test_list_filtered_no_filters_returns_everything(self, test_app, test_leave):
        leaves = LeaveRepository.list_filtered()
        assert [leave.id for leave in leaves] == [test_leave.id]

    def test_list_filtered_by_user_id(
        self, test_app, test_user, second_user, test_leave
    ):
        assert len(LeaveRepository.list_filtered(user_id=test_user.id)) == 1
        assert LeaveRepository.list_filtered(user_id=second_user.id) == []

    def test_list_filtered_by_ids(self, test_app, test_user, test_leave):
        other = LeaveRepository.create(
            test_user.id,
            test_leave.end_date + timedelta(days=10),
            test_leave.end_date + timedelta(days=12),
        )
        db.session.commit()

        assert [
            leave.id for leave in LeaveRepository.list_filtered(ids=[test_leave.id])
        ] == [test_leave.id]
        assert len(LeaveRepository.list_filtered(ids=[test_leave.id, other.id])) == 2

    def test_list_paginated_filters_by_ids(self, test_app, test_user, test_leave):
        other = LeaveRepository.create(
            test_user.id,
            test_leave.end_date + timedelta(days=10),
            test_leave.end_date + timedelta(days=12),
        )
        db.session.commit()

        assert LeaveRepository.list_paginated(1, 10, ids=[test_leave.id]).total == 1
        assert (
            LeaveRepository.list_paginated(1, 10, ids=[test_leave.id, other.id]).total
            == 2
        )


class TestOnCallRepository:
    def test_get_by_id(self, test_app, test_oncall):
        assert OnCallRepository.get_by_id(test_oncall.id) is not None
        assert OnCallRepository.get_by_id(999999) is None

    def test_list_for_user(self, test_app, test_user, test_oncall):
        oncalls = OnCallRepository.list_for_user(test_user.id)
        assert len(oncalls) == 1
        assert oncalls[0].id == test_oncall.id

    def test_list_all_with_user_filters_by_group_ids(
        self, test_app, test_group, test_oncall
    ):
        from app.models import Group

        other_group = Group(name="Other Group OnCall AllWithUser")
        db.session.add(other_group)
        db.session.commit()

        assert [
            oc.id
            for oc in OnCallRepository.list_all_with_user(group_ids=[test_group.id])
        ] == [test_oncall.id]
        assert OnCallRepository.list_all_with_user(group_ids=[other_group.id]) == []
        assert [oc.id for oc in OnCallRepository.list_all_with_user()] == [
            test_oncall.id
        ]

    def test_list_in_window_filters_by_group_ids(
        self, test_app, test_group, test_oncall
    ):
        from app.models import Group

        other_group = Group(name="Other Group OnCall Window")
        db.session.add(other_group)
        db.session.commit()

        assert (
            len(
                OnCallRepository.list_in_window(
                    test_oncall.start_time,
                    test_oncall.end_time,
                    group_ids=[test_group.id],
                )
            )
            == 1
        )
        assert (
            OnCallRepository.list_in_window(
                test_oncall.start_time,
                test_oncall.end_time,
                group_ids=[other_group.id],
            )
            == []
        )

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

    def test_count_all_and_exists_for_user(
        self, test_app, test_user, second_user, test_oncall
    ):
        assert OnCallRepository.count_all() == 1
        assert OnCallRepository.exists_for_user(test_user.id) is True
        assert OnCallRepository.exists_for_user(second_user.id) is False

    def test_count_for_group(self, test_app, test_group, test_oncall):
        from werkzeug.security import generate_password_hash

        from app.models import Group, User

        other_group = Group(name="Other")
        db.session.add(other_group)
        db.session.commit()
        other_user = User(
            name="Other",
            email="other-oncall-group@test.com",
            password_hash=generate_password_hash("x"),
            is_admin=False,
            group_id=other_group.id,
        )
        db.session.add(other_user)
        db.session.commit()

        assert OnCallRepository.count_for_group(test_group.id) == 1
        assert OnCallRepository.count_for_group(other_group.id) == 0

    def test_get_starting_at_scoped_to_group(self, test_app, test_group, test_oncall):
        from werkzeug.security import generate_password_hash

        from app.models import Group, User

        other_group = Group(name="Other")
        db.session.add(other_group)
        db.session.commit()
        other_user = User(
            name="Other",
            email="other-starting-at@test.com",
            password_hash=generate_password_hash("x"),
            is_admin=False,
            group_id=other_group.id,
        )
        db.session.add(other_user)
        db.session.commit()

        assert (
            OnCallRepository.get_starting_at(
                test_oncall.start_time, group_id=test_group.id
            )
            is not None
        )
        assert (
            OnCallRepository.get_starting_at(
                test_oncall.start_time, group_id=other_group.id
            )
            is None
        )
        # group_id=None (default) preserves today's ungrouped behavior
        assert OnCallRepository.get_starting_at(test_oncall.start_time) is not None

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

    def test_delete_overlapping_range_uses_a_single_bulk_delete(
        self, test_app, test_oncall, monkeypatch
    ):
        """Regression guard: this used to fetch every overlapping row into
        Python objects and call db.session.delete() once per row - now a
        single bulk DELETE ... WHERE (see OnCallRepository.delete_overlapping_range()).
        """
        calls = []
        monkeypatch.setattr(db.session, "delete", lambda obj: calls.append(obj))

        deleted = OnCallRepository.delete_overlapping_range(
            test_oncall.start_time.date(), test_oncall.end_time.date()
        )

        assert deleted == 1
        assert calls == []

    def test_create_and_delete(self, test_app, test_user):
        start = datetime.now()
        end = start + timedelta(days=7)
        oncall = OnCallRepository.create(test_user.id, start, end)
        db.session.commit()
        assert OnCallRepository.get_by_id(oncall.id) is not None

        OnCallRepository.delete(oncall)
        db.session.commit()
        assert OnCallRepository.get_by_id(oncall.id) is None

    def test_list_spans_for_user(self, test_app, test_user, test_oncall):
        spans = OnCallRepository.list_spans_for_user(test_user.id)
        assert spans == [(test_oncall.start_time, test_oncall.end_time)]

    def test_list_spans_for_user_empty(self, test_app, test_user):
        assert OnCallRepository.list_spans_for_user(test_user.id) == []

    def test_list_paginated_filters_by_user_id(
        self, test_app, test_user, second_user, test_oncall
    ):
        assert OnCallRepository.list_paginated(1, 10, user_id=test_user.id).total == 1
        assert OnCallRepository.list_paginated(1, 10, user_id=second_user.id).total == 0

    def test_list_paginated_filters_by_group_id(
        self, test_app, test_group, test_oncall
    ):
        from app.models import Group

        other_group = Group(name="Other Group OnCall Paginated")
        db.session.add(other_group)
        db.session.commit()

        assert OnCallRepository.list_paginated(1, 10, group_id=test_group.id).total == 1
        assert (
            OnCallRepository.list_paginated(1, 10, group_id=other_group.id).total == 0
        )

    def test_list_paginated_filters_by_date_range_overlap(self, test_app, test_oncall):
        start_date = test_oncall.start_time.date()
        end_date = test_oncall.end_time.date()
        assert (
            OnCallRepository.list_paginated(
                1, 10, date_from=start_date, date_to=start_date
            ).total
            == 1
        )
        assert (
            OnCallRepository.list_paginated(
                1, 10, date_from=end_date + timedelta(days=1)
            ).total
            == 0
        )
        assert (
            OnCallRepository.list_paginated(
                1, 10, date_to=start_date - timedelta(days=1)
            ).total
            == 0
        )

    def test_delete_filtered_no_filters_deletes_everything(self, test_app, test_oncall):
        deleted = OnCallRepository.delete_filtered()
        db.session.commit()
        assert deleted == 1
        assert OnCallRepository.count_all() == 0

    def test_delete_filtered_by_user_id_only_deletes_matching(
        self, test_app, test_user, second_user, test_oncall
    ):
        test_oncall_id = test_oncall.id
        other_oncall = OnCallRepository.create(
            second_user.id, datetime.now(), datetime.now() + timedelta(days=7)
        )
        db.session.commit()
        other_oncall_id = other_oncall.id

        deleted = OnCallRepository.delete_filtered(user_id=test_user.id)
        db.session.commit()

        assert deleted == 1
        assert OnCallRepository.get_by_id(test_oncall_id) is None
        assert OnCallRepository.get_by_id(other_oncall_id) is not None

    def test_delete_filtered_by_ids_only_deletes_selected(
        self, test_app, test_user, second_user, test_oncall
    ):
        test_oncall_id = test_oncall.id
        other_oncall = OnCallRepository.create(
            second_user.id, datetime.now(), datetime.now() + timedelta(days=7)
        )
        db.session.commit()
        other_oncall_id = other_oncall.id

        deleted = OnCallRepository.delete_filtered(ids=[test_oncall_id])
        db.session.commit()

        assert deleted == 1
        assert OnCallRepository.get_by_id(test_oncall_id) is None
        assert OnCallRepository.get_by_id(other_oncall_id) is not None

    def test_list_paginated_filters_by_ids(
        self, test_app, test_user, second_user, test_oncall
    ):
        other_oncall = OnCallRepository.create(
            second_user.id, datetime.now(), datetime.now() + timedelta(days=7)
        )
        db.session.commit()

        assert OnCallRepository.list_paginated(1, 10, ids=[test_oncall.id]).total == 1
        assert (
            OnCallRepository.list_paginated(
                1, 10, ids=[test_oncall.id, other_oncall.id]
            ).total
            == 2
        )
