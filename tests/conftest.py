"""
Test configuration for Leviia Schedule.

This version uses create_app() to build a fresh app instance for the
tests, which allows disabling Talisman before it initializes.

Updated for Flask 3.x and Flask-Login 0.6.3.
"""

import os
import warnings

import pytest

# Filter datetime.utcnow() deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flask_login")

# Import the required modules - deliberately after the
# warnings.filterwarnings() call above: importing `app` triggers
# flask_limiter, whose warning must already be filtered by then.
from app import db, limiter  # noqa: E402

# Model fixtures (user/group, shift/shift_type, leave, oncall) extracted
# into tests/fixtures/ - declared here so they stay visible across all
# subdirectories (unit/integration/e2e) without an explicit per-test
# import.
pytest_plugins = [
    "tests.fixtures.user_fixtures",
    "tests.fixtures.shift_fixtures",
    "tests.fixtures.leave_fixtures",
    "tests.fixtures.oncall_fixtures",
    "tests.fixtures.swap_fixtures",
]


@pytest.fixture(scope="function")
def test_app():
    """
    Fixture that builds a fresh app instance for the tests.
    Disables Talisman and OIDC before it initializes.
    Scope: function, to avoid conflicts between tests.
    """
    # Save and disable OIDC for the tests
    original_oidc_enabled = os.environ.get("OIDC_ENABLED")
    original_oidc_disable_basic = os.environ.get("OIDC_DISABLE_BASIC_AUTH")
    os.environ["OIDC_ENABLED"] = "False"
    os.environ["OIDC_DISABLE_BASIC_AUTH"] = "False"

    # Reload the OIDC configuration
    from config_oidc import OIDCConfig

    OIDCConfig.ENABLED = False
    OIDCConfig.DISABLE_BASIC_AUTH = False

    # Build a fresh app instance with a test configuration
    from app import create_app

    app = create_app("app.config.TestingConfig")

    # Disable the rate limiter
    limiter.enabled = False

    # Disable the cache for the tests
    from app.utils.cache import CacheConfig

    CacheConfig.CACHE_ENABLED = False

    # Create an app context
    with app.app_context():
        # Recreate the tables for the test
        db.drop_all()
        db.create_all()
        yield app
        # Clean up after the test
        db.session.rollback()
        db.drop_all()

    # Restore OIDC
    if original_oidc_enabled is not None:
        os.environ["OIDC_ENABLED"] = original_oidc_enabled
    else:
        os.environ.pop("OIDC_ENABLED", None)
    if original_oidc_disable_basic is not None:
        os.environ["OIDC_DISABLE_BASIC_AUTH"] = original_oidc_disable_basic
    else:
        os.environ.pop("OIDC_DISABLE_BASIC_AUTH", None)
    OIDCConfig.load_config()


@pytest.fixture
def client(test_app):
    """Flask test client with cookies and sessions enabled.

    Does NOT create a default user, to avoid conflicts between tests.
    """
    with test_app.test_client(use_cookies=True) as client:
        yield client


# Alias required by pytest-flask: its autouse _configure_application
# fixture looks for a fixture named exactly "app" (see pytest_flask/plugin.py).
app = test_app
