"""
Rate limiting for the public API (app/api/) - keyed by ServiceAccount
identity rather than IP (app-wide default key_func, get_remote_address,
see app/__init__.py), so one integration's traffic never exhausts
another's quota when both happen to share an egress IP. First use of
@limiter.limit() on an individual route in this app - until now only
the app-wide RATELIMIT_DEFAULT existed.

api_rate_limit() is passed as a *callable* limit value (Flask-Limiter
evaluates it once per request via current_app), not a plain string -
every @limiter.limit() decorator below is applied at class-definition/
import time, before any Flask app exists (and this module is imported
once per process while create_app() runs many times, e.g. in tests), so
the configured value (app.config["API_RATE_LIMIT"], see
app/config/base.py) can only be resolved per-request, not baked in at
decoration time.
"""

from flask import current_app, g
from flask_limiter.util import get_remote_address


def api_rate_limit() -> str:
    return current_app.config["API_RATE_LIMIT"]


def service_account_key() -> str:
    service_account = getattr(g, "service_account", None)
    if service_account is not None:
        return f"service_account:{service_account.id}"
    return get_remote_address()
