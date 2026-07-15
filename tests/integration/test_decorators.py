"""
Tests for the permission decorators.
"""

from datetime import datetime, timedelta


class TestDecoratorImports:
    """Tests for importing the decorators."""

    def test_admin_required_import(self):
        """Test that the admin_required decorator can be imported."""
        from app.auth.decorators import admin_required

        assert callable(admin_required)

    def test_user_owns_resource_import(self):
        """Test that the user_owns_resource decorator can be imported."""
        from app.auth.decorators import user_owns_resource

        assert callable(user_owns_resource)


class TestDecoratorProperties:
    """Tests for the decorators' properties."""

    def test_decorator_preserves_function_name(self, test_app):
        """Test that the decorator preserves the function name."""
        from app.auth.decorators import admin_required

        @admin_required
        def test_function():
            return "Test", 200

        assert test_function.__name__ == "test_function"

    def test_decorator_preserves_function_docstring(self, test_app):
        """Test that the decorator preserves the function's docstring."""
        from app.auth.decorators import admin_required

        @admin_required
        def test_function():
            """This is a test function."""
            return "Test", 200

        assert test_function.__doc__ == "This is a test function."

    def test_admin_required_is_callable(self, test_app):
        """Test that admin_required is callable."""
        from app.auth.decorators import admin_required

        @admin_required
        def dummy():
            pass

        assert callable(dummy)

    def test_user_owns_resource_is_callable(self, test_app):
        """Test that user_owns_resource is callable."""
        from app.auth.decorators import user_owns_resource
        from app.models import Leave

        decorated_func = user_owns_resource(Leave, "leave_id")
        assert callable(decorated_func)


class TestAdminRequiredDecorator:
    """Tests for the admin_required decorator."""

    def test_admin_required_allows_admin(self, logged_in_client):
        """Test that an admin can access admin routes."""
        response = logged_in_client.get("/admin")
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"admin" in response.data.lower()

    def test_admin_required_blocks_non_admin(self, logged_in_client):
        """Test that a regular user can't access admin routes."""
        response = logged_in_client.get("/admin", follow_redirects=True)
        assert response.status_code == 200
        # The user is redirected to the index
        assert b"Leviia" in response.data or b"Schedule" in response.data
        # The error message should be present
        assert (
            b"Acces refuse" in response.data
            or b"permissions" in response.data.lower()
            or b"admin" in response.data.lower()
        )


