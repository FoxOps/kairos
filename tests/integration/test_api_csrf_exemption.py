"""
Tests that every public API blueprint (app/api/resources) is exempted
from CSRFProtect (app/__init__.py) - safe only because this blueprint
never accepts cookie-based auth, see app/auth/service_account_auth.py.
"""

from app import csrf
from app.api.resources import all_blueprints


class TestCsrfExemption:
    def test_every_api_blueprint_is_csrf_exempt(self, test_app):
        assert set(all_blueprints) <= csrf._exempt_blueprints
