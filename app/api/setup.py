"""
One-time-per-blueprint wiring for the public API (app/api/resources).

Deliberately separate from app/api/__init__.py::init_api(): Flask
blueprints only allow "setup" calls (before_request, error_handler
registration) *before* their first registration on an app - and this
app's module-level `app = create_app()` (app/__init__.py) plus the test
suite's per-test create_app() calls mean create_app() runs many times
in the same process, reusing the same blueprint *objects* every time
(they're module-level singletons, like main_bp/admin_bp). Calling
blp.before_request()/register_error_handler() from inside init_api()
(which reruns on every create_app() call) would raise
"blueprint has already been registered" from the second call onward.
configure_blueprint() is instead called once, at import time, directly
in each resource module right after the Blueprint is created - module
import itself only happens once per process, regardless of how many
times create_app() runs. Only api.register_blueprint() (attaching an
already-configured blueprint to a specific app instance) belongs in
init_api().
"""

from flask_smorest import Blueprint

from app.api.errors import JSON_ERROR_CODES, json_error_handler
from app.auth.service_account_auth import resolve_service_account


def configure_blueprint(blp: Blueprint) -> None:
    blp.before_request(resolve_service_account)
    for code in JSON_ERROR_CODES:
        blp.register_error_handler(code, json_error_handler)
