"""
E2E test of the full SSO flow, in a real browser, against a real fake
OIDC provider (tests/e2e/oidc_mock_provider.py) - not a Python-level
function mock (see tests/integration/test_oidc_routes.py for that).
This test exercises the real end-to-end HTTP wiring: browser redirect
to the IdP, a real login page with a click, return with an authorization
code, real server-to-server exchanges (OIDC discovery,
exchange_code_for_token, get_user_info), user creation, session
establishment, RP-initiated logout.

Requires `pip install -r requirements-e2e.txt && playwright install
chromium` - otherwise collection is cleanly skipped
(pytest.importorskip).
"""

import pytest

pytest.importorskip("playwright")

from tests.e2e.oidc_mock_provider import MOCK_USER_NAME  # noqa: E402


class TestOidcBrowserLogin:
    def test_login_redirects_straight_to_idp(self, oidc_live_servers, page):
        app_url, idp_url = oidc_live_servers
        page.goto(f"{app_url}/login")
        page.wait_for_load_state("networkidle")

        assert page.url.startswith(idp_url)
        assert page.locator("#mock-idp-approve").is_visible()

    def test_full_sso_round_trip_creates_and_logs_in_user(
        self, oidc_live_servers, page
    ):
        app_url, idp_url = oidc_live_servers

        page.goto(f"{app_url}/login")
        page.wait_for_load_state("networkidle")
        assert page.url.startswith(idp_url)

        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")

        # Back on the app side, session open, OIDC user created on the fly.
        assert page.url.startswith(app_url)
        assert "/login" not in page.url
        assert page.locator(f"text={MOCK_USER_NAME}").first.is_visible()

    def test_second_login_reuses_existing_synced_user(
        self, oidc_live_servers, page, browser
    ):
        app_url, idp_url = oidc_live_servers

        # First round trip: creates the user.
        page.goto(f"{app_url}/login")
        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")

        # browser.new_context() (not context.new_page()): a new page in
        # the same context would share `page`'s session cookies (already
        # logged in) and skip login entirely - an isolated context is
        # needed for a genuine 2nd SSO round trip.
        context2 = browser.new_context()
        page2 = context2.new_page()
        page2.goto(f"{app_url}/login")
        page2.wait_for_load_state("networkidle")
        page2.click("#mock-idp-approve")
        page2.wait_for_load_state("networkidle")

        assert page2.url.startswith(app_url)
        assert "/login" not in page2.url
        assert page2.locator(f"text={MOCK_USER_NAME}").first.is_visible()
        context2.close()


class TestOidcBrowserLogout:
    def test_logout_redirects_to_idp_end_session_endpoint(
        self, oidc_live_servers, page
    ):
        app_url, idp_url = oidc_live_servers

        page.goto(f"{app_url}/login")
        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")
        assert "/login" not in page.url

        page.goto(f"{app_url}/logout")
        page.wait_for_load_state("networkidle")

        # build_logout_url() sends the user to the IdP (the mock's
        # end_session_endpoint, /logout) - a local-only logout would
        # leave the session active on the provider side (a bug already
        # fixed elsewhere, see app/auth/oidc_auth.py::build_logout_url).
        assert page.url.startswith(idp_url)

    def test_protected_page_requires_new_login_after_logout(
        self, oidc_live_servers, page
    ):
        app_url, idp_url = oidc_live_servers

        page.goto(f"{app_url}/login")
        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")

        page.goto(f"{app_url}/logout")
        page.wait_for_load_state("networkidle")

        page.goto(f"{app_url}/dashboard")
        page.wait_for_load_state("networkidle")
        # @login_required must redirect away from /dashboard (to /login
        # then /oidc/login, since /logout invalidated the session) - all
        # the way to the fake IdP's login page, not stay on the
        # dashboard. Not checking for the absence of MOCK_USER_EMAIL on
        # the page here: the mock IdP's own login form displays that
        # email itself (indicating which user the click will
        # authenticate), so that assertion would always be true even if
        # /logout did nothing.
        assert page.url.startswith(idp_url)


class TestOidcBrowserSingleFlashMessage:
    def test_no_stale_login_required_flash_after_redirect_from_protected_page(
        self, oidc_live_servers, page
    ):
        """Regression test: visiting a protected page (login_required)
        while unauthenticated used to trigger Flask-Login's default
        "please log in" flash before the redirect to auth.oidc_login -
        which never renders a template and immediately continues on to
        the IdP. That flash then survived the whole SSO round trip
        without ever being consumed, and ended up stuck alongside the
        "Connexion OIDC réussie !" flash on the first page rendered
        afterwards (both shown at once). Fix: login_manager.login_message
        is disabled in forced-OIDC mode (app/__init__.py)."""
        app_url, idp_url = oidc_live_servers

        # A protected page (not /login): triggers @login_required.
        page.goto(f"{app_url}/dashboard")
        page.wait_for_load_state("networkidle")
        assert page.url.startswith(idp_url)

        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")

        assert page.url.startswith(app_url)
        alerts = page.locator(".flash-message")
        assert alerts.count() == 1
        assert "Connexion OIDC réussie" in alerts.first.inner_text()
        assert "log in" not in page.content().lower()
