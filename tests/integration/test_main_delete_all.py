"""
Tests pour les routes de suppression en masse dans main.py
Couvre les routes delete-all non testées précédemment.
"""


class TestDeleteAllShifts:
    """Tests pour POST /shift/delete-all."""

    def test_requires_admin(self, logged_in_client):
        """Test que /shift/delete-all nécessite admin."""
        response = logged_in_client.post("/shift/delete-all")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /shift/delete-all nécessite une requête POST."""
        response = logged_in_client.get("/shift/delete-all")
        assert response.status_code == 405  # Method Not Allowed


class TestDeleteAllShiftsForUser:
    """Tests pour POST /shift/delete-all-for-user/<user_id>."""

    def test_requires_admin(self, logged_in_client):
        """Test que /shift/delete-all-for-user/<user_id> nécessite admin."""
        response = logged_in_client.post("/shift/delete-all-for-user/1")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /shift/delete-all-for-user/<user_id> nécessite une requête POST."""
        response = logged_in_client.get("/shift/delete-all-for-user/1")
        assert response.status_code == 405


class TestDeleteAllShiftsForDay:
    """Tests pour POST /shift/delete-day/<date_str>."""

    def test_requires_admin(self, logged_in_client):
        """Test que /shift/delete-day/<date_str> nécessite admin."""
        response = logged_in_client.post("/shift/delete-day/2025-01-01")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /shift/delete-day/<date_str> nécessite une requête POST."""
        response = logged_in_client.get("/shift/delete-day/2025-01-01")
        assert response.status_code == 405

    def test_invalid_date_format(self, logged_in_client):
        """Test que /shift/delete-day/<date_str> gère les dates invalides."""
        response = logged_in_client.post("/shift/delete-day/invalid-date")
        assert response.status_code == 302


class TestDeleteAllShiftsForWeek:
    """Tests pour POST /shift/delete-week/<date_str>."""

    def test_requires_admin(self, logged_in_client):
        """Test que /shift/delete-week/<date_str> nécessite admin."""
        response = logged_in_client.post("/shift/delete-week/2025-01-01")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /shift/delete-week/<date_str> nécessite une requête POST."""
        response = logged_in_client.get("/shift/delete-week/2025-01-01")
        assert response.status_code == 405

    def test_invalid_date_format(self, logged_in_client):
        """Test que /shift/delete-week/<date_str> gère les dates invalides."""
        response = logged_in_client.post("/shift/delete-week/invalid-date")
        assert response.status_code == 302


class TestDeleteAllOnCalls:
    """Tests pour POST /oncall/delete-all."""

    def test_requires_admin(self, logged_in_client):
        """Test que /oncall/delete-all nécessite admin."""
        response = logged_in_client.post("/oncall/delete-all")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /oncall/delete-all nécessite une requête POST."""
        response = logged_in_client.get("/oncall/delete-all")
        assert response.status_code == 405


class TestDeleteAllOnCallsForUser:
    """Tests pour POST /oncall/delete-all-for-user/<user_id>."""

    def test_requires_admin(self, logged_in_client):
        """Test que /oncall/delete-all-for-user/<user_id> nécessite admin."""
        response = logged_in_client.post("/oncall/delete-all-for-user/1")
        assert response.status_code in [302, 403]

    def test_requires_post(self, logged_in_client):
        """Test que /oncall/delete-all-for-user/<user_id> nécessite une requête POST."""
        response = logged_in_client.get("/oncall/delete-all-for-user/1")
        assert response.status_code == 405
