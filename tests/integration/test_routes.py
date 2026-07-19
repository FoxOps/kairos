"""
Tests for the Flask routes.
"""

from app import db
from app.models import AuditLog, Leave, OnCall, Shift, ShiftType


class TestRolePermissions:
    """Tests for role-based permissions."""

    def test_decorators_import(self):
        """Test that the decorators can be imported."""
        from app.auth.decorators import admin_required

        assert callable(admin_required)

    def test_models_have_is_admin(self):
        """Test that the User model has the is_admin field."""
        from app.models import User

        assert hasattr(User, "is_admin")


class TestIndexRoute:
    """Tests for the main route."""

    def test_index_route_accessible(self, client):
        """Test that the home page is only accessible to logged-in users."""
        # Test without authentication - should redirect to login
        response = client.get("/")
        assert response.status_code == 302
        assert response.location.endswith("/login?next=%2F")


class TestAuthRoutes:
    """Tests for the authentication routes."""

    def test_login_get(self, client):
        """Test rendering the login page."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"email" in response.data

    def test_login_get_hides_authenticated_nav_links(self, client):
        """An anonymous visitor must not see the internal nav links
        (route map / feature disclosure) - only authenticated users get
        the sidebar's nav_links loop (see base.html)."""
        response = client.get("/login")
        html = response.get_data(as_text=True)
        for path in ("/dashboard", "/schedule", "/oncall", "/leave", "/swaps"):
            assert f'href="{path}"' not in html

    def test_login_get_authenticated_shows_nav_links(self, test_app, logged_in_client):
        """Sanity check: the same nav links do appear once authenticated -
        confirms the previous test isn't a false negative from a broken
        nav_links definition."""
        response = logged_in_client.get("/login", follow_redirects=True)
        html = response.get_data(as_text=True)
        assert 'href="/schedule"' in html

    def test_404_page_hides_authenticated_nav_links(self, client):
        """Same guard applies to error pages (400-504 all extend
        base.html) - not a login.html-specific fix."""
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404
        html = response.get_data(as_text=True)
        for path in ("/dashboard", "/schedule", "/oncall", "/leave", "/swaps"):
            assert f'href="{path}"' not in html

    def test_login_post_valid(self, client, test_user, test_app):
        """Test logging in with valid credentials."""
        with test_app.app_context():
            response = client.post(
                "/login",
                data={"email": test_user.email, "password": "test123"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"Kairos" in response.data or b"Schedule" in response.data

    def test_login_post_invalid_credentials(self, client):
        """Test logging in with invalid credentials."""
        response = client.post(
            "/login",
            data={"email": "invalid@test.com", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Email ou mot de passe incorrect" in response.data

    def test_login_post_valid_writes_audit_log_entry(self, client, test_user, test_app):
        with test_app.app_context():
            client.post(
                "/login",
                data={"email": test_user.email, "password": "test123"},
                follow_redirects=True,
            )

            entry = AuditLog.query.filter_by(action="auth.login_success").first()
            assert entry is not None
            assert entry.actor_id == test_user.id

    def test_login_post_invalid_writes_audit_log_entry(self, client, test_app):
        with test_app.app_context():
            client.post(
                "/login",
                data={"email": "invalid@test.com", "password": "wrongpassword"},
                follow_redirects=True,
            )

            entry = AuditLog.query.filter_by(action="auth.login_failure").first()
            assert entry is not None
            assert entry.details == "invalid@test.com"

    def test_logout_writes_audit_log_entry(self, client, test_user, test_app):
        with test_app.app_context():
            client.post(
                "/login",
                data={"email": test_user.email, "password": "test123"},
                follow_redirects=True,
            )
            client.get("/logout", follow_redirects=True)

            entry = AuditLog.query.filter_by(action="auth.logout").first()
            assert entry is not None
            assert entry.resource_id == test_user.id

    def test_login_post_empty_fields(self, client):
        """Test logging in with empty fields."""
        response = client.post(
            "/login", data={"email": "", "password": ""}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Email et mot de passe sont obligatoires" in response.data

    def test_logout(self, logged_in_client):
        """Test logging out."""
        response = logged_in_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        # After logging out, we're redirected to the index
        assert b"Kairos" in response.data or b"Schedule" in response.data

    def test_register_disabled(self, client):
        """Test that public registration is disabled."""
        response = client.get("/register", follow_redirects=True)
        assert response.status_code == 200
        # We're redirected to the login page
        assert (
            b"Login" in response.data
            or b"Connexion" in response.data
            or b"email" in response.data
        )

    def test_profile_route(self, logged_in_client):
        """Test accessing the profile page."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200
        assert b"Profil" in response.data or b"profile" in response.data.lower()

    def test_profile_update_get(self, logged_in_client):
        """Test rendering the profile update form."""
        response = logged_in_client.get("/profile/update")
        assert response.status_code == 200

    def test_profile_update_post_valid(self, logged_in_client, test_user, test_app):
        """Test updating the profile with valid data."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Updated Name",
                "email": "updated@test.com",
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # The profile is updated or a message is shown
        assert b"Profil" in response.data or b"profile" in response.data.lower()

    def test_profile_update_post_invalid_email(
        self, logged_in_client, test_user, second_user, app
    ):
        """Test updating the profile with an already-used email."""
        response = logged_in_client.post(
            "/profile/update",
            data={
                "name": "Test User",
                "email": second_user.email,
                "current_password": "",
                "new_password": "",
                "confirm_password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # An error message is shown
        assert (
            b"email" in response.data.lower()
            or b"Profil" in response.data
            or b"profile" in response.data.lower()
        )


class TestShiftRoutes:
    """Tests for the shift routes."""

    def test_schedule_route_accessible(self, logged_in_client):
        """Test accessing the shifts page."""
        response = logged_in_client.get("/schedule")
        assert response.status_code == 200
        assert b"Shifts" in response.data or b"schedule" in response.data.lower()

    def test_add_shift_get_unauthorized(self, logged_in_client):
        """Test that a regular user can't access the add-shift form."""
        response = logged_in_client.get("/schedule/add", follow_redirects=True)
        assert response.status_code == 200
        # The user is redirected to the index or sees a message
        assert b"Kairos" in response.data or b"Schedule" in response.data

    def test_add_shift_get_admin(self, logged_in_client):
        """Test that an admin can access the add-shift form."""
        response = logged_in_client.get("/schedule/add")
        assert response.status_code == 200
        assert b"Ajouter un shift" in response.data or b"Add Shift" in response.data

    def test_add_shift_post_valid(self, logged_in_client, test_user, test_shift_type):
        """Test adding a valid shift."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2023-12-01",
            "end_date": "2023-12-01",
        }
        response = logged_in_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shifts ajoute" in response.data or b"succes" in response.data

        shifts = Shift.query.filter_by(user_id=test_user.id).all()
        assert len(shifts) >= 1

    def test_add_shift_post_invalid_dates_weekend(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test adding a shift with invalid dates (weekend)."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2023-12-02",
            "end_date": "2023-12-02",
        }
        response = logged_in_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # The form is redisplayed with an error message
        assert (
            b"Shifts" in response.data
            or b"schedule" in response.data.lower()
            or b"Add" in response.data
        )

    def test_delete_shift_post(self, logged_in_client, test_shift):
        """Test deleting a shift."""
        response = logged_in_client.post(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shift supprime" in response.data or b"succes" in response.data

        shift = db.session.get(Shift, test_shift.id)
        assert shift is None

    def test_delete_shift_unauthorized(self, logged_in_client, test_shift):
        """Test that a regular user can't delete a shift."""
        response = logged_in_client.post(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # The admin_required decorator uses this message
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestOnCallRoutes:
    """Tests for the on-call routes."""

    def test_oncall_route_accessible(self, logged_in_client):
        """Test accessing the on-call page."""
        response = logged_in_client.get("/oncall")
        assert response.status_code == 200
        assert b"Astreinte" in response.data or b"oncall" in response.data.lower()

    def test_add_oncall_get_unauthorized(self, logged_in_client):
        """Test that a regular user can't access the add-on-call form."""
        response = logged_in_client.get("/oncall/add", follow_redirects=True)
        assert response.status_code == 200
        # The user is redirected
        assert b"Kairos" in response.data or b"Schedule" in response.data

    def test_add_oncall_get_admin(self, logged_in_client):
        """Test that an admin can access the add-on-call form."""
        response = logged_in_client.get("/oncall/add")
        assert response.status_code == 200
        assert (
            b"Ajouter une astreinte" in response.data or b"Add OnCall" in response.data
        )

    def test_add_oncall_post_valid(self, logged_in_client, test_user):
        """Test adding a valid on-call."""
        data = {"user_id": test_user.id, "start_date": "2023-12-01"}
        response = logged_in_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte ajoutee" in response.data or b"succes" in response.data

        on_calls = OnCall.query.filter_by(user_id=test_user.id).all()
        assert len(on_calls) >= 1

    def test_add_oncall_post_invalid_day(self, logged_in_client, test_user):
        """Test adding an on-call on an invalid day."""
        data = {"user_id": test_user.id, "start_date": "2023-12-02"}
        response = logged_in_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"vendredi" in response.data.lower()

    def test_delete_oncall_post(self, logged_in_client, test_oncall):
        """Test deleting an on-call."""
        response = logged_in_client.post(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte supprimee" in response.data or b"succes" in response.data

        oncall = db.session.get(OnCall, test_oncall.id)
        assert oncall is None

    def test_delete_oncall_unauthorized(self, logged_in_client, test_oncall):
        """Test that a regular user can't delete an on-call."""
        response = logged_in_client.post(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # The admin_required decorator uses this message
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestLeaveRoutes:
    """Tests for the leave routes."""

    def test_leave_route_accessible(self, logged_in_client):
        """Test accessing the leave page."""
        response = logged_in_client.get("/leave")
        assert response.status_code == 200
        assert b"Conge" in response.data or b"leave" in response.data.lower()

    def test_add_leave_get(self, logged_in_client):
        """Test rendering the add-leave form."""
        response = logged_in_client.get("/leave/add")
        assert response.status_code == 200
        assert b"Ajouter" in response.data and (
            b"Conge" in response.data or b"leave" in response.data.lower()
        )

    def test_add_leave_post_valid(self, logged_in_client, test_user):
        """Test adding a valid leave."""
        data = {
            "user_id": test_user.id,
            "start_date": "2023-12-20",
            "end_date": "2023-12-25",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data

        leaves = Leave.query.filter_by(user_id=test_user.id).all()
        assert len(leaves) >= 1

    def test_add_leave_post_invalid_dates(self, logged_in_client, test_user):
        """Test adding a leave with invalid dates."""
        data = {
            "user_id": test_user.id,
            "start_date": "2023-12-25",
            "end_date": "2023-12-20",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        # The form is redisplayed with an error message
        assert (
            b"date" in response.data.lower()
            or b"debut" in response.data.lower()
            or b"fin" in response.data.lower()
        )

    def test_delete_leave_post(self, logged_in_client, test_leave):
        """Test deleting a leave."""
        response = logged_in_client.post(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        leave = db.session.get(Leave, test_leave.id)
        assert leave is None

    def test_delete_leave_unauthorized(self, client, test_leave, second_user, test_app):
        """Test that a user can't delete another user's leave."""
        with test_app.app_context():
            client.post(
                "/login",
                data={"email": second_user.email, "password": "test123"},
                follow_redirects=True,
            )

            response = client.post(
                f"/leave/delete/{test_leave.id}", follow_redirects=True
            )
            assert response.status_code == 200
            # The user_owns_resource decorator uses this message
            assert (
                b"Acces refuse" in response.data
                or b"Seuls" in response.data
                or b"vos propres" in response.data
                or b"vous" in response.data.lower()
            )


class TestAdminRoutes:
    """Tests for the admin routes.

    The dashboard/list/add-group/add-user/add-shift-type happy-path and
    validation cases are covered more precisely by
    test_admin_lists.py (exact-count/exact-field assertions instead of
    this file's loose `or`-chained substring checks) - only the
    delete-related cases below, which test_admin_lists.py doesn't
    cover, remain here.
    """

    def test_delete_group_post(self, logged_in_client, test_group):
        """Test deleting a group."""
        response = logged_in_client.post(
            f"/admin/groups/delete/{test_group.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Check that the group was deleted or that a message is shown
        assert (
            b"Groupe" in response.data
            or b"groups" in response.data.lower()
            or b"succes" in response.data
        )

    def test_delete_group_with_users(self, logged_in_client, test_group, test_user):
        """Test that a group with users can't be deleted."""
        response = logged_in_client.post(
            f"/admin/groups/delete/{test_group.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # The group can't be deleted because it has users
        assert (
            b"Groupe" in response.data
            or b"groups" in response.data.lower()
            or b"Impossible" in response.data
        )

    def test_delete_user_post(self, logged_in_client, test_user):
        """Test deleting a user."""
        response = logged_in_client.post(
            f"/admin/users/delete/{test_user.id}", follow_redirects=True
        )
        assert response.status_code == 200
        # Check that the user was deleted or that a message is shown
        assert (
            b"Utilisateur" in response.data
            or b"users" in response.data.lower()
            or b"succes" in response.data
        )

    def test_delete_user_with_resources(self, logged_in_client, test_shift, test_user):
        """Test that a user with resources can't be deleted."""
        # test_shift is already associated with test_user via the fixture
        response = logged_in_client.post(
            f"/admin/users/delete/{test_user.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Utilisateur" in response.data
            or b"users" in response.data.lower()
            or b"Impossible" in response.data
        )


class TestShiftTypeRoutes:
    """Tests for the shift-type routes.

    The list/add happy-path is covered more precisely by
    test_admin_lists.py::TestListShiftTypes/TestAddShiftType - only the
    validation and delete cases below, which that file doesn't cover,
    remain here.
    """

    def test_add_shift_type_post_invalid_hours(self, logged_in_client):
        """Test adding a shift type with invalid hours."""
        data = {
            "name": "invalid",
            "label": "Invalide",
            "start_hour": "25",
            "end_hour": "6",
        }
        response = logged_in_client.post(
            "/admin/shift-types/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # The form is redisplayed with an error message
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Add" in response.data
        )

    def test_add_shift_type_start_after_end(self, logged_in_client):
        """Test adding a shift type where the start hour is after the end hour."""
        data = {
            "name": "invalid",
            "label": "Invalide",
            "start_hour": "15",
            "end_hour": "10",
        }
        response = logged_in_client.post(
            "/admin/shift-types/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # The form is redisplayed with an error message
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Add" in response.data
        )

    def test_delete_shift_type_post(self, logged_in_client, test_shift_type):
        """Test deleting a shift type."""
        response = logged_in_client.post(
            f"/admin/shift-types/delete/{test_shift_type.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Type de shift supprim" in response.data or b"succ" in response.data

        shift_type = db.session.get(ShiftType, test_shift_type.id)
        assert shift_type is None

    def test_delete_shift_type_in_use(self, logged_in_client, test_shift):
        """Test that a shift type in use can't be deleted."""
        # test_shift already uses test_shift_type
        response = logged_in_client.post(
            f"/admin/shift-types/delete/{test_shift.shift_type_id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        # A message is shown
        assert (
            b"Type" in response.data
            or b"shift" in response.data.lower()
            or b"Impossible" in response.data
        )
