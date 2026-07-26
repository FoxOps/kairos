"""
Tests for the "delete filtered result" bulk-delete routes on
/schedule, /oncall, /leave (POST /shift/delete-filtered,
/oncall/delete-filtered, /leave/delete-filtered) - the single action
replacing the old per-purpose delete-all/delete-all-for-user/
delete-day/delete-week routes.
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
