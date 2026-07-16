"""
E2E tests with a real browser (Playwright + Chromium).

Complements tests/e2e/test_user_flows.py (Flask test client, no
browser) rather than replacing it - see report/E2E Playwright - Tests
navigateur réel.md for the full justification. The Flask test client
never executes JS nor applies CSS/CSP: this suite covers exactly the
category of bug that lets through (3 real CSP bugs were found manually
during the UI/UX redesign, before these tests existed).

Requires `pip install -r requirements-e2e.txt && playwright install
chromium` - otherwise collecting this whole module is cleanly skipped
(see pytest.importorskip below), so make test/CI never breaks for
contributors without a browser installed.
"""

import pytest

pytest.importorskip("playwright")

from tests.e2e.conftest import ADMIN_EMAIL, ADMIN_PASSWORD  # noqa: E402


class TestLoginFlow:
    def test_login_with_real_form_submit(self, live_server_url, page):
        page.goto(f"{live_server_url}/login")
        page.fill('input[name="email"]', ADMIN_EMAIL)
        page.fill('input[name="password"]', ADMIN_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        assert "/login" not in page.url
        assert page.locator("text=E2E Admin").first.is_visible()

    def test_wrong_password_shows_error_and_stays_on_login(self, live_server_url, page):
        page.goto(f"{live_server_url}/login")
        page.fill('input[name="email"]', ADMIN_EMAIL)
        page.fill('input[name="password"]', "wrong-password")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url
        assert page.locator("text=incorrect").first.is_visible()


class TestNavbarBurgerMenu:
    """Pure JS behavior (toggling the daisyUI drawer/aria-expanded) -
    never executed by the Flask test client, so never checked before
    this suite. A real bug found and fixed here: the burger didn't even
    exist. Since the sidebar layout redesign (a single vertical
    navigation menu, #sidebar-menu, instead of a horizontal nav plus a
    separate mobile panel): #sidebar-menu is driven by the #mobile-drawer
    checkbox (daisyUI's native CSS mechanism, `drawer lg:drawer-open`) -
    navbar-menu.js only syncs its "checked" state and aria-expanded.
    Below the lg breakpoint, #sidebar-menu is an overlay panel hidden by
    default (checkbox unchecked); from lg up, it stays permanently shown
    as a sidebar (daisyUI ignores the checkbox state at that breakpoint)
    and the burger disappears."""

    def test_burger_toggles_menu_on_mobile_viewport(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 390, "height": 844})

        burger = page.locator("#navbar-burger")
        drawer_toggle = page.locator("#mobile-drawer")

        assert burger.is_visible()
        assert not drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "false"

        burger.click()
        page.wait_for_timeout(200)
        assert drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "true"

        # The open panel (.drawer-side, z-50, position fixed) deliberately
        # covers the burger on screen (standard daisyUI behavior, not a
        # bug) - the realistic mouse gesture to close it is clicking
        # daisyUI's generated overlay (<label for="mobile-drawer">), not
        # re-clicking the burger at the same pixel. Explicit position in
        # the darkened area (outside the w-72 panel): the overlay's
        # default geometric center (which covers the whole viewport)
        # falls under the menu's <ul>, which would intercept the click.
        # This also checks that navbar-menu.js correctly resyncs
        # aria-expanded even when the checkbox is unchecked by something
        # other than a direct click on the burger.
        page.locator(".drawer-overlay").click(position={"x": 350, "y": 400})
        page.wait_for_timeout(200)
        assert not drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "false"

    def test_burger_toggles_via_keyboard(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 390, "height": 844})

        burger = page.locator("#navbar-burger")
        drawer_toggle = page.locator("#mobile-drawer")

        burger.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        assert drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "true"

        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        assert not drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "false"

    def test_escape_closes_menu_and_refocuses_burger(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 390, "height": 844})

        burger = page.locator("#navbar-burger")
        drawer_toggle = page.locator("#mobile-drawer")

        burger.click()
        page.wait_for_timeout(200)
        assert drawer_toggle.is_checked()

        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        assert not drawer_toggle.is_checked()
        assert burger.get_attribute("aria-expanded") == "false"
        assert page.evaluate("document.activeElement.id") == "navbar-burger"

    def test_sidebar_permanent_on_desktop_viewport(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 1280, "height": 900})

        assert not page.locator("#navbar-burger").is_visible()
        assert page.locator("#sidebar-menu").is_visible()


class TestDarkThemeToggle:
    """localStorage + a DOM attribute - untestable server-side (the
    Flask test client has no localStorage)."""

    def test_theme_toggle_persists_after_reload(self, logged_in_page, live_server_url):
        page = logged_in_page
        html = page.locator("html")
        initial_theme = html.get_attribute("data-theme")

        # #theme-toggle is a zero-size checkbox (daisyUI's "Theme
        # Controller" swap pattern, see base.html) - only the icon
        # (.swap-on/.swap-off) is visible. A real user's click goes
        # through the wrapping <label> (native <label><input>...</label>
        # association, no for attribute); clicking the input directly
        # fails even with force=True ("outside of the viewport",
        # Playwright needs real coordinates).
        page.click("label:has(#theme-toggle)")
        page.wait_for_timeout(200)
        toggled_theme = html.get_attribute("data-theme")
        assert toggled_theme != initial_theme

        page.reload()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("data-theme") == toggled_theme


