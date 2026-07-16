"""
Fixtures for the public API's bearer-token auth (ServiceAccount,
app/models/service_account.py). Same pattern as user_fixtures.py's
logged_in_client, but for /api/v1/* instead of session-cookie routes.
"""

import pytest

from app import db
from app.services.service_account_service import ServiceAccountService


@pytest.fixture
def service_account(test_app):
    """A ServiceAccount plus its full bearer token in clear (only
    available at creation time, exactly like in the real admin UI)."""
    with test_app.app_context():
        sa, full_token = ServiceAccountService.create_account("Test integration")
        db.session.commit()
        return sa, full_token


@pytest.fixture
def service_account_client(test_app, service_account):
    """Test client pre-configured with a valid Authorization header -
    the /api/v1/* equivalent of logged_in_client."""
    _, full_token = service_account
    with test_app.test_client(use_cookies=True) as client:
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {full_token}"
        yield client
