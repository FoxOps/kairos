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
