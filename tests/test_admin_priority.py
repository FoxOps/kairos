"""
Tests prioritaires pour admin.py - utilisant correctement les fixtures du conftest.
"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType


class TestEditGroup:
    """Tests pour /admin/groups/edit/<group_id>."""

    def test_edit_group_get(self, logged_in_client, group_not_in_schedule):
        """Test l'affichage du formulaire d'édition de groupe."""
        response = logged_in_client.get(f"/admin/groups/edit/{group_not_in_schedule.id}")
        assert response.status_code == 200

    def test_edit_group_post_update_name(self, logged_in_client, group_not_in_schedule):
        """Test la modification du nom d'un groupe."""
        response = logged_in_client.post(
            f"/admin/groups/edit/{group_not_in_schedule.id}",
            data={"name": "Updated Group", "is_part_of_schedule": "on", "is_part_of_oncall": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated_group = db.session.get(Group, group_not_in_schedule.id)
        assert updated_group.name == "Updated Group"

    def test_edit_group_post_empty_name(self, logged_in_client, group_not_in_schedule):
        """Test la modification avec un nom vide."""
        response = logged_in_client.post(
            f"/admin/groups/edit/{group_not_in_schedule.id}",
            data={"name": "", "is_part_of_schedule": "on", "is_part_of_oncall": "on"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"obligatoire" in response.data


class TestEditUser:
    """Tests pour /admin/users/edit/<user_id>."""

    def test_edit_user_get(self, logged_in_client, test_user):
        """Test l'affichage du formulaire d'édition d'utilisateur."""
        response = logged_in_client.get(f"/admin/users/edit/{test_user.id}")
        assert response.status_code == 200

    def test_edit_user_post_update(self, logged_in_client, test_user):
        """Test la modification d'un utilisateur."""
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
    """Tests pour /admin/shift-types/edit/<shift_type_id>."""

    def test_edit_shift_type_get(self, logged_in_client, test_shift_type):
        """Test l'affichage du formulaire d'édition de type de shift."""
        response = logged_in_client.get(f"/admin/shift-types/edit/{test_shift_type.id}")
        assert response.status_code == 200

    def test_edit_shift_type_post_update(self, logged_in_client, test_shift_type):
        """Test la modification d'un type de shift."""
        response = logged_in_client.post(
            f"/admin/shift-types/edit/{test_shift_type.id}",
            data={"name": "morning", "label": "Updated Label", "start_hour": "8", "end_hour": "16"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        updated = db.session.get(ShiftType, test_shift_type.id)
        assert updated.label == "Updated Label"
        assert updated.start_hour == 8


class TestDeleteGroup:
    """Tests pour /admin/groups/delete/<group_id>."""

    def test_delete_group_without_users(self, logged_in_client, group_not_in_schedule):
        """Test la suppression d'un groupe sans utilisateurs."""
        initial_count = Group.query.count()
        response = logged_in_client.post(
            f"/admin/groups/delete/{test_group.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Group.query.count() == initial_count - 1

    def test_delete_group_with_users(self, logged_in_client, test_group, test_user):
        """Test que la suppression d'un groupe avec des utilisateurs est bloquée."""
        response = logged_in_client.post(
            f"/admin/groups/delete/{test_group.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Impossible" in response.data
        assert db.session.get(Group, test_group.id) is not None


class TestDeleteUser:
    """Tests pour /admin/users/delete/<user_id>."""

    def test_delete_user_without_resources(self, logged_in_client, second_user):
        """Test la suppression d'un utilisateur sans ressources."""
        initial_count = User.query.count()
        response = logged_in_client.post(
            f"/admin/users/delete/{second_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert User.query.count() == initial_count - 1

    def test_delete_user_with_shifts(self, logged_in_client, test_user, test_shift_type):
        """Test que la suppression d'un utilisateur avec des shifts est bloquée."""
        # Créer un shift
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
    """Tests pour /admin/shift-types/delete/<shift_type_id>."""

    def test_delete_shift_type_unused(self, logged_in_client, afternoon_shift_type):
        """Test la suppression d'un type de shift non utilisé."""
        initial_count = ShiftType.query.count()
        response = logged_in_client.post(
            f"/admin/shift-types/delete/{afternoon_shift_type.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert ShiftType.query.count() == initial_count - 1

    def test_delete_shift_type_in_use(self, logged_in_client, test_shift_type, test_user):
        """Test que la suppression d'un type de shift utilisé est bloquée."""
        # Créer un shift avec ce type
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
    """Tests pour les routes d'automatisation."""

    def test_automation_dashboard(self, logged_in_client):
        """Test l'affichage du tableau de bord d'automatisation."""
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200

    def test_automation_shifts(self, logged_in_client):
        """Test l'affichage de la page d'automatisation des shifts."""
        response = logged_in_client.get("/admin/automation/shifts")
        assert response.status_code == 200

    def test_automation_full(self, logged_in_client):
        """Test l'affichage de la page d'automatisation complète."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200

    def test_automation_status(self, logged_in_client):
        """Test l'affichage de la page de statut d'automatisation."""
        response = logged_in_client.get("/admin/automation/status")
        assert response.status_code == 200

    def test_automation_refresh_shifts(self, logged_in_client):
        """Test l'affichage de la page de rafraîchissement des shifts."""
        response = logged_in_client.get("/admin/automation/refresh-shifts")
        assert response.status_code == 200
