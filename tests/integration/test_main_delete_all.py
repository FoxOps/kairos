"""
Tests for the bulk-delete routes in main.py
Covers the delete-all routes not previously tested.
"""


class TestDeleteAllShifts:
    """Tests for POST /shift/delete-all."""

    def test_requires_admin(self, logged_in_client):
        """Test that /shift/delete-all requires admin."""
        response = logged_in_client.post("/shift/delete-all")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /shift/delete-all requires a POST request."""
        response = logged_in_client.get("/shift/delete-all")
        assert response.status_code == 405  # Method Not Allowed


class TestDeleteAllShiftsForUser:
    """Tests for POST /shift/delete-all-for-user/<user_id>."""

    def test_requires_admin(self, logged_in_client):
        """Test that /shift/delete-all-for-user/<user_id> requires admin."""
        response = logged_in_client.post("/shift/delete-all-for-user/1")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /shift/delete-all-for-user/<user_id> requires a POST request."""
        response = logged_in_client.get("/shift/delete-all-for-user/1")
        assert response.status_code == 405


class TestDeleteAllShiftsForDay:
    """Tests for POST /shift/delete-day/<date_str>."""

    def test_requires_admin(self, logged_in_client):
        """Test that /shift/delete-day/<date_str> requires admin."""
        response = logged_in_client.post("/shift/delete-day/2025-01-01")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /shift/delete-day/<date_str> requires a POST request."""
        response = logged_in_client.get("/shift/delete-day/2025-01-01")
        assert response.status_code == 405

    def test_invalid_date_format(self, logged_in_client):
        """Test that /shift/delete-day/<date_str> handles invalid dates."""
        response = logged_in_client.post("/shift/delete-day/invalid-date")
        assert response.status_code == 302


class TestDeleteAllShiftsForWeek:
    """Tests for POST /shift/delete-week/<date_str>."""

    def test_requires_admin(self, logged_in_client):
        """Test that /shift/delete-week/<date_str> requires admin."""
        response = logged_in_client.post("/shift/delete-week/2025-01-01")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /shift/delete-week/<date_str> requires a POST request."""
        response = logged_in_client.get("/shift/delete-week/2025-01-01")
        assert response.status_code == 405

    def test_invalid_date_format(self, logged_in_client):
        """Test that /shift/delete-week/<date_str> handles invalid dates."""
        response = logged_in_client.post("/shift/delete-week/invalid-date")
        assert response.status_code == 302


class TestDeleteAllOnCalls:
    """Tests for POST /oncall/delete-all."""

    def test_requires_admin(self, logged_in_client):
        """Test that /oncall/delete-all requires admin."""
        response = logged_in_client.post("/oncall/delete-all")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /oncall/delete-all requires a POST request."""
        response = logged_in_client.get("/oncall/delete-all")
        assert response.status_code == 405


class TestDeleteAllOnCallsForUser:
    """Tests for POST /oncall/delete-all-for-user/<user_id>."""

    def test_requires_admin(self, logged_in_client):
        """Test that /oncall/delete-all-for-user/<user_id> requires admin."""
        response = logged_in_client.post("/oncall/delete-all-for-user/1")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test that /oncall/delete-all-for-user/<user_id> requires a POST request."""
        response = logged_in_client.get("/oncall/delete-all-for-user/1")
        assert response.status_code == 405
