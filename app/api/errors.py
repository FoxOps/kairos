"""
JSON error handlers for the public API blueprints (app/api/).

app/__init__.py registers app-wide HTML error handlers for 400/401/403/
404/405/500/502/503/504 (_make_http_error_handler, renders e.g.
404.html). Flask resolves error handlers in this precedence order:
blueprint handler for a specific code > app handler for a specific code
> blueprint handler for an exception class > app handler for an
exception class (confirmed against Flask's own
Flask._find_error_handler docstring/implementation). A blueprint-level
handler registered by exception *class* (HTTPException) would therefore
still lose to the app-wide *code*-specific HTML handler - it must be
registered per code, exactly mirroring the app-wide list, for the
public API to reliably return JSON instead of an HTML error page.

Deliberately excludes 422: flask-smorest already installs its own
handler for webargs/marshmallow validation errors there, with
structured per-field detail (`{"code": 422, "errors": {...}, "status":
...}`) - overriding it here would replace that detail with a flat
message and provide strictly less information to API clients.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException

# Mirrors the code list in app/__init__.py's error handler registration
# loop, minus 422 (see module docstring).
JSON_ERROR_CODES = (400, 401, 403, 404, 405, 500, 502, 503, 504)


def json_error_handler(error: HTTPException):
    data = getattr(error, "data", None) or {}
    message = data.get("message") or error.description or str(error)
    return jsonify(message=message), error.code
