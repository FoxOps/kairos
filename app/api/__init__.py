"""
Public REST API for Leviia Schedule (flask-smorest).

Distinct from app/routes/ (session-cookie/Flask-Login, HTML/legacy JSON
responses): every blueprint registered here is authenticated by a
ServiceAccount bearer token (app/auth/service_account_auth.py), never a
cookie, and always returns JSON (see app/api/errors.py for why that
needs an explicit per-blueprint error handler). URL prefix is
/api/v1/*, deliberately distinct from the internal /api/* routes
(app/routes/shift_routes.py etc., cookie-based) to avoid any collision.
See CLAUDE.md's "API publique (flask-smorest)" section for the full
picture.

OPENAPI_SWAGGER_UI_PATH/OPENAPI_REDOC_PATH/OPENAPI_RAPIDOC_PATH are
deliberately left unset: flask-smorest's default UIs pull their JS/CSS
from a CDN that isn't in this app's CSP_POLICY (app/__init__.py), and
relaxing the CSP for an admin-only convenience isn't worth it. Only the
raw spec is exposed (/api/v1/openapi.json), usable in an external
Swagger UI/Postman/Insomnia instance.
"""

from flask import Flask
from flask_smorest import Api

from app.api.errors import JSON_ERROR_CODES, json_error_handler
from app.auth.service_account_auth import resolve_service_account

api = Api()


def init_api(app: Flask) -> None:
    app.config.setdefault("API_TITLE", "Leviia Schedule Public API")
    app.config.setdefault("API_VERSION", "v1")
    app.config.setdefault("OPENAPI_VERSION", "3.0.3")
    app.config.setdefault("OPENAPI_URL_PREFIX", "/api/v1")
    app.config.setdefault("OPENAPI_JSON_PATH", "openapi.json")

    api.init_app(app)

    from app.api.resources import all_blueprints

    for blp in all_blueprints:
        blp.before_request(resolve_service_account)
        for code in JSON_ERROR_CODES:
            blp.register_error_handler(code, json_error_handler)
        api.register_blueprint(blp)
