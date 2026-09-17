"""
Plain Flask views for the public API's discovery endpoint and
interactive documentation page - deliberately NOT flask-smorest
resources (no schema-documented model, nothing to add to the OpenAPI
spec itself) and NOT registered as a Blueprint the way app/api/resources/
are: no ServiceAccount auth needed here (both are meant to be reachable
by anyone exploring the API, same as /api/v1/openapi.json itself), so
they're plain views wired directly onto the app in
app/api/__init__.py::init_api().
"""

from flask import Flask, Response, abort, jsonify, url_for

_SCALAR_JS_URL = "https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.25.75/dist/browser/standalone.js"


def discovery() -> Response:
    """GET /api/v1 - minimal machine-readable entry point (name,
    version, links to the spec and interactive docs). Every link is a
    relative path, not an absolute PUBLIC_BASE_URL-based URL, so it
    resolves correctly regardless of whether that setting is
    configured, and never leaks a deployment-specific hostname."""
    return jsonify(
        {
            "name": "Kairos Public API",
            "version": "v1",
            "openapi": url_for("api-docs.openapi_json"),
            "documentation": url_for("api_docs_page"),
        }
    )


def docs_page():
    """GET /api/v1/docs - Scalar interactive documentation, loaded from
    cdn.jsdelivr.net (already CSP-whitelisted for FullCalendar, see
    app/__init__.py's CSP_POLICY - no CSP change needed for this page).
    Gated by PUBLIC_API_DOCS_ENABLED (default on); the raw spec stays
    reachable either way. Scalar reads the spec's own securitySchemes
    (app/api/__init__.py's API_SPEC_OPTIONS) to expose an Authorize
    button automatically - no extra Scalar configuration needed for
    that."""
    from flask import current_app

    if not current_app.config.get("PUBLIC_API_DOCS_ENABLED", True):
        abort(404)

    openapi_url = url_for("api-docs.openapi_json")
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Kairos Public API</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>
<script id="api-reference" data-url="{openapi_url}"></script>
<script src="{_SCALAR_JS_URL}"></script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


def register_docs_views(app: Flask) -> None:
    """Called once per create_app() from app/api/__init__.py::init_api() -
    plain app.add_url_rule() calls are safe to repeat across the many app
    instances this process can build (e.g. one per test), unlike
    flask-smorest's blueprint before_request/error_handler registration
    (see app/api/setup.py's own docstring for why those must run only
    once at import time)."""
    app.add_url_rule("/api/v1", endpoint="api_discovery", view_func=discovery)
    app.add_url_rule("/api/v1/docs", endpoint="api_docs_page", view_func=docs_page)
