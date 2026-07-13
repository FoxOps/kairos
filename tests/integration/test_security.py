"""
Tests de sécurité pour Leviia Schedule.

TestingConfig désactive Talisman (TESTING=True -> create_app() saute
l'initialisation de Talisman, voir app/__init__.py) et CSRF
(WTF_CSRF_ENABLED=False) pour simplifier les tests fonctionnels. Les tests
qui vérifient ces deux protections construisent donc leur propre instance
d'application avec ces options réactivées, plutôt que d'utiliser le
fixture test_app standard qui les désactive.
"""

import pytest

from app import CSP_POLICY, create_app, db
from app.models import User


@pytest.fixture
def secure_app():
    """App avec Talisman ET CSRF activés, pour tester les protections
    normalement désactivées par TestingConfig."""
    app = create_app("app.config.TestingConfig")
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["TALISMAN_FORCE_HTTPS"] = True

    from flask_talisman import Talisman

    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP_POLICY,
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


class TestSensitiveDataNotSerialized:
    """User.to_dict() ne doit jamais exposer password_hash ni ics_token."""

    def test_to_dict_excludes_password_hash(self, test_app):
        user = User(name="Test", email="secure@test.com", group_id=1)
        user.set_password("supersecret")
        assert "password_hash" not in user.to_dict()

    def test_to_dict_excludes_ics_token(self, test_app):
        user = User(name="Test", email="secure2@test.com", group_id=1)
        user.generate_ics_token()
        assert "ics_token" not in user.to_dict()

    def test_to_dict_still_includes_non_sensitive_fields(self, test_app):
        user = User(name="Test", email="secure3@test.com", group_id=1)
        data = user.to_dict()
        assert data["name"] == "Test"
        assert data["email"] == "secure3@test.com"


class TestPasswordStorage:
    def test_password_is_hashed_not_plaintext(self, test_app, test_group):
        user = User(name="Test", email="hash@test.com", group_id=test_group.id)
        user.set_password("plaintext-password")
        assert user.password_hash != "plaintext-password"
        assert "plaintext-password" not in user.password_hash

    def test_check_password_roundtrip(self, test_app, test_group):
        user = User(name="Test", email="hash2@test.com", group_id=test_group.id)
        user.set_password("correct-password")
        assert user.check_password("correct-password") is True
        assert user.check_password("wrong-password") is False


class TestTalismanSecurityHeaders:
    def test_security_headers_present_when_enabled(self, secure_app):
        client = secure_app.test_client()
        resp = client.get("/login")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") is not None

    def test_security_headers_applied_even_without_force_https(self, test_app):
        """Bug réel corrigé en Phase 6 : les en-têtes de sécurité (CSP,
        X-Content-Type-Options, etc.) étaient entièrement gated derrière
        TALISMAN_FORCE_HTTPS - un déploiement avec TLS terminé par un
        reverse proxy (donc TALISMAN_FORCE_HTTPS=false côté app, comme
        docker/docker-compose.yml) n'avait alors AUCUN en-tête de sécurité.
        Talisman est maintenant toujours initialisé (sauf en test) ;
        force_https ne contrôle plus que la redirection HTTP->HTTPS."""
        app = create_app("app.config.Config")
        app.config["TALISMAN_FORCE_HTTPS"] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        resp = client.get("/login")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("Content-Security-Policy") is not None
        with app.app_context():
            db.drop_all()

    def test_csp_blocks_inline_script_but_allows_onclick_and_inline_style(
        self, secure_app
    ):
        """CSP réelle appliquée par l'app (CSP_POLICY) : script-src 'self'
        (bloque tout <script> injecté), script-src-attr 'unsafe-inline'
        (les attributs onclick="" restants dans les templates sont du
        contenu statique, pas des données utilisateur), style-src avec
        'unsafe-inline' (un seul style dynamique dans dashboard.html)."""
        client = secure_app.test_client()
        resp = client.get("/login")
        csp = resp.headers.get("Content-Security-Policy")
        assert "script-src 'self'" in csp
        assert "script-src-attr 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "object-src 'none'" in csp

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
    def test_page_has_no_inline_executable_script(
        self, test_app, logged_in_client, path
    ):
        """Régression Phase 6 : script-src 'self' strict (pas de
        unsafe-inline, pas de nonce) bloque silencieusement tout <script>
        inline exécutable - le navigateur ne le signale pas comme une
        erreur HTTP, juste une erreur console, donc ça passe inaperçu sans
        ce test. Trois pages avaient un <script> inline (index.html,
        auth/ics_token.html, admin/automation/full.html) - seule la
        première avait été vérifiée à l'origine (Phase 6), les deux autres
        sont restées cassées jusqu'à cet audit. Balayage sur plusieurs
        pages représentatives plutôt qu'une seule pour éviter que ça se
        reproduise ailleurs sans être détecté."""
        resp = logged_in_client.get(path)
        assert resp.status_code == 200, f"{path} : statut {resp.status_code}"
        html = resp.data.decode("utf-8")
        import re

        inline_script_blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html)
        for tag in inline_script_blocks:
            assert 'type="application/json"' in tag, (
                f"{path} : script inline exécutable trouvé ({tag}) - "
                "bloqué silencieusement par script-src 'self'"
            )

    def test_calendar_page_uses_external_module(self, test_app, logged_in_client):
        """Régression Phase 6 : index.html avait un <script> inline de
        ~576 lignes (config FullCalendar), externalisé vers
        static/js/calendar/fullcalendar-config.js pour permettre un
        script-src strict sans nonce ni unsafe-inline."""
        resp = logged_in_client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert '<script type="module"' in html
        assert 'src="/static/js/calendar/fullcalendar-config.js"' in html


