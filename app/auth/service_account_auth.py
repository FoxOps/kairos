"""
Bearer-token authentication for the public API (app/api/, /api/v1/*).

Not to be confused with app/auth/decorators.py (session-cookie based,
HTML redirects on failure) - this module never touches Flask-Login or
current_user, and always fails with a JSON body, matching the public
API's contract. See CLAUDE.md's "API publique (flask-smorest)" section.
"""

from flask import g, request
from flask_smorest import abort

from app.models import ServiceAccount
from app.repositories.service_account_repository import ServiceAccountRepository


def resolve_service_account() -> None:
    """before_request hook registered on every flask-smorest Blueprint
    (see app/api/__init__.py) - populates g.service_account or aborts
    with a JSON 401 via flask_smorest.abort(). Each blueprint also
    registers a JSON error handler for this abort (see app/api/errors.py)
    so it never falls through to the app-wide HTML error pages."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, message="Missing or malformed Authorization header.")

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        abort(401, message="Missing or malformed Authorization header.")

    token_hash = ServiceAccount.hash_token(token)
    service_account = ServiceAccountRepository.get_by_token_hash(token_hash)

    if service_account is None or not service_account.is_valid():
        abort(401, message="Invalid, revoked, or expired API token.")
    assert (  # nosec B101 - abort() above already raised; this is a mypy narrowing hint only
        service_account is not None
    )  # flask_smorest.abort() has no mypy stub NoReturn signal

    g.service_account = service_account
    ServiceAccountRepository.touch_last_used(service_account)
