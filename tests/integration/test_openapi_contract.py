"""
Contract tests for the generated OpenAPI document (/api/v1/openapi.json,
app/api/) - guards against regressions in the spec itself (missing
metadata, duplicate/missing operationIds, undocumented status codes,
untyped fields), independent of runtime behavior (see
test_api_v1_routes.py/test_api_scopes.py/test_api_rate_limiting.py for
that). Uses openapi_spec_validator to confirm the document is valid
OpenAPI 3.0.3, not just "some JSON that has the right top-level keys".
"""

from flask import Flask
from openapi_spec_validator import validate

from app.api import init_api


class TestOpenApiValidity:
    def test_spec_is_valid_openapi(self, client):
        response = client.get("/api/v1/openapi.json")
        spec = response.get_json()
        validate(spec)  # raises on any schema/reference error

    def test_openapi_version_is_3_0_3(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        assert spec["openapi"] == "3.0.3"


class TestInfoAndServers:
    def test_info_title_and_version_exist(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        assert spec["info"]["title"]
        assert spec["info"]["version"]

    def test_info_description_exists(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        assert spec["info"]["description"]

    def test_servers_present_and_non_empty(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        assert spec.get("servers")
        assert spec["servers"][0]["url"]


class TestServersUrlFromPublicBaseUrl:
    """Regression guard: PUBLIC_BASE_URL must be used verbatim as the
    OpenAPI server origin, never combined with request/app host - a bug
    report claimed the two get concatenated into e.g.
    "https://host/host". Exercises init_api() directly on a bare Flask
    app (bypassing create_app()) since Config.PUBLIC_BASE_URL is a class
    attribute frozen at module-import time and can't be varied per-test
    via env vars/monkeypatch without a module reload."""

    def test_uses_configured_public_base_url_verbatim(self):
        app = Flask(__name__)
        app.config["PUBLIC_BASE_URL"] = "https://kairos.mydomain.tld"
        init_api(app)

        url = app.config["API_SPEC_OPTIONS"]["servers"][0]["url"]
        assert url == "https://kairos.mydomain.tld"
        assert url.count("kairos.mydomain.tld") == 1

    def test_falls_back_to_relative_root_when_unset(self):
        app = Flask(__name__)
        init_api(app)

        assert app.config["API_SPEC_OPTIONS"]["servers"][0]["url"] == "/"


class TestSecurityScheme:
    def test_bearer_scheme_documented(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        scheme = spec["components"]["securitySchemes"]["ServiceAccountBearer"]
        assert scheme["type"] == "http"
        assert scheme["scheme"] == "bearer"

    def test_security_applied_globally(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        assert spec["security"] == [{"ServiceAccountBearer": []}]


def _operations(spec):
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if isinstance(op, dict) and "operationId" in op:
                yield path, method, op


class TestOperations:
    def test_every_operation_has_operation_id(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        for path, method, op in _operations(spec):
            assert op.get("operationId"), f"{method.upper()} {path} missing operationId"

    def test_operation_ids_are_unique(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        ids = [op["operationId"] for _, _, op in _operations(spec)]
        assert len(ids) == len(set(ids))

    def test_expected_operation_ids_present(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        ids = {op["operationId"] for _, _, op in _operations(spec)}
        assert ids == {
            "listShifts",
            "getShift",
            "listOnCallPeriods",
            "getOnCallPeriod",
            "getCurrentOnCall",
            "listLeave",
            "getLeave",
            "listUsers",
            "getUser",
            "listShiftTypes",
            "listGroups",
            "getGroup",
        }

    def test_every_operation_has_summary(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        for path, method, op in _operations(spec):
            assert op.get("summary"), f"{method.upper()} {path} missing summary"

    def test_every_operation_documents_401_and_429(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        for path, method, op in _operations(spec):
            responses = op.get("responses", {})
            assert "401" in responses, f"{method.upper()} {path} missing 401"
            assert "429" in responses, f"{method.upper()} {path} missing 429"

    def test_detail_operations_document_404(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        for path, method, op in _operations(spec):
            if "{" in path:  # every detail route has a path parameter
                responses = op.get("responses", {})
                assert "404" in responses, f"{method.upper()} {path} missing 404"

    def test_filtered_list_operations_document_422(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        filtered_list_ids = {
            "listShifts",
            "listOnCallPeriods",
            "getCurrentOnCall",
            "listLeave",
            "listUsers",
        }
        for _path, _method, op in _operations(spec):
            if op["operationId"] in filtered_list_ids:
                assert "422" in op.get("responses", {}), op["operationId"]


class TestSchemaTypes:
    def test_duration_fields_are_numeric(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        schemas = spec["components"]["schemas"]
        assert schemas["Shift"]["properties"]["duration_hours"]["type"] == "number"
        assert schemas["OnCall"]["properties"]["duration_hours"]["type"] == "number"
        assert schemas["Leave"]["properties"]["duration_days"]["type"] == "integer"

    def test_datetime_fields_use_date_time_format(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        schemas = spec["components"]["schemas"]
        for schema_name, field in (
            ("Shift", "start_time"),
            ("Shift", "end_time"),
            ("OnCall", "start_time"),
            ("OnCall", "end_time"),
        ):
            prop = schemas[schema_name]["properties"][field]
            assert prop["type"] == "string"
            assert prop["format"] == "date-time"

    def test_id_query_params_have_minimum_one(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        op = spec["paths"]["/api/v1/shifts/"]["get"]
        params_by_name = {p["name"]: p for p in op["parameters"]}
        for name in ("user_id", "group_id", "shift_type_id"):
            assert params_by_name[name]["schema"]["minimum"] == 1

    def test_page_query_param_documented(self, client):
        spec = client.get("/api/v1/openapi.json").get_json()
        op = spec["paths"]["/api/v1/shifts/"]["get"]
        page_param = next(p for p in op["parameters"] if p["name"] == "page")
        assert page_param["schema"]["minimum"] == 1
        assert page_param["schema"]["default"] == 1