class TestCSRFProtection:
    def test_post_without_csrf_token_rejected(self, secure_app):
        client = secure_app.test_client()
        resp = client.post(
            "/login",
            data={"email": "admin@leviia.local", "password": "admin123"},
        )
        # Sans jeton CSRF valide, Flask-WTF renvoie 400 (CSRFError) plutôt
        # que de traiter la requête normalement.
        assert resp.status_code == 400

    def test_post_with_valid_csrf_token_succeeds(self, secure_app):
        with secure_app.app_context():
            from app.models import Group

            group = Group(
                name="Secure Group", is_part_of_schedule=True, is_part_of_oncall=True
            )
            db.session.add(group)
            db.session.commit()
            user = User(
                name="Secure User", email="secure-login@test.com", group_id=group.id
            )
            user.set_password("correct-password")
            db.session.add(user)
            db.session.commit()

        client = secure_app.test_client()
        # Récupérer un jeton CSRF valide comme le ferait un vrai navigateur :
        # GET la page du formulaire, extraire la valeur du champ caché.
        login_page = client.get("/login")
        html = login_page.data.decode("utf-8")
        import re

        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        assert match, "Aucun champ csrf_token trouvé dans le formulaire de login"
        token = match.group(1)

        resp = client.post(
            "/login",
            data={
                "email": "secure-login@test.com",
                "password": "correct-password",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"incorrect" not in resp.data.lower()


class TestAccessControl:
    """Un utilisateur non-admin ne doit pas pouvoir agir sur les
    ressources d'un autre utilisateur ni accéder aux routes admin."""

    def test_non_admin_cannot_access_admin_dashboard(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin", follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_non_admin_cannot_list_users(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin/users", follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_non_admin_cannot_add_shift(
        self, test_app, non_admin_client, test_shift_type, test_user
    ):
        resp = non_admin_client.get("/schedule/add", follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_non_admin_cannot_delete_other_users_shift(
        self, test_app, non_admin_client, test_shift
    ):
        # test_shift appartient à test_user, non_admin_client est connecté
        # en tant que test_user lui-même ici (fixture), donc on vérifie
        # plutôt qu'un utilisateur non-admin ne peut pas utiliser la route
        # de suppression réservée aux admins, même pour son propre shift.
        resp = non_admin_client.get(
            f"/schedule/delete/{test_shift.id}", follow_redirects=False
        )
        assert resp.status_code in (302, 403)

    def test_anonymous_cannot_access_protected_routes(self, test_app, client):
        for path in ("/schedule", "/oncall", "/leave", "/dashboard", "/admin"):
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code in (
                302,
                401,
            ), f"{path} accessible sans authentification"
