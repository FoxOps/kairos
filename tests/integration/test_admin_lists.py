"""
Tests for the list_* routes in admin.py.
"""

from app.models import Group, ShiftType, User


class TestListGroups:
    """Tests for /admin/groups."""

    def test_list_groups(self, logged_in_client, test_group):
        """Test rendering the group list."""
        response = logged_in_client.get("/admin/groups")
        assert response.status_code == 200
        assert b"Test Group" in response.data or b"Groupes" in response.data

    def test_list_groups_unauthenticated(self, client):
        """Test that the group list requires authentication."""
        response = client.get("/admin/groups", follow_redirects=True)
        assert b"Connexion" in response.data


class TestListUsers:
    """Tests for /admin/users."""

    def test_list_users(self, logged_in_client, test_user):
        """Test rendering the user list."""
        response = logged_in_client.get("/admin/users")
        assert response.status_code == 200
        assert b"Test User" in response.data or b"Utilisateurs" in response.data

    def test_list_users_unauthenticated(self, client):
        """Test that the user list requires authentication."""
        response = client.get("/admin/users", follow_redirects=True)
        assert b"Connexion" in response.data


class TestListShiftTypes:
    """Tests for /admin/shift-types."""

    def test_list_shift_types(self, logged_in_client, test_shift_type):
        """Test rendering the shift-type list."""
        response = logged_in_client.get("/admin/shift-types")
        assert response.status_code == 200
        assert b"morning" in response.data or b"Types de shifts" in response.data

    def test_list_shift_types_unauthenticated(self, client):
        """Test that the shift-type list requires authentication."""
        response = client.get("/admin/shift-types", follow_redirects=True)
        assert b"Connexion" in response.data


class TestAddGroup:
    """Tests for /admin/groups/add."""

    def test_add_group_get(self, logged_in_client):
        """Test rendering the add-group form."""
        response = logged_in_client.get("/admin/groups/add")
        assert response.status_code == 200

    def test_add_group_post_valid(self, logged_in_client):
        """Test adding a group with valid data."""
        initial_count = Group.query.count()
        response = logged_in_client.post(
            "/admin/groups/add",
            data={
                "name": "New Group",
                "is_part_of_schedule": "on",
                "is_part_of_oncall": "on",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Group.query.count() == initial_count + 1

        # Check that the group was created
        new_group = Group.query.filter_by(name="New Group").first()
        assert new_group is not None
        assert new_group.is_part_of_schedule is True
        assert new_group.is_part_of_oncall is True

    def test_add_group_post_empty_name(self, logged_in_client):
        """Test adding a group with an empty name."""
        response = logged_in_client.post(
            "/admin/groups/add",
            data={"name": "", "is_part_of_schedule": "on", "is_part_of_oncall": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoire" in response.data

    def test_add_group_post_duplicate_name(self, logged_in_client, test_group):
        """Test adding a group with an already-used name."""
        response = logged_in_client.post(
            "/admin/groups/add",
            data={
                "name": test_group.name,
                "is_part_of_schedule": "on",
                "is_part_of_oncall": "on",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"existe" in response.data or b"already" in response.data


class TestAddUser:
    """Tests for /admin/users/add."""

    def test_add_user_get(self, logged_in_client):
        """Test rendering the add-user form."""
        response = logged_in_client.get("/admin/users/add")
        assert response.status_code == 200

    def test_add_user_post_valid(self, logged_in_client, test_group):
        """Test adding a user with valid data."""
        initial_count = User.query.count()
        response = logged_in_client.post(
            "/admin/users/add",
            data={
                "name": "New User",
                "email": "newuser@test.com",
                "group_id": test_group.id,
                "password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert User.query.count() == initial_count + 1

        # Check that the user was created
        new_user = User.query.filter_by(email="newuser@test.com").first()
        assert new_user is not None
        assert new_user.name == "New User"
        assert new_user.group_id == test_group.id

    def test_add_user_post_empty_fields(self, logged_in_client):
        """Test adding a user with empty fields."""
        response = logged_in_client.post(
            "/admin/users/add",
            data={"name": "", "email": "", "group_id": "", "password": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoires" in response.data

    def test_add_user_post_duplicate_email(self, logged_in_client, test_user):
        """Test adding a user with an already-used email."""
        response = logged_in_client.post(
            "/admin/users/add",
            data={
                "name": "New User",
                "email": test_user.email,
                "group_id": test_user.group_id,
                "password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"existe" in response.data or b"already" in response.data


class TestAddShiftType:
    """Tests for /admin/shift-types/add."""

    def test_add_shift_type_get(self, logged_in_client):
        """Test rendering the add-shift-type form."""
        response = logged_in_client.get("/admin/shift-types/add")
        assert response.status_code == 200

    def test_add_shift_type_post_valid(self, logged_in_client):
        """Test adding a shift type with valid data."""
        initial_count = ShiftType.query.count()
        response = logged_in_client.post(
            "/admin/shift-types/add",
            data={
                "name": "night",
                "label": "Nuit",
                "start_hour": "22",
                "end_hour": "23",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert ShiftType.query.count() == initial_count + 1

        # Check that the shift type was created
        new_shift_type = ShiftType.query.filter_by(name="night").first()
        assert new_shift_type is not None
        assert new_shift_type.label == "Nuit"
        assert new_shift_type.start_hour == 22
        assert new_shift_type.end_hour == 23

    def test_add_shift_type_post_empty_fields(self, logged_in_client):
        """Test adding a shift type with empty fields."""
        response = logged_in_client.post(
            "/admin/shift-types/add",
            data={"name": "", "label": "", "start_hour": "", "end_hour": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoires" in response.data

    def test_add_shift_type_post_duplicate_name(
        self, logged_in_client, test_shift_type
    ):
        """Test adding a shift type with an already-used name."""
        response = logged_in_client.post(
            "/admin/shift-types/add",
            data={
                "name": test_shift_type.name,
                "label": "Test",
                "start_hour": "9",
                "end_hour": "17",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"existe" in response.data or b"already" in response.data


class TestAdminDashboard:
    """Tests for /admin."""

    def test_admin_dashboard(self, logged_in_client):
        """Test rendering the admin dashboard."""
        response = logged_in_client.get("/admin")
        assert response.status_code == 200

    def test_admin_dashboard_unauthenticated(self, client):
        """Test that the admin dashboard requires authentication."""
        response = client.get("/admin", follow_redirects=True)
        assert b"Connexion" in response.data