class TestUserOwnsResourceDecorator:
    """Tests for the user_owns_resource decorator."""

    def test_user_can_delete_own_leave(
        self, logged_in_client, test_leave, test_user, app
    ):
        """Test that a user can delete their own leave."""
        # test_leave is already associated with test_user via the fixture
        # test_user is already logged in via logged_in_client
        response = logged_in_client.post(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        # Check that the leave was deleted
        from app import db
        from app.models import Leave

        leave = db.session.get(Leave, test_leave.id)
        assert leave is None

    def test_user_cannot_delete_others_leave(
        self, client, test_leave, second_user, test_app
    ):
        """Test that a user can't delete another user's leave."""
        with test_app.app_context():
            # Log in as second_user
            client.post(
                "/login",
                data={"email": second_user.email, "password": "test123"},
                follow_redirects=True,
            )

            # Try to delete test_user's leave (which is test_leave)
            response = client.post(
                f"/leave/delete/{test_leave.id}", follow_redirects=True
            )
            assert response.status_code == 200
            # The error message should be present
            assert b"Acces refuse" in response.data or b"vos propres" in response.data

            # Check that the leave was not deleted
            from app import db
            from app.models import Leave

            leave = db.session.get(Leave, test_leave.id)
            assert leave is not None

    def test_admin_can_delete_any_leave(self, logged_in_client, test_leave, test_app):
        """Test that an admin can delete any leave."""
        response = logged_in_client.post(
            f"/leave/delete/{test_leave.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Conge supprime" in response.data or b"succes" in response.data

        # Check that the leave was deleted
        from app import db
        from app.models import Leave

        leave = db.session.get(Leave, test_leave.id)
        assert leave is None


class TestShiftPermissions:
    """Tests for shift permissions."""

    def test_admin_can_add_shift(self, logged_in_client, test_user, test_shift_type):
        """Test that an admin can add a shift."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2025-12-01",
            "end_date": "2025-12-01",
        }
        response = logged_in_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shifts ajoute" in response.data or b"succes" in response.data

    def test_non_admin_cannot_add_shift(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test that a regular user can't add a shift."""
        data = {
            "user_id": test_user.id,
            "shift_type_id": test_shift_type.id,
            "start_date": "2025-12-01",
            "end_date": "2025-12-01",
        }
        response = logged_in_client.post(
            "/schedule/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        # The user is redirected with an error message
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )

    def test_admin_can_delete_shift(self, logged_in_client, test_shift):
        """Test that an admin can delete a shift."""
        response = logged_in_client.post(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Shift supprime" in response.data or b"succes" in response.data

        from app import db
        from app.models import Shift

        shift = db.session.get(Shift, test_shift.id)
        assert shift is None

    def test_non_admin_cannot_delete_shift(self, logged_in_client, test_shift):
        """Test that a regular user can't delete a shift."""
        response = logged_in_client.post(
            f"/schedule/delete/{test_shift.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestOnCallPermissions:
    """Tests for on-call permissions."""

    def test_admin_can_add_oncall(self, logged_in_client, test_user):
        """Test that an admin can add an on-call."""
        # Find a Friday in the future
        now = datetime.now()
        days_until_friday = (4 - now.weekday()) % 7
        friday_date = (now + timedelta(days=days_until_friday + 7)).strftime("%Y-%m-%d")

        data = {"user_id": test_user.id, "start_date": friday_date}
        response = logged_in_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte ajoutee" in response.data or b"succes" in response.data

    def test_non_admin_cannot_add_oncall(self, logged_in_client, test_user):
        """Test that a regular user can't add an on-call."""
        data = {"user_id": test_user.id, "start_date": "2025-12-06"}  # A Friday
        response = logged_in_client.post(
            "/oncall/add", data=data, follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )

    def test_admin_can_delete_oncall(self, logged_in_client, test_oncall):
        """Test that an admin can delete an on-call."""
        response = logged_in_client.post(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Astreinte supprimee" in response.data or b"succes" in response.data

        from app import db
        from app.models import OnCall

        oncall = db.session.get(OnCall, test_oncall.id)
        assert oncall is None

    def test_non_admin_cannot_delete_oncall(self, logged_in_client, test_oncall):
        """Test that a regular user can't delete an on-call."""
        response = logged_in_client.post(
            f"/oncall/delete/{test_oncall.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert (
            b"Acces refuse" in response.data
            or b"admin" in response.data.lower()
            or b"Seuls les administrateurs" in response.data
        )


class TestLeavePermissions:
    """Tests for leave permissions."""

    def test_user_can_add_own_leave(self, logged_in_client, test_user):
        """Test that a user can add their own leave."""
        data = {
            "user_id": test_user.id,
            "start_date": "2025-12-20",
            "end_date": "2025-12-25",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data

    def test_user_cannot_add_others_leave(
        self, client, test_user, second_user, test_app
    ):
        """Test that a user can't add a leave for someone else."""
        with test_app.app_context():
            # Log in as second_user
            client.post(
                "/login",
                data={"email": second_user.email, "password": "test123"},
                follow_redirects=True,
            )

            # Try to add a leave for test_user
            data = {
                "user_id": test_user.id,
                "start_date": "2025-12-20",
                "end_date": "2025-12-25",
            }
            response = client.post("/leave/add", data=data, follow_redirects=True)
            assert response.status_code == 200
            # The error message should be present
            # The message is "Vous ne pouvez ajouter des congés que pour vous-même."
            # Checked in ASCII to avoid encoding issues
            assert (
                b"vous" in response.data.lower()
                and b"pour vous" in response.data.lower()
                or b"Seuls" in response.data
            )

    def test_admin_can_add_leave_for_anyone(self, logged_in_client, test_user):
        """Test that an admin can add a leave for anyone."""
        data = {
            "user_id": test_user.id,
            "start_date": "2025-12-20",
            "end_date": "2025-12-25",
        }
        response = logged_in_client.post("/leave/add", data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Conge ajoute" in response.data or b"succes" in response.data
