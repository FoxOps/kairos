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

Now also includes 422 and 429: flask-smorest installs its own 422
handler (webargs/marshmallow validation errors) and Flask-Limiter's
RateLimitExceeded is just another HTTPException - both are normally
caught by flask-smorest's own APP-level handler, registered by
*exception class* (flask_smorest.error_handler.ErrorHandlerMixin.
_register_error_handlers: `self._app.register_error_handler(
HTTPException, self.handle_http_exception)`, confirmed by reading that
source directly). Per the precedence order above, THIS module's
per-*code* blueprint handlers win over that app-level class handler, so
registering 422/429 here re-shapes both into the same
{"error": {"code", "message", "details"}} envelope as every other
public API error, without needing to fight or monkeypatch
flask-smorest/Flask-Limiter - the underlying data (webargs' validation
`messages`, the breached-limit description) is simply read from
error.data / error.description as before.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException

# Mirrors the code list in app/__init__.py's error handler registration
# loop, plus 422/429 (see module docstring - these two are NOT part of
# that app-wide HTML list, they're specific to this JSON API).
JSON_ERROR_CODES = (400, 401, 403, 404, 405, 422, 429, 500, 502, 503, 504)

# Stable error codes for the public API's error envelope - never renamed
# once shipped, generated SDKs may switch on these.
_ERROR_CODES_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "service_unavailable",
    503: "service_unavailable",
    504: "service_unavailable",
}


def json_error_handler(error: HTTPException):
    """{"error": {"code", "message", "details"}} for every JSON_ERROR_CODES
    status - the one predictable envelope every public API error uses,
    replacing flask-smorest's own default shape
    (`{"code", "status", "message", "errors"}`) for consistency across
    every status this API can return, 422/429 included."""
    data = getattr(error, "data", None) or {}
    status_code = error.code or 500
    code = _ERROR_CODES_BY_STATUS.get(status_code, "internal_error")
    details = data.get("messages") or data.get("errors") or None
    message = data.get("message") or error.description or str(error)
    if code == "validation_error" and "message" not in data:
        message = "Request validation failed."
    response = jsonify(error={"code": code, "message": message, "details": details})
    response.status_code = status_code
    for name, value in (data.get("headers") or {}).items():
        response.headers[name] = value
    return response