class TestNoConsoleErrors:
    """This suite's main regression guard: generalizes the manual check
    that found 3 real CSP bugs into an automated sweep across the key
    pages. A console error here (CSP violation, broken script, blocked
    resource) is a strong signal that a JS feature is silently dead in
    production - exactly what neither the Flask tests nor a code review
    can catch."""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/dashboard",
            "/schedule",
            "/oncall",
            "/leave",
            "/profile/ics-token",
            "/admin",
            "/admin/automation/full",
            "/admin/service-accounts",
        ],
    )
    def test_page_has_no_console_errors(self, logged_in_page, live_server_url, path):
        page = logged_in_page
        errors = []
        page.on(
            "console",
            lambda msg: errors.append(msg.text) if msg.type == "error" else None,
        )
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        page.goto(f"{live_server_url}{path}")
        page.wait_for_load_state("networkidle")

        assert not errors, f"{path}: console error(s) found:\n" + "\n".join(errors)


class TestIcsTokenCopyButton:
    """Checks the fix for a real bug: the copy button was silently dead
    (inline script blocked by the CSP) before being extracted to
    static/js/clipboard/copy-token.js."""

    def test_copy_button_shows_feedback(self, logged_in_page, live_server_url):
        page = logged_in_page
        page.goto(f"{live_server_url}/profile/ics-token")
        page.wait_for_load_state("networkidle")

        copy_button = page.locator('button[onclick*="copyToken"]').first
        copy_button.click()
        page.wait_for_timeout(100)

        assert "Copié" in copy_button.inner_text()


class TestDeleteConfirmationModal:
    """Regression test: onclick="return Leviia.confirmActionAccessible(...)"
    used to call an async (opened, never blocking) modal and therefore
    returned undefined - the link/form's default navigation/submission
    fired immediately, before the user even clicked Confirm/Cancel in
    the modal. Invisible to the Flask test client (which never executes
    JS) - only a real browser can detect this, hence this test living in
    the real-browser E2E layer."""

    def _add_leave(self, page, live_server_url, start_date, end_date):
        page.goto(f"{live_server_url}/leave/add")
        page.wait_for_load_state("networkidle")
        page.select_option("select[name='user_id']", label="E2E Admin")
        page.fill('input[name="start_date"]', start_date)
        page.fill('input[name="end_date"]', end_date)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

    def test_cancel_in_modal_does_not_delete(self, logged_in_page, live_server_url):
        # A weekend: sidesteps rule 6 (minimum headcount), irrelevant
        # here - only one user exists on this E2E server.
        page = logged_in_page
        self._add_leave(page, live_server_url, "2031-03-01", "2031-03-02")

        page.goto(f"{live_server_url}/leave")
        page.wait_for_load_state("networkidle")
        row = page.locator("tr", has_text="01/03/2031")
        assert row.count() > 0

        row.locator(".js-confirm-delete").first.click()
        page.wait_for_selector(".modal.modal-open")
        page.click(".modal.modal-open button:has-text('Annuler')")
        page.wait_for_timeout(200)

        # Still on /leave (no navigation triggered), leave still present.
        assert "/leave" in page.url
        assert page.locator("tr", has_text="01/03/2031").count() > 0

    def test_confirm_in_modal_deletes(self, logged_in_page, live_server_url):
        page = logged_in_page
        self._add_leave(page, live_server_url, "2031-04-05", "2031-04-06")

        page.goto(f"{live_server_url}/leave")
        page.wait_for_load_state("networkidle")
        row = page.locator("tr", has_text="05/04/2031")
        assert row.count() > 0

        row.locator(".js-confirm-delete").first.click()
        page.wait_for_selector(".modal.modal-open")
        page.click(".modal.modal-open button:has-text('Confirmer')")
        page.wait_for_load_state("networkidle")

        assert page.locator("tr", has_text="05/04/2031").count() == 0


class TestServiceAccountCreationFlow:
    """Real-browser check for the admin service accounts UI
    (app/routes/admin_service_account_routes.py): the token is shown
    exactly once, right after creation, and never again on later
    visits to the same page."""

    def test_create_shows_token_once_then_hidden_on_list(
        self, logged_in_page, live_server_url
    ):
        page = logged_in_page
        page.goto(f"{live_server_url}/admin/service-accounts/add")
        page.fill('input[name="name"]', "Playwright test integration")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        token_input = page.locator("#full-token")
        assert token_input.count() == 1
        token_value = token_input.input_value()
        assert token_value.startswith("lsak_")

        page.goto(f"{live_server_url}/admin/service-accounts")
        page.wait_for_load_state("networkidle")
        assert "Playwright test integration" in page.content()
        assert token_value not in page.content()
