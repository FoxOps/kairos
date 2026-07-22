"""
Tests for main.py's API endpoints.
Covers API routes not previously tested.
"""

import json


class TestAPIGetShifts:
    """Tests for GET /api/shifts."""

    def test_returns_json(self, logged_in_client):
        """Test that /api/shifts returns JSON."""
        response = logged_in_client.get("/api/shifts")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_returns_list(self, logged_in_client):
        """Test that /api/shifts returns a list."""
        response = logged_in_client.get("/api/shifts")
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_start_end_range_beyond_default_window_returns_shift(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Regression test: the calendar used to be capped to a fixed
        ±180-day window embedded once at page load - a shift generated
        further out than that would silently never appear, with no way
        for the admin to tell why. FullCalendar now fetches this
        endpoint with start/end for whatever range it's actually
        viewing, so a shift a year out must be reachable via those
        params even though it falls outside the fallback default
        window."""
        from datetime import date, datetime, timedelta

        from app import db
        from app.models import Shift

        far_future = date.today() + timedelta(days=400)
        shift = Shift(
            user_id=test_user.id,
            shift_type_id=test_shift_type.id,
            date=far_future,
            start_time=datetime.combine(far_future, datetime.min.time()).replace(
                hour=9
            ),
            end_time=datetime.combine(far_future, datetime.min.time()).replace(hour=17),
        )
        db.session.add(shift)
        db.session.commit()

        # Falls outside the default ±180-day window with no params.
        default_response = logged_in_client.get("/api/shifts")
        default_ids = {e["extendedProps"]["resourceId"] for e in default_response.json}
        assert shift.id not in default_ids

        range_start = (far_future - timedelta(days=3)).isoformat()
        range_end = (far_future + timedelta(days=3)).isoformat()
        ranged_response = logged_in_client.get(
            f"/api/shifts?start={range_start}&end={range_end}"
        )
        assert ranged_response.status_code == 200
        ranged_ids = {e["extendedProps"]["resourceId"] for e in ranged_response.json}
        assert shift.id in ranged_ids

    def test_malformed_start_end_falls_back_to_default_window(self, logged_in_client):
        """An unparseable start/end must not error the whole request -
        falls back to the same default window as when they're omitted."""
        response = logged_in_client.get("/api/shifts?start=not-a-date&end=also-not")
        assert response.status_code == 200
        assert isinstance(response.json, list)


class TestAPIGetUsers:
    """Tests for GET /api/users."""

    def test_returns_json(self, logged_in_client):
        """Test that /api/users returns JSON."""
        response = logged_in_client.get("/api/users")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_returns_list(self, logged_in_client):
        """Test that /api/users returns a list."""
        response = logged_in_client.get("/api/users")
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_returns_user_data(self, logged_in_client):
        """Test that /api/users returns user data."""
        response = logged_in_client.get("/api/users")
        data = json.loads(response.data)
        if data:
            user = data[0]
            assert "id" in user
            assert "name" in user
            assert "email" in user


class TestAPIGetShiftTypes:
    """Tests for GET /api/shift-types."""

    def test_returns_json(self, logged_in_client):
        """Test that /api/shift-types returns JSON."""
        response = logged_in_client.get("/api/shift-types")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_returns_list(self, logged_in_client):
        """Test that /api/shift-types returns a list."""
        response = logged_in_client.get("/api/shift-types")
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestAPICreateShift:
    """Tests for POST /api/shifts."""

    def test_requires_admin(self, non_admin_client):
        """Test that POST /api/shifts requires admin."""
        response = non_admin_client.post("/api/shifts", json={})
        assert response.status_code in [302, 403]

    def test_requires_data(self, logged_in_client):
        """Test that POST /api/shifts requires data."""
        response = logged_in_client.post("/api/shifts", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    def test_missing_fields(self, logged_in_client):
        """Test that POST /api/shifts fails with missing fields."""
        response = logged_in_client.post("/api/shifts", json={"userId": 1})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False


class TestAPIUpdateShift:
    """Tests for PATCH /api/shifts/<id>."""

    def test_requires_admin(self, non_admin_client):
        """Test that PATCH /api/shifts/<id> requires admin."""
        response = non_admin_client.patch("/api/shifts/1", json={})
        assert response.status_code in [302, 403]

    def test_nonexistent_shift(self, logged_in_client):
        """Test that PATCH /api/shifts/<id> returns 404 for a nonexistent shift."""
        response = logged_in_client.patch("/api/shifts/99999", json={})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False


class TestAPIDeleteShift:
    """Tests for DELETE /api/shifts/<id>."""

    def test_requires_admin(self, non_admin_client):
        """Test that DELETE /api/shifts/<id> requires admin."""
        response = non_admin_client.delete("/api/shifts/1")
        assert response.status_code in [302, 403]

    def test_nonexistent_shift(self, logged_in_client):
        """Test that DELETE /api/shifts/<id> returns 404 for a nonexistent shift."""
        response = logged_in_client.delete("/api/shifts/99999")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
