"""
Security tests for Leviia Schedule.

TestingConfig disables Talisman (TESTING=True -> create_app() skips
Talisman's initialization, see app/__init__.py) and CSRF
(WTF_CSRF_ENABLED=False) to simplify the functional tests. The tests
that check these two protections therefore build their own app
instance with these options re-enabled, instead of using the standard
test_app fixture that disables them.
"""

import pytest

from app import CSP_POLICY, create_app, db
from app.models import User


@pytest.fixture
def secure_app():
    """App with both Talisman and CSRF enabled, to test the protections
    TestingConfig normally disables."""
    app = create_app("app.config.TestingConfig")
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["TALISMAN_FORCE_HTTPS"] = True

    from flask_talisman import Talisman

    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP_POLICY,
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", False),
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


class TestSensitiveDataNotSerialized:
    """User.to_dict() must never expose password_hash or ics_token."""

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
        """Regression test: the security headers (CSP,
        X-Content-Type-Options, etc.) used to be entirely gated behind
        TALISMAN_FORCE_HTTPS - a deployment with TLS terminated by a
        reverse proxy (so TALISMAN_FORCE_HTTPS=false on the app side, as
        in docker/docker-compose.yml) then had NO security headers at
        all. Talisman is now always initialized (except in tests);
        force_https only controls the HTTP->HTTPS redirect."""
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

    def test_session_cookie_not_forced_secure_without_https(self):
        """Regression test (v1.0 load testing): Flask-Talisman's own
        session_cookie_secure default is True, independent of
        force_https - its before_request hook overwrites
        app.config["SESSION_COOKIE_SECURE"] to True on every request
        whenever app.debug is False, silently ignoring this app's own
        SESSION_COOKIE_SECURE setting. Confirmed end-to-end with a real
        gunicorn process: in the documented default configuration
        (TALISMAN_FORCE_HTTPS=false, SESSION_COOKIE_SECURE=false, no TLS
        anywhere in the chain, e.g. `python run.py` ->
        http://localhost:5000), the browser silently drops the Secure
        session cookie over plain HTTP - login appeared to succeed (302)
        but no session ever persisted, every subsequent request was
        anonymous again."""
        app = create_app("app.config.Config")
        app.config["TALISMAN_FORCE_HTTPS"] = False
        app.config["SESSION_COOKIE_SECURE"] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        client.get("/login")
        assert app.config["SESSION_COOKIE_SECURE"] is False
        with app.app_context():
            db.drop_all()

    def test_csp_blocks_inline_script_but_allows_onclick_and_inline_style(
        self, secure_app
    ):
        """The real CSP enforced by the app (CSP_POLICY): script-src 'self'
        (blocks any injected <script>), script-src-attr 'unsafe-inline'
        (the remaining onclick="" attributes in the templates are static
        content, not user data), style-src with 'unsafe-inline' (a single
        dynamic style in dashboard.html)."""
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
        """Regression test: a strict script-src 'self' (no unsafe-inline,
        no nonce) silently blocks any executable inline <script> - the
        browser doesn't report it as an HTTP error, just a console error,
        so it goes unnoticed without this test. Three pages had an inline
        <script> (index.html, auth/ics_token.html,
        admin/automation/full.html) - only the first one had originally
        been checked, the other two stayed broken until this was caught.
        This sweeps several representative pages instead of just one so
        the same regression can't reappear elsewhere undetected."""
        resp = logged_in_client.get(path)
        assert resp.status_code == 200, f"{path}: status {resp.status_code}"
        html = resp.data.decode("utf-8")
        import re

        inline_script_blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html)
        for tag in inline_script_blocks:
            assert 'type="application/json"' in tag, (
                f"{path}: found an executable inline script ({tag}) - "
                "silently blocked by script-src 'self'"
            )

    def test_calendar_page_uses_external_module(self, test_app, logged_in_client):
        """Regression test: index.html used to have a ~576-line inline
        <script> (the FullCalendar config), extracted to
        static/js/calendar/fullcalendar-config.js to allow a strict
        script-src with no nonce or unsafe-inline."""
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
        # Without a valid CSRF token, Flask-WTF returns 400 (CSRFError)
        # instead of processing the request normally.
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
        # Fetch a valid CSRF token the way a real browser would: GET the
        # form page, extract the hidden field's value.
        login_page = client.get("/login")
        html = login_page.data.decode("utf-8")
        import re

        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        assert match, "No csrf_token field found in the login form"
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
    """A non-admin user must not be able to act on another user's
    resources, nor access the admin routes."""

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
        # test_shift belongs to test_user, and non_admin_client is
        # logged in as test_user itself here (fixture), so this really
        # checks that a non-admin user can't use the delete route
        # reserved for admins, even for their own shift.
        resp = non_admin_client.post(
            f"/schedule/delete/{test_shift.id}", follow_redirects=False
        )
        assert resp.status_code in (302, 403)

    def test_anonymous_cannot_access_protected_routes(self, test_app, client):
        for path in ("/schedule", "/oncall", "/leave", "/dashboard", "/admin"):
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code in (
                302,
                401,
            ), f"{path} accessible without authentication"
