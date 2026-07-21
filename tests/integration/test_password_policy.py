"""
Integration tests for the password-strength policy and the forced
first-login password change (ANSSI-PG-078 section 4) - covers the
app-wide before_request hook (app/__init__.py::enforce_password_change),
the admin user-creation/reset flows (UserService.create/update), and
the self-service change (auth.update_profile).
"""

from app import db
from app.models import User


class TestForcedPasswordChangeEnforcement:
    """Tests for the app-wide before_request hook."""

    def test_forced_user_redirected_to_update_profile(self, client, test_group):
        with client.application.app_context():
            user = User(
                name="Forced User",
                email="forced@test.com",
                is_admin=False,
                group_id=test_group.id,
                must_change_password=True,
            )
            user.set_password("Correct-Horse-9")
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"email": "forced@test.com", "password": "Correct-Horse-9"},
        )

        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location.endswith("/profile/update")

    def test_forced_user_can_still_reach_update_profile_and_logout(
        self, client, test_group
    ):
        with client.application.app_context():
            user = User(
                name="Forced User",
                email="forced2@test.com",
                is_admin=False,
                group_id=test_group.id,
                must_change_password=True,
            )
            user.set_password("Correct-Horse-9")
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"email": "forced2@test.com", "password": "Correct-Horse-9"},
        )

        resp = client.get("/profile/update")
        assert resp.status_code == 200

        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302

    def test_non_forced_user_not_redirected(self, test_app, logged_in_client):
        """logged_in_client's user has must_change_password=False by
        model default - normal navigation must be unaffected."""
        resp = logged_in_client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 200

    def test_update_profile_blocks_name_only_submit_while_forced(
        self, client, test_group
    ):
        """A user with must_change_password=True can't sidestep the
        requirement by only editing their name/email and leaving the
        password fields blank."""
        with client.application.app_context():
            user = User(
                name="Forced User",
                email="forced3@test.com",
                is_admin=False,
                group_id=test_group.id,
                must_change_password=True,
            )
            user.set_password("Correct-Horse-9")
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"email": "forced3@test.com", "password": "Correct-Horse-9"},
        )

        resp = client.post(
            "/profile/update",
            data={"name": "Renamed Only", "email": "forced3@test.com"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"nouveau mot de passe avant de continuer" in resp.data

        with client.application.app_context():
            reloaded = User.query.filter_by(email="forced3@test.com").first()
            assert reloaded.must_change_password is True
            assert reloaded.name == "Forced User"  # unchanged

    def test_successful_password_change_clears_flag_and_unblocks_navigation(
        self, client, test_group
    ):
        with client.application.app_context():
            user = User(
                name="Forced User",
                email="forced4@test.com",
                is_admin=False,
                group_id=test_group.id,
                must_change_password=True,
            )
            user.set_password("Correct-Horse-9")
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"email": "forced4@test.com", "password": "Correct-Horse-9"},
        )

        resp = client.post(
            "/profile/update",
            data={
                "name": "Forced User",
                "email": "forced4@test.com",
                "current_password": "Correct-Horse-9",
                "new_password": "Even-Stronger-42",
                "confirm_password": "Even-Stronger-42",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with client.application.app_context():
            reloaded = User.query.filter_by(email="forced4@test.com").first()
            assert reloaded.must_change_password is False

        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 200

    def test_weak_new_password_rejected_even_when_forced(self, client, test_group):
        with client.application.app_context():
            user = User(
                name="Forced User",
                email="forced5@test.com",
                is_admin=False,
                group_id=test_group.id,
                must_change_password=True,
            )
            user.set_password("Correct-Horse-9")
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"email": "forced5@test.com", "password": "Correct-Horse-9"},
        )

        resp = client.post(
            "/profile/update",
            data={
                "name": "Forced User",
                "email": "forced5@test.com",
                "current_password": "Correct-Horse-9",
                "new_password": "short1",
                "confirm_password": "short1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with client.application.app_context():
            reloaded = User.query.filter_by(email="forced5@test.com").first()
            assert reloaded.must_change_password is True
            assert reloaded.check_password("Correct-Horse-9")  # unchanged


class TestAdminCreateUserPasswordPolicy:
    def test_weak_password_rejected(self, logged_in_client, test_group):
        resp = logged_in_client.post(
            "/admin/users/add",
            data={
                "name": "New User",
                "email": "weakpw@test.com",
                "group_id": test_group.id,
                "password": "short1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert User.query.filter_by(email="weakpw@test.com").first() is None

    def test_strong_password_creates_user_forced_to_change(
        self, logged_in_client, test_group
    ):
        resp = logged_in_client.post(
            "/admin/users/add",
            data={
                "name": "New User",
                "email": "strongpw@test.com",
                "group_id": test_group.id,
                "password": "Correct-Horse-9",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        user = User.query.filter_by(email="strongpw@test.com").first()
        assert user is not None
        assert user.must_change_password is True

    def test_blank_password_generates_one_and_flashes_it_once(
        self, logged_in_client, test_group
    ):
        resp = logged_in_client.post(
            "/admin/users/add",
            data={
                "name": "New User",
                "email": "genpw@test.com",
                "group_id": test_group.id,
                "password": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Mot de passe généré automatiquement".encode() in resp.data
        user = User.query.filter_by(email="genpw@test.com").first()
        assert user is not None
        assert user.must_change_password is True


class TestAdminResetPasswordPolicy:
    def test_admin_resetting_password_forces_change(
        self, logged_in_client, test_user, test_group
    ):
        resp = logged_in_client.post(
            f"/admin/users/edit/{test_user.id}",
            data={
                "name": test_user.name,
                "email": test_user.email,
                "group_id": test_group.id,
                "password": "Correct-Horse-9",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with logged_in_client.application.app_context():
            reloaded = db.session.get(User, test_user.id)
            assert reloaded.must_change_password is True
            assert reloaded.check_password("Correct-Horse-9")

    def test_admin_weak_reset_password_rejected(
        self, logged_in_client, test_user, test_group
    ):
        resp = logged_in_client.post(
            f"/admin/users/edit/{test_user.id}",
            data={
                "name": test_user.name,
                "email": test_user.email,
                "group_id": test_group.id,
                "password": "short1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with logged_in_client.application.app_context():
            reloaded = db.session.get(User, test_user.id)
            # Original password untouched, still the fixture's "test123".
            assert reloaded.check_password("test123")

    def test_admin_leaving_password_blank_does_not_force_change(
        self, logged_in_client, test_user, test_group
    ):
        """Editing name/email without touching the password field must
        not retroactively force a change - only an actual password
        reset does."""
        resp = logged_in_client.post(
            f"/admin/users/edit/{test_user.id}",
            data={
                "name": "Renamed",
                "email": test_user.email,
                "group_id": test_group.id,
                "password": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with logged_in_client.application.app_context():
            reloaded = db.session.get(User, test_user.id)
            assert reloaded.must_change_password is False
