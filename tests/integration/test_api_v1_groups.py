"""
Integration tests for GET /api/v1/groups/[/<id>] (app/api/resources/
groups.py) - resolves the group_id values already present in other
public API responses.
"""


class TestGroupsEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/groups/")
        assert response.status_code == 401

    def test_list_returns_group(self, service_account_client, test_group):
        response = service_account_client.get("/api/v1/groups/")
        assert response.status_code == 200
        groups = response.get_json()
        assert any(g["id"] == test_group.id for g in groups)
        found = next(g for g in groups if g["id"] == test_group.id)
        assert found["name"] == test_group.name

    def test_detail_returns_group(self, service_account_client, test_group):
        response = service_account_client.get(f"/api/v1/groups/{test_group.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == test_group.id
        assert data["name"] == test_group.name

    def test_detail_404_for_unknown_id(self, service_account_client):
        response = service_account_client.get("/api/v1/groups/999999")
        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "not_found"
