"""
Integration tests for the public API v1 endpoints (app/api/resources) -
real HTTP requests through service_account_client (Authorization:
Bearer header), exercising auth + serialization + pagination together.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, OnCall


class TestShiftsEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/shifts/")
        assert response.status_code == 401

    def test_list_returns_shift(self, service_account_client, test_shift):
        response = service_account_client.get("/api/v1/shifts/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == test_shift.id
        assert data["items"][0]["user_id"] == test_shift.user_id

    def test_detail_returns_shift(self, service_account_client, test_shift):
        response = service_account_client.get(f"/api/v1/shifts/{test_shift.id}")
        assert response.status_code == 200
        assert response.get_json()["id"] == test_shift.id

    def test_detail_404_for_unknown_id(self, service_account_client, test_shift):
        response = service_account_client.get("/api/v1/shifts/999999")
        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "not_found"
        assert "message" in response.get_json()["error"]

    def test_list_filters_by_user_id(self, service_account_client, test_shift):
        response = service_account_client.get(
            f"/api/v1/shifts/?user_id={test_shift.user_id}"
        )
        assert response.status_code == 200
        assert response.get_json()["total"] == 1
        response = service_account_client.get("/api/v1/shifts/?user_id=999999")
        assert response.get_json()["total"] == 0

    def test_list_filters_by_group_id(
        self, service_account_client, test_shift, test_group
    ):
        response = service_account_client.get(
            f"/api/v1/shifts/?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert response.get_json()["total"] == 1

    def test_list_filters_by_shift_type_id(
        self, service_account_client, test_shift, test_shift_type
    ):
        response = service_account_client.get(
            f"/api/v1/shifts/?shift_type_id={test_shift_type.id}"
        )
        assert response.status_code == 200
        assert response.get_json()["total"] == 1

    def test_date_range_overlap_includes_shift(
        self, service_account_client, test_shift
    ):
        response = service_account_client.get(
            f"/api/v1/shifts/?start={test_shift.date.isoformat()}"
            f"&end={test_shift.date.isoformat()}"
        )
        assert response.get_json()["total"] == 1

    def test_date_range_excludes_shift_outside_window(
        self, service_account_client, test_shift
    ):
        future = (test_shift.date + timedelta(days=10)).isoformat()
        response = service_account_client.get(
            f"/api/v1/shifts/?start={future}&end={future}"
        )
        assert response.get_json()["total"] == 0

    def test_invalid_range_returns_422(self, service_account_client, test_shift):
        response = service_account_client.get(
            "/api/v1/shifts/?start=2026-09-10&end=2026-09-01"
        )
        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "validation_error"

    def test_invalid_date_returns_422(self, service_account_client):
        response = service_account_client.get("/api/v1/shifts/?start=not-a-date")
        assert response.status_code == 422


class TestOnCallEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/oncall/")
        assert response.status_code == 401

    def test_list_returns_oncall(self, service_account_client, test_oncall):
        response = service_account_client.get("/api/v1/oncall/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == test_oncall.id

    def test_list_tz_aware_datetimes(self, service_account_client, test_oncall):
        response = service_account_client.get("/api/v1/oncall/")
        assert response.status_code == 200
        start_time = response.get_json()["items"][0]["start_time"]
        assert datetime.fromisoformat(start_time).tzinfo is not None

    def test_detail_returns_oncall(self, service_account_client, test_oncall):
        response = service_account_client.get(f"/api/v1/oncall/{test_oncall.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == test_oncall.id
        assert datetime.fromisoformat(data["start_time"]).tzinfo is not None

    def test_detail_404_for_unknown_id(self, service_account_client, test_oncall):
        response = service_account_client.get("/api/v1/oncall/999999")
        assert response.status_code == 404

    def test_list_filters_by_group_id(
        self, service_account_client, test_oncall, test_group
    ):
        response = service_account_client.get(
            f"/api/v1/oncall/?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert response.get_json()["total"] == 1

    def test_date_range_overlap_includes_oncall_starting_before_range(
        self, service_account_client, test_oncall
    ):
        """test_oncall spans today..today+7 - a range starting today
        (before the on-call ends) must still return it (overlap
        semantics, not strict containment)."""
        today = date.today().isoformat()
        response = service_account_client.get(
            f"/api/v1/oncall/?start={today}&end={today}"
        )
        assert response.get_json()["total"] == 1

    def test_date_range_excludes_oncall_outside_window(
        self, service_account_client, test_oncall
    ):
        future = (date.today() + timedelta(days=30)).isoformat()
        response = service_account_client.get(
            f"/api/v1/oncall/?start={future}&end={future}"
        )
        assert response.get_json()["total"] == 0

    def test_invalid_range_returns_422(self, service_account_client, test_oncall):
        response = service_account_client.get(
            "/api/v1/oncall/?start=2026-09-10&end=2026-09-01"
        )
        assert response.status_code == 422


class TestOnCallCurrentEndpoint:
    def test_requires_auth(self, client):
        response = client.get("/api/v1/oncall/current")
        assert response.status_code == 401

    def test_no_active_no_group_returns_empty_items(self, service_account_client):
        response = service_account_client.get("/api/v1/oncall/current")
        assert response.status_code == 200
        assert response.get_json() == {"items": [], "count": 0}

    def test_no_active_with_group_returns_empty_items(
        self, service_account_client, test_group
    ):
        response = service_account_client.get(
            f"/api/v1/oncall/current?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert response.get_json() == {"items": [], "count": 0}

    def test_active_no_group_returns_items(
        self, service_account_client, test_oncall, test_user
    ):
        response = service_account_client.get("/api/v1/oncall/current")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        item = data["items"][0]
        assert item["id"] == test_oncall.id
        assert item["user_id"] == test_user.id
        assert item["name"] == test_user.name
        assert item["email"] == test_user.email
        assert item["group_id"] == test_user.group_id
        assert item["timezone"]
        assert datetime.fromisoformat(item["start_time"]).tzinfo is not None
        assert datetime.fromisoformat(item["end_time"]).tzinfo is not None

    def test_active_matching_group_returns_items(
        self, service_account_client, test_oncall, test_user
    ):
        response = service_account_client.get(
            f"/api/v1/oncall/current?group_id={test_user.group_id}"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["items"][0]["id"] == test_oncall.id
        assert data["items"][0]["user_id"] == test_user.id

    def test_two_concurrent_actives_same_group_returns_array(
        self, service_account_client, test_app, test_oncall, test_user
    ):
        """Found during 1.1.1 release QA: with group_id given, only
        oncalls[0] was ever returned - a second genuinely-concurrent
        on-call in the same group (e.g. an admin-created overlap) was
        silently dropped from the response, exactly the kind of data
        loss this monitoring-facing endpoint exists to avoid."""
        from werkzeug.security import generate_password_hash

        from app.models import User

        other_user = User(
            name="Other User",
            email="other-oncall@test.com",
            password_hash=generate_password_hash("test123"),
            is_admin=False,
            group_id=test_user.group_id,
        )
        db.session.add(other_user)
        db.session.commit()

        overlapping = OnCall(
            user_id=other_user.id,
            start_time=test_oncall.start_time,
            end_time=test_oncall.end_time,
        )
        db.session.add(overlapping)
        db.session.commit()

        response = service_account_client.get(
            f"/api/v1/oncall/current?group_id={test_user.group_id}"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2
        assert {item["user_id"] for item in data["items"]} == {
            test_user.id,
            other_user.id,
        }

    def test_active_other_group_returns_inactive(
        self, service_account_client, test_app, test_oncall
    ):
        other_group = Group(
            name="Other Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(other_group)
        db.session.commit()

        response = service_account_client.get(
            f"/api/v1/oncall/current?group_id={other_group.id}"
        )
        assert response.status_code == 200
        assert response.get_json() == {"items": [], "count": 0}


class TestLeaveEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/leave/")
        assert response.status_code == 401

    def test_list_returns_leave(self, service_account_client, test_leave):
        response = service_account_client.get("/api/v1/leave/")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == test_leave.id

    def test_detail_returns_leave(self, service_account_client, test_leave):
        response = service_account_client.get(f"/api/v1/leave/{test_leave.id}")
        assert response.status_code == 200
        assert response.get_json()["id"] == test_leave.id

    def test_detail_404_for_unknown_id(self, service_account_client, test_leave):
        response = service_account_client.get("/api/v1/leave/999999")
        assert response.status_code == 404

    def test_list_filters_by_group_id(
        self, service_account_client, test_leave, test_group
    ):
        response = service_account_client.get(
            f"/api/v1/leave/?group_id={test_group.id}"
        )
        assert response.status_code == 200
        assert response.get_json()["total"] == 1

    def test_date_range_overlap_includes_leave_starting_before_range(
        self, service_account_client, test_leave
    ):
        """test_leave spans today..today+5 - a range starting today must
        still return it (overlap semantics, not strict containment)."""
        today = date.today().isoformat()
        response = service_account_client.get(
            f"/api/v1/leave/?start={today}&end={today}"
        )
        assert response.get_json()["total"] == 1

    def test_date_range_excludes_leave_outside_window(
        self, service_account_client, test_leave
    ):
        future = (date.today() + timedelta(days=30)).isoformat()
        response = service_account_client.get(
            f"/api/v1/leave/?start={future}&end={future}"
        )
        assert response.get_json()["total"] == 0


class TestUsersEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/users/")
        assert response.status_code == 401

    def test_list_returns_user_without_sensitive_fields(
        self, service_account_client, test_user
    ):
        response = service_account_client.get("/api/v1/users/")
        assert response.status_code == 200
        data = response.get_json()
        assert "total" in data
        users = data["items"]
        assert any(u["id"] == test_user.id for u in users)
        for u in users:
            assert "password_hash" not in u
            assert "ics_token" not in u

    def test_list_filters_by_group_id(
        self, service_account_client, test_user, test_group
    ):
        response = service_account_client.get(
            f"/api/v1/users/?group_id={test_group.id}"
        )
        assert response.status_code == 200
        users = response.get_json()["items"]
        assert all(u["group_id"] == test_group.id for u in users)

    def test_detail_returns_user(self, service_account_client, test_user):
        response = service_account_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        assert response.get_json()["id"] == test_user.id

    def test_detail_404_for_unknown_id(self, service_account_client, test_user):
        response = service_account_client.get("/api/v1/users/999999")
        assert response.status_code == 404


class TestShiftTypesEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/shift-types/")
        assert response.status_code == 401

    def test_list_returns_shift_type(self, service_account_client, test_shift_type):
        response = service_account_client.get("/api/v1/shift-types/")
        assert response.status_code == 200
        types = response.get_json()
        assert any(st["id"] == test_shift_type.id for st in types)
