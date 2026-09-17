"""
Tests for GET /api/v1 (discovery) and GET /api/v1/docs (Scalar
interactive documentation), app/api/docs_view.py.
"""


class TestDiscovery:
    def test_returns_expected_shape(self, client):
        response = client.get("/api/v1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Kairos Public API"
        assert data["version"] == "v1"
        assert data["openapi"] == "/api/v1/openapi.json"
        assert data["documentation"] == "/api/v1/docs"

    def test_no_auth_required(self, client):
        # Discovery must be reachable without a bearer token, same as
        # the raw spec itself.
        response = client.get("/api/v1")
        assert response.status_code == 200


class TestDocsPage:
    def test_enabled_by_default(self, client):
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
        assert response.content_type.startswith("text/html")
        assert b"api-reference" in response.data

    def test_disabled_via_config(self, test_app, client):
        test_app.config["PUBLIC_API_DOCS_ENABLED"] = False
        try:
            response = client.get("/api/v1/docs")
            assert response.status_code == 404
        finally:
            test_app.config["PUBLIC_API_DOCS_ENABLED"] = True

    def test_openapi_json_reachable_even_when_docs_disabled(self, test_app, client):
        test_app.config["PUBLIC_API_DOCS_ENABLED"] = False
        try:
            response = client.get("/api/v1/openapi.json")
            assert response.status_code == 200
        finally:
            test_app.config["PUBLIC_API_DOCS_ENABLED"] = True
