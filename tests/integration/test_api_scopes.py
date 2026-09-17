"""
Tests for ServiceAccount read scopes (app/models/service_account.py,
app/auth/service_account_auth.py::require_scope). Doesn't use the
shared service_account_client fixture (always full access) - builds
scoped ServiceAccounts directly per test.
"""

from app import db
from app.services.service_account_service import ServiceAccountService


def _client_for(test_app, scopes=None, name="scoped"):
    with test_app.app_context():
        _, token = ServiceAccountService.create_account(name, scopes=scopes)
        db.session.commit()
    client = test_app.test_client()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


class TestScopeEnforcement:
    def test_no_scopes_means_full_access(self, test_app):
        client = _client_for(test_app, scopes=None)
        assert client.get("/api/v1/shifts/").status_code == 200
        assert client.get("/api/v1/oncall/").status_code == 200
        assert client.get("/api/v1/leave/").status_code == 200
        assert client.get("/api/v1/users/").status_code == 200
        assert client.get("/api/v1/shift-types/").status_code == 200
        assert client.get("/api/v1/groups/").status_code == 200

    def test_read_wildcard_means_full_access(self, test_app):
        client = _client_for(test_app, scopes=["read:*"])
        assert client.get("/api/v1/oncall/").status_code == 200

    def test_restricted_scope_allows_matching_resource(self, test_app):
        client = _client_for(test_app, scopes=["read:shifts"])
        assert client.get("/api/v1/shifts/").status_code == 200

    def test_restricted_scope_denies_other_resources(self, test_app):
        client = _client_for(test_app, scopes=["read:shifts"])
        for path in (
            "/api/v1/oncall/",
            "/api/v1/leave/",
            "/api/v1/users/",
            "/api/v1/shift-types/",
            "/api/v1/groups/",
        ):
            response = client.get(path)
            assert response.status_code == 403, path
            body = response.get_json()
            assert body["error"]["code"] == "forbidden"

    def test_oncall_current_gated_by_read_oncall_scope(self, test_app):
        client = _client_for(test_app, scopes=["read:leave"])
        response = client.get("/api/v1/oncall/current")
        assert response.status_code == 403
