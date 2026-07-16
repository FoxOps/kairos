"""
Rate limiting for the public API (app/api/) - keyed by ServiceAccount
identity rather than IP (app-wide default key_func, get_remote_address,
see app/__init__.py), so one integration's traffic never exhausts
another's quota when both happen to share an egress IP. First use of
@limiter.limit() on an individual route in this app - until now only
the app-wide RATELIMIT_DEFAULT existed.
"""

from flask import g
from flask_limiter.util import get_remote_address

API_RATE_LIMIT = "60 per minute, 1000 per day"


def service_account_key() -> str:
    service_account = getattr(g, "service_account", None)
    if service_account is not None:
        return f"service_account:{service_account.id}"
    return get_remote_address()
