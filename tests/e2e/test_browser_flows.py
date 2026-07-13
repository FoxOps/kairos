"""
Tests E2E avec un vrai navigateur (Playwright + Chromium).

Complète tests/e2e/test_user_flows.py (client de test Flask, sans
navigateur) plutôt que de le remplacer - voir report/E2E Playwright -
Tests navigateur réel.md pour la justification complète. Le client de
test Flask n'exécute jamais de JS ni n'applique CSS/CSP : cette suite
couvre exactement la catégorie de bug que ça laisse passer (3 bugs CSP
réels trouvés manuellement lors de la refonte UI/UX, PR #103, avant que
ces tests n'existent).

Nécessite `pip install -r requirements-e2e.txt && playwright install
chromium` - sinon toute la collecte de ce module est skippée
proprement (voir pytest.importorskip ci-dessous), make test/CI ne
casse jamais pour qui n'a pas installé de navigateur.
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
    """Comportement JS pur (toggle is-active/aria-expanded) - jamais
    exécuté par le client de test Flask, donc jamais vérifié avant
    cette suite. Bug réel trouvé et corrigé en PR #103 : le burger
    n'existait même pas."""

    def test_burger_toggles_menu_on_mobile_viewport(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 390, "height": 844})

        burger = page.locator("#navbar-burger")
        menu = page.locator("#navbar-menu")

        assert burger.is_visible()
        assert "is-active" not in (menu.get_attribute("class") or "")
        assert burger.get_attribute("aria-expanded") == "false"

        burger.click()
        page.wait_for_timeout(200)
        assert "is-active" in menu.get_attribute("class")
        assert burger.get_attribute("aria-expanded") == "true"

        burger.click()
        page.wait_for_timeout(200)
        assert "is-active" not in menu.get_attribute("class")

    def test_burger_hidden_on_desktop_viewport(self, logged_in_page):
        page = logged_in_page
        page.set_viewport_size({"width": 1280, "height": 900})

        assert not page.locator("#navbar-burger").is_visible()
        assert page.locator("#navbar-menu").is_visible()


class TestDarkThemeToggle:
    """localStorage + attribut DOM - intestable côté serveur (le client
    de test Flask n'a pas de localStorage)."""

    def test_theme_toggle_persists_after_reload(self, logged_in_page, live_server_url):
        page = logged_in_page
        html = page.locator("html")
        initial_theme = html.get_attribute("data-theme")

        page.click("#theme-toggle")
        page.wait_for_timeout(200)
        toggled_theme = html.get_attribute("data-theme")
        assert toggled_theme != initial_theme

        page.reload()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("data-theme") == toggled_theme


class TestNoConsoleErrors:
    """Garde-fou de régression principal de cette suite : généralise la
    vérification manuelle qui a trouvé 3 bugs CSP réels (PR #103) en
    balayage automatique sur les pages clés. Une erreur console ici
    (violation CSP, script cassé, ressource bloquée) est un signal fort
    qu'une fonctionnalité JS est silencieusement morte en production -
    exactement ce que ni les tests Flask ni une revue de code ne
    peuvent attraper."""

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

        assert not errors, f"{path} : erreur(s) console trouvée(s) :\n" + "\n".join(
            errors
        )


class TestIcsTokenCopyButton:
    """Vérifie le fix PR #103 : le bouton copier était silencieusement
    mort (script inline bloqué par la CSP) avant l'externalisation vers
    static/js/clipboard/copy-token.js."""

    def test_copy_button_shows_feedback(self, logged_in_page, live_server_url):
        page = logged_in_page
        page.goto(f"{live_server_url}/profile/ics-token")
        page.wait_for_load_state("networkidle")

        copy_button = page.locator('button[onclick*="copyToken"]').first
        copy_button.click()
        page.wait_for_timeout(100)

        assert "Copié" in copy_button.inner_text()
