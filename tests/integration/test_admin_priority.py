"""
Priority tests for admin.py - correctly using the conftest fixtures.
"""

from datetime import datetime, timedelta

from app import db
from app.models import Group, Shift, ShiftType, User


class TestEditGroup:
    """Tests for /admin/groups/edit/<group_id>."""

    def test_edit_group_get(self, logged_in_client, group_not_in_schedule):
        """Test rendering the group edit form."""
        response = logged_in_client.get(
            f"/admin/groups/edit/{group_not_in_schedule.id}"
        )
        assert response.status_code == 200

    def test_edit_group_post_update_name(self, logged_in_client, group_not_in_schedule):
        """Test renaming a group."""
        response = logged_in_client.post(
            f"/admin/groups/edit/{group_not_in_schedule.id}",
            data={
                "name": "Updated Group",
                "is_part_of_schedule": "on",
                "is_part_of_oncall": "on",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated_group = db.session.get(Group, group_not_in_schedule.id)
        assert updated_group.name == "Updated Group"

    def test_edit_group_post_empty_name(self, logged_in_client, group_not_in_schedule):
        """Test editing with an empty name."""
        response = logged_in_client.post(
            f"/admin/groups/edit/{group_not_in_schedule.id}",
            data={"name": "", "is_part_of_schedule": "on", "is_part_of_oncall": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoire" in response.data


class TestEditUser:
    """Tests for /admin/users/edit/<user_id>."""

    def test_edit_user_get(self, logged_in_client, test_user):
        """Test rendering the user edit form."""
        response = logged_in_client.get(f"/admin/users/edit/{test_user.id}")
        assert response.status_code == 200

    def test_edit_user_post_update(self, logged_in_client, test_user):
        """Test editing a user."""
        response = logged_in_client.post(
            f"/admin/users/edit/{test_user.id}",
            data={
                "name": "Updated User",
                "email": "updated@test.com",
                "group_id": test_user.group_id,
                "is_admin": "off",
                "password": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated_user = db.session.get(User, test_user.id)
        assert updated_user.name == "Updated User"
        assert updated_user.email == "updated@test.com"


class TestEditShiftType:
    """Tests for /admin/shift-types/edit/<shift_type_id>."""

    def test_edit_shift_type_get(self, logged_in_client, test_shift_type):
        """Test rendering the shift-type edit form."""
        response = logged_in_client.get(f"/admin/shift-types/edit/{test_shift_type.id}")
        assert response.status_code == 200

    def test_edit_shift_type_post_update(self, logged_in_client, test_shift_type):
        """Test editing a shift type."""
        response = logged_in_client.post(
            f"/admin/shift-types/edit/{test_shift_type.id}",
            data={
                "name": "morning",
                "label": "Updated Label",
                "start_hour": "8",
                "end_hour": "16",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated = db.session.get(ShiftType, test_shift_type.id)
        assert updated.label == "Updated Label"
        assert updated.start_hour == 8


class TestDeleteGroup:
    """Tests for /admin/groups/delete/<group_id>."""

    def test_delete_button_is_a_post_form_not_a_get_link(
        self, logged_in_client, group_not_in_schedule
    ):
        """Regression test: the delete button used to be a plain <a
        href="..."> - .js-confirm-delete's handler for non-<button>
        triggers does `window.location.href = href` (a GET navigation),
        but the delete route only accepts POST, so confirming the
        deletion 405'd instead of deleting anything. Rendered as a real
        <form method="POST"> + <button type="submit"> now, matching
        every other delete action in this app (shift types, service
        accounts, etc.)."""
        response = logged_in_client.get("/admin/groups")
        html = response.data.decode()
        delete_url = f"/admin/groups/delete/{group_not_in_schedule.id}"
        assert f'action="{delete_url}"' in html
        assert f'href="{delete_url}"' not in html

    def test_delete_group_without_users(self, logged_in_client, group_not_in_schedule):
        """Test deleting a group with no users."""
        initial_count = Group.query.count()
        response = logged_in_client.post(
            f"/admin/groups/delete/{group_not_in_schedule.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Group.query.count() == initial_count - 1

    def test_delete_group_with_users(self, logged_in_client, test_group, test_user):
        """Test that deleting a group with users is blocked."""
        response = logged_in_client.post(
            f"/admin/groups/delete/{test_group.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Impossible" in response.data
        assert db.session.get(Group, test_group.id) is not None


class TestDeleteUser:
    """Tests for /admin/users/delete/<user_id>."""

    def test_delete_button_is_a_post_form_not_a_get_link(
        self, logged_in_client, second_user
    ):
        """Same regression as TestDeleteGroup's equivalent test - the
        user-delete button had the identical <a href> bug."""
        response = logged_in_client.get("/admin/users")
        html = response.data.decode()
        delete_url = f"/admin/users/delete/{second_user.id}"
        assert f'action="{delete_url}"' in html
        assert f'href="{delete_url}"' not in html

    def test_delete_user_without_resources(self, logged_in_client, second_user):
        """Test deleting a user with no resources."""
        initial_count = User.query.count()
        response = logged_in_client.post(
            f"/admin/users/delete/{second_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert User.query.count() == initial_count - 1

    def test_delete_user_with_shifts(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test that deleting a user with shifts is blocked."""
        # Create a shift
        start_time = datetime.now() + timedelta(days=1)
        shift = Shift(
            user_id=test_user.id,
            shift_type_id=test_shift_type.id,
            start_time=start_time,
            end_time=start_time + timedelta(hours=8),
            date=start_time.date(),
        )
        db.session.add(shift)
        db.session.commit()

        response = logged_in_client.post(
            f"/admin/users/delete/{test_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Impossible" in response.data
        assert db.session.get(User, test_user.id) is not None


class TestDeleteShiftType:
    """Tests for /admin/shift-types/delete/<shift_type_id>."""

    def test_delete_shift_type_unused(self, logged_in_client, afternoon_shift_type):
        """Test deleting an unused shift type."""
        initial_count = ShiftType.query.count()
        response = logged_in_client.post(
            f"/admin/shift-types/delete/{afternoon_shift_type.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert ShiftType.query.count() == initial_count - 1

    def test_delete_shift_type_in_use(
        self, logged_in_client, test_shift_type, test_user
    ):
        """Test that deleting a shift type in use is blocked."""
        # Create a shift with this type
        start_time = datetime.now() + timedelta(days=1)
        shift = Shift(
            user_id=test_user.id,
            shift_type_id=test_shift_type.id,
            start_time=start_time,
            end_time=start_time + timedelta(hours=8),
            date=start_time.date(),
        )
        db.session.add(shift)
        db.session.commit()

        response = logged_in_client.post(
            f"/admin/shift-types/delete/{test_shift_type.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Impossible" in response.data
        assert db.session.get(ShiftType, test_shift_type.id) is not None


class TestAutomationRoutes:
    """Tests for the automation routes."""

    def test_automation_dashboard(self, logged_in_client):
        """Test rendering the automation dashboard."""
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200

    def test_automation_full(self, logged_in_client):
        """Test rendering the full-automation page."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200

    def test_automation_status_old_url_removed(self, logged_in_client):
        """Old standalone URL, never linked from anywhere - its one
        unique stat (next available on-call date) was folded into
        /admin/automation's own stats block instead (see
        test_admin_automation.py::TestAutomationStatusMergedIntoDashboard)."""
        response = logged_in_client.get("/admin/automation/status")
        assert response.status_code == 404

    def test_automation_refresh_shifts_old_url_removed(self, logged_in_client):
        """Old standalone URL, merged into /admin/automation/full as a
        "Rafraîchir les shifts" button next to Dry Run - dropped outright
        rather than kept as a redirect (see
        test_admin_automation.py::TestRefreshShiftsOldUrlRemoved)."""
        response = logged_in_client.get("/admin/automation/refresh-shifts")
        assert response.status_code == 404
