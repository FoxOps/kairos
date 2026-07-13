"""
Test E2E du flux SSO complet, dans un vrai navigateur, contre un faux
fournisseur OIDC réel (tests/e2e/oidc_mock_provider.py) - pas un mock
Python au niveau des fonctions (voir tests/integration/test_oidc_routes.py
pour ça). Ce test exerce le vrai câblage HTTP de bout en bout :
redirection navigateur vers l'IdP, vraie page de login avec un clic,
retour avec un code d'autorisation, échanges serveur-à-serveur réels
(découverte OIDC, exchange_code_for_token, get_user_info), création
d'utilisateur, établissement de session, déconnexion RP-initiated.

Nécessite `pip install -r requirements-e2e.txt && playwright install
chromium` - sinon collecte skippée proprement (pytest.importorskip).
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

        # De retour côté app, session ouverte, utilisateur OIDC créé à la volée.
        assert page.url.startswith(app_url)
        assert "/login" not in page.url
        assert page.locator(f"text={MOCK_USER_NAME}").first.is_visible()

    def test_second_login_reuses_existing_synced_user(
        self, oidc_live_servers, page, browser
    ):
        app_url, idp_url = oidc_live_servers

        # Premier aller-retour : crée l'utilisateur.
        page.goto(f"{app_url}/login")
        page.click("#mock-idp-approve")
        page.wait_for_load_state("networkidle")

        # browser.new_context() (pas context.new_page()) : une nouvelle
        # page dans le même contexte partagerait les cookies de session
        # de `page` (déjà connectée) et sauterait directement le login -
        # il faut un contexte isolé pour un vrai 2e aller-retour SSO.
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

        # build_logout_url() envoie vers l'IdP (end_session_endpoint du
        # mock, /logout) - la déconnexion locale seule laisserait la
        # session côté fournisseur active (bug déjà corrigé ailleurs,
        # voir app/auth/oidc_auth.py::build_logout_url).
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
        # @login_required doit rediriger loin de /dashboard (vers /login
        # puis /oidc/login, la session ayant été invalidée par /logout) -
        # jusqu'à la page de login du faux IdP, pas rester sur le
        # dashboard. Ne pas vérifier l'absence de MOCK_USER_EMAIL dans la
        # page ici : le formulaire de login du mock IdP lui-même affiche
        # cet email (indiquant quel utilisateur le clic va authentifier),
        # donc cette assertion serait toujours vraie même si /logout ne
        # faisait rien.
        assert page.url.startswith(idp_url)
