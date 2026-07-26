"""
Tests for the "delete filtered result" bulk-delete routes on
/schedule, /oncall, /leave (POST /shift/delete-filtered,
/oncall/delete-filtered, /leave/delete-filtered) - the single action
replacing the old per-purpose delete-all/delete-all-for-user/
delete-day/delete-week routes - and the "delete selection" routes
(POST /shift/delete-selected, /oncall/delete-selected,
/leave/delete-selected) that act on a hand-picked subset (row
checkboxes) instead of everything the current filters match.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift


class TestDeleteFilteredShifts:
    """Tests for POST /shift/delete-filtered."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/shift/delete-filtered")
        assert response.status_code in [302, 403]

    def test_non_admin_forbidden(self, non_admin_client):
        response = non_admin_client.post("/shift/delete-filtered")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/shift/delete-filtered")
        assert response.status_code == 405

    def test_no_filters_deletes_everything(
        self, test_app, logged_in_client, test_shift
    ):
        response = logged_in_client.post(
            "/shift/delete-filtered", follow_redirects=True
        )
        assert response.status_code == 200
        assert Shift.query.count() == 0

    def test_filters_by_user_id_only_deletes_matching(
        self,
        test_app,
        logged_in_client,
        test_user,
        second_user,
        test_shift_type,
        test_shift,
    ):
        other = Shift(
            date=date.today(),
            start_time=datetime.combine(date.today(), datetime.min.time()),
            end_time=datetime.combine(date.today(), datetime.max.time()),
            user_id=second_user.id,
            shift_type_id=test_shift_type.id,
        )
        db.session.add(other)
        db.session.commit()
        other_id = other.id
        test_shift_id = test_shift.id

        response = logged_in_client.post(
            "/shift/delete-filtered",
            data={"user_id": str(test_user.id)},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(Shift, test_shift_id) is None
        assert db.session.get(Shift, other_id) is not None

    def test_invalid_date_still_redirects(self, logged_in_client):
        response = logged_in_client.post(
            "/shift/delete-filtered", data={"date_from": "not-a-date"}
        )
        assert response.status_code == 302

    def test_redirect_preserves_filters(self, logged_in_client, test_user):
        response = logged_in_client.post(
            "/shift/delete-filtered", data={"user_id": str(test_user.id)}
        )
        assert response.status_code == 302
        assert f"user_id={test_user.id}" in response.location


class TestDeleteFilteredOnCalls:
    """Tests for POST /oncall/delete-filtered."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/oncall/delete-filtered")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/oncall/delete-filtered")
        assert response.status_code == 405

    def test_no_filters_deletes_everything(
        self, test_app, logged_in_client, test_oncall
    ):
        response = logged_in_client.post(
            "/oncall/delete-filtered", follow_redirects=True
        )
        assert response.status_code == 200
        assert OnCall.query.count() == 0

    def test_filters_by_user_id_only_deletes_matching(
        self, test_app, logged_in_client, test_user, test_oncall
    ):
        response = logged_in_client.post(
            "/oncall/delete-filtered",
            data={"user_id": str(test_user.id)},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert OnCall.query.count() == 0

    def test_invalid_date_still_redirects(self, logged_in_client):
        response = logged_in_client.post(
            "/oncall/delete-filtered", data={"date_to": "not-a-date"}
        )
        assert response.status_code == 302


class TestDeleteFilteredLeaves:
    """Tests for POST /leave/delete-filtered - new, /leave had no
    bulk-delete before this feature."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/leave/delete-filtered")
        assert response.status_code in [302, 403]

    def test_non_admin_forbidden(self, non_admin_client):
        response = non_admin_client.post("/leave/delete-filtered")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/leave/delete-filtered")
        assert response.status_code == 405

    def test_no_filters_deletes_everything(
        self, test_app, logged_in_client, test_leave
    ):
        response = logged_in_client.post(
            "/leave/delete-filtered", follow_redirects=True
        )
        assert response.status_code == 200
        assert Leave.query.count() == 0

    def test_filters_by_date_range(self, test_app, logged_in_client, test_leave):
        far_future = test_leave.end_date + timedelta(days=365)
        response = logged_in_client.post(
            "/leave/delete-filtered",
            data={"date_from": far_future.strftime("%Y-%m-%d")},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Leave.query.count() == 1


class TestDeleteSelectedShifts:
    """Tests for POST /shift/delete-selected."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/shift/delete-selected")
        assert response.status_code in [302, 403]

    def test_non_admin_forbidden(self, non_admin_client):
        response = non_admin_client.post("/shift/delete-selected")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/shift/delete-selected")
        assert response.status_code == 405

    def test_empty_selection_is_a_noop(self, test_app, logged_in_client, test_shift):
        response = logged_in_client.post(
            "/shift/delete-selected", follow_redirects=True
        )
        assert response.status_code == 200
        assert Shift.query.count() == 1

    def test_deletes_only_selected_ids(
        self,
        test_app,
        logged_in_client,
        test_user,
        second_user,
        test_shift_type,
        test_shift,
    ):
        other = Shift(
            date=date.today(),
            start_time=datetime.combine(date.today(), datetime.min.time()),
            end_time=datetime.combine(date.today(), datetime.max.time()),
            user_id=second_user.id,
            shift_type_id=test_shift_type.id,
        )
        db.session.add(other)
        db.session.commit()
        other_id = other.id
        test_shift_id = test_shift.id

        response = logged_in_client.post(
            "/shift/delete-selected",
            data={"ids": [str(test_shift_id)]},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(Shift, test_shift_id) is None
        assert db.session.get(Shift, other_id) is not None

    def test_redirect_preserves_filters(self, logged_in_client, test_shift):
        response = logged_in_client.post(
            "/shift/delete-selected",
            data={"ids": [str(test_shift.id)], "date_from": "2026-01-01"},
        )
        assert response.status_code == 302
        assert "date_from=2026-01-01" in response.location


class TestDeleteSelectedOnCalls:
    """Tests for POST /oncall/delete-selected."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/oncall/delete-selected")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/oncall/delete-selected")
        assert response.status_code == 405

    def test_empty_selection_is_a_noop(self, test_app, logged_in_client, test_oncall):
        response = logged_in_client.post(
            "/oncall/delete-selected", follow_redirects=True
        )
        assert response.status_code == 200
        assert OnCall.query.count() == 1

    def test_deletes_only_selected_ids(
        self, test_app, logged_in_client, test_user, second_user, test_oncall
    ):
        from app.repositories.oncall_repository import OnCallRepository

        other = OnCallRepository.create(
            second_user.id, datetime.now(), datetime.now() + timedelta(days=7)
        )
        db.session.commit()
        other_id = other.id
        test_oncall_id = test_oncall.id

        response = logged_in_client.post(
            "/oncall/delete-selected",
            data={"ids": [str(test_oncall_id)]},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(OnCall, test_oncall_id) is None
        assert db.session.get(OnCall, other_id) is not None


class TestDeleteSelectedLeaves:
    """Tests for POST /leave/delete-selected."""

    def test_requires_admin(self, logged_in_client):
        response = logged_in_client.post("/leave/delete-selected")
        assert response.status_code in [302, 403]

    def test_non_admin_forbidden(self, non_admin_client):
        response = non_admin_client.post("/leave/delete-selected")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        response = logged_in_client.get("/leave/delete-selected")
        assert response.status_code == 405

    def test_empty_selection_is_a_noop(self, test_app, logged_in_client, test_leave):
        response = logged_in_client.post(
            "/leave/delete-selected", follow_redirects=True
        )
        assert response.status_code == 200
        assert Leave.query.count() == 1

    def test_deletes_only_selected_ids(
        self, test_app, logged_in_client, test_user, test_leave
    ):
        from app.repositories.leave_repository import LeaveRepository

        other = LeaveRepository.create(
            test_user.id,
            test_leave.end_date + timedelta(days=10),
            test_leave.end_date + timedelta(days=12),
        )
        db.session.commit()
        other_id = other.id
        test_leave_id = test_leave.id

        response = logged_in_client.post(
            "/leave/delete-selected",
            data={"ids": [str(test_leave_id)]},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(Leave, test_leave_id) is None
        assert db.session.get(Leave, other_id) is not None


class TestRowSelectCheckboxesAdminOnly:
    """The checkbox column (select-all + per-row) backing "delete
    selection" is admin-only, same visibility rule as the delete-filtered
    button - a regular user must not see it."""

    def test_schedule_hides_checkboxes_for_non_admin(
        self, test_app, non_admin_client, test_shift
    ):
        html = non_admin_client.get("/schedule").get_data(as_text=True)
        assert "js-select-all" not in html
        assert "js-row-select" not in html

    def test_oncall_hides_checkboxes_for_non_admin(
        self, test_app, non_admin_client, test_oncall
    ):
        html = non_admin_client.get("/oncall").get_data(as_text=True)
        assert "js-select-all" not in html
        assert "js-row-select" not in html

    def test_leave_hides_checkboxes_for_non_admin(
        self, test_app, non_admin_client, test_leave
    ):
        html = non_admin_client.get("/leave").get_data(as_text=True)
        assert "js-select-all" not in html
        assert "js-row-select" not in html

    def test_schedule_shows_checkboxes_for_admin(
        self, test_app, logged_in_client, test_shift
    ):
        html = logged_in_client.get("/schedule").get_data(as_text=True)
        assert "js-select-all" in html
        assert "js-row-select" in html
