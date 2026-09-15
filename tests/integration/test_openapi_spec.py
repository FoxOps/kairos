"""
Tests for the auto-generated OpenAPI spec (app/api/, flask-smorest) -
the public API's documentation, distinct from the hand-maintained
Docs/api/openapi.yaml (internal /api/* routes, session cookie).
"""


class TestOpenApiJson:
    def test_returns_valid_spec(self, client):
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["openapi"] == "3.0.3"
        assert data["info"]["title"] == "Kairos Public API"

    def test_oncall_current_path_is_documented(self, client):
        # Regression guard: OnCallCurrent returns its own
        # flask.jsonify(...) Response instead of a plain dict/list (the
        # response shape depends on group_id), so @blp.response only
        # gets used for documentation there (per flask_smorest's own
        # "Response object" short-circuit) - confirms that trick still
        # produces a real 200 schema rather than silently documenting
        # nothing.
        response = client.get("/api/v1/openapi.json")
        data = response.get_json()
        current_get = data["paths"]["/api/v1/oncall/current"]["get"]
        schema_ref = current_get["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert schema_ref["type"] == "array"
        assert "$ref" in schema_ref["items"]

    def test_no_session_cookie_required(self, client):
        # No login performed - the spec itself must stay reachable
        # without a bearer token or a session, same as e.g. GitHub's
        # public OpenAPI spec.
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200


class TestSwaggerUiDisabled:
    def test_no_interactive_ui_served(self, client):
        # OPENAPI_SWAGGER_UI_PATH/OPENAPI_REDOC_PATH/OPENAPI_RAPIDOC_PATH
        # are deliberately left unset (app/api/__init__.py) - CSP
        # doesn't allow the CDN these default UIs pull from.
        for path in ("/api/v1/swagger-ui", "/api/v1/redoc", "/api/v1/rapidoc"):
            response = client.get(path)
            assert response.status_code == 404
