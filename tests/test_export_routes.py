"""
Tests pour les routes d'export ICS.
"""

import pytest
from datetime import datetime, timedelta
from app.models import Shift, OnCall, Leave, User, Group, ShiftType
from app import db


class TestExportRoutes:
    """Tests pour les routes d'export."""

    def test_export_shifts_route(self, logged_in_client, test_user, test_shift_type, app):
        """Test l'export des shifts."""
        with app.app_context():
            # Créer un shift pour l'utilisateur
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(hour=7)
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

        response = logged_in_client.get("/export/shifts")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        assert "BEGIN:VCALENDAR" in response.data.decode("utf-8")
        assert "BEGIN:VEVENT" in response.data.decode("utf-8")
        assert "Shift" in response.data.decode("utf-8")

    def test_export_shifts_scope_all(self, logged_in_admin_client, test_user, test_shift_type, app):
        """Test l'export de tous les shifts (scope=all)."""
        with app.app_context():
            # Créer un shift
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(hour=7)
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

        response = logged_in_admin_client.get("/export/shifts?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "shifts_all.ics" in response.headers["Content-Disposition"]

    def test_export_shifts_scope_my(self, logged_in_client, test_user, test_shift_type, app):
        """Test l'export des shifts de l'utilisateur connecté (scope=my)."""
        with app.app_context():
            # Créer un shift pour l'utilisateur connecté
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(hour=7)
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

        response = logged_in_client.get("/export/shifts?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "shifts_my.ics" in response.headers["Content-Disposition"]

    def test_export_oncall_route(self, logged_in_client, test_user, app):
        """Test l'export des astreintes."""
        with app.app_context():
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_client.get("/export/oncall")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Astreinte" in content

    def test_export_oncall_scope_all(self, logged_in_admin_client, test_user, app):
        """Test l'export de toutes les astreintes (scope=all)."""
        with app.app_context():
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_admin_client.get("/export/oncall?scope=all")
        assert response.status_code == 200
        assert "oncall_all.ics" in response.headers["Content-Disposition"]

    def test_export_oncall_scope_my(self, logged_in_client, test_user, app):
        """Test l'export des astreintes de l'utilisateur connecté (scope=my)."""
        with app.app_context():
            # Créer une astreinte pour l'utilisateur connecté
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_client.get("/export/oncall?scope=my")
        assert response.status_code == 200
        assert "oncall_my.ics" in response.headers["Content-Disposition"]

    def test_export_leaves_route(self, logged_in_client, test_user, app):
        """Test l'export des congés."""
        with app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
            db.session.add(leave)
            db.session.commit()

        response = logged_in_client.get("/export/leaves")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Conge" in content or "Cong" in content

    def test_export_leaves_scope_all(self, logged_in_admin_client, test_user, app):
        """Test l'export de tous les congés (scope=all)."""
        with app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
            db.session.add(leave)
            db.session.commit()

        response = logged_in_admin_client.get("/export/leaves?scope=all")
        assert response.status_code == 200
        assert "leaves_all.ics" in response.headers["Content-Disposition"]

    def test_export_leaves_scope_my(self, logged_in_client, test_user, app):
        """Test l'export des congés de l'utilisateur connecté (scope=my)."""
        with app.app_context():
            # Créer un congé pour l'utilisateur connecté
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
            db.session.add(leave)
            db.session.commit()

        response = logged_in_client.get("/export/leaves?scope=my")
        assert response.status_code == 200
        assert "leaves_my.ics" in response.headers["Content-Disposition"]

    def test_export_shifts_unauthorized(self, client):
        """Test que l'export des shifts nécessite une authentification."""
        response = client.get("/export/shifts", follow_redirects=True)
        assert response.status_code == 200
        # Doit être redirigé vers la page de login
        assert b"Login" in response.data or b"email" in response.data

    def test_export_oncall_unauthorized(self, client):
        """Test que l'export des astreintes nécessite une authentification."""
        response = client.get("/export/oncall", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data or b"email" in response.data

    def test_export_leaves_unauthorized(self, client):
        """Test que l'export des congés nécessite une authentification."""
        response = client.get("/export/leaves", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data or b"email" in response.data

    def test_export_shifts_empty(self, logged_in_client):
        """Test l'export des shifts lorsque l'utilisateur n'en a pas."""
        response = logged_in_client.get("/export/shifts?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        # Pas d'événements
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_oncall_empty(self, logged_in_client):
        """Test l'export des astreintes lorsque l'utilisateur n'en a pas."""
        response = logged_in_client.get("/export/oncall?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_leaves_empty(self, logged_in_client):
        """Test l'export des congés lorsque l'utilisateur n'en a pas."""
        response = logged_in_client.get("/export/leaves?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_shifts_invalid_scope(self, logged_in_client):
        """Test l'export avec un scope invalide (par défaut, scope=all)."""
        response = logged_in_client.get("/export/shifts?scope=invalid")
        assert response.status_code == 200
        # Doit utiliser le scope par défaut (all)
        assert "BEGIN:VCALENDAR" in response.data.decode("utf-8")

    def test_export_content_disposition_header(self, logged_in_client, test_user, test_shift_type, app):
        """Test que le header Content-Disposition est correct."""
        with app.app_context():
            # Créer un shift
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(hour=7)
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

        response = logged_in_client.get("/export/shifts?scope=my")
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert "filename=" in response.headers["Content-Disposition"]


class TestExportRoutesAdminScope:
    """Tests pour vérifier que les admins peuvent exporter tous les données."""

    def test_admin_export_all_shifts(self, logged_in_admin_client, test_user, second_user, test_shift_type, app):
        """Test qu'un admin peut exporter les shifts de tous les utilisateurs."""
        with app.app_context():
            # Créer des shifts pour deux utilisateurs différents
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(hour=7)
            end_time = start_time + timedelta(hours=8)
            
            shift1 = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            shift2 = Shift(
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time + timedelta(days=1),
                end_time=end_time + timedelta(days=1),
                date=shift_date + timedelta(days=1),
            )
            db.session.add(shift1)
            db.session.add(shift2)
            db.session.commit()

        response = logged_in_admin_client.get("/export/shifts?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        # Doit contenir les shifts des deux utilisateurs
        assert content.count("BEGIN:VEVENT") == 2

    def test_admin_export_all_oncalls(self, logged_in_admin_client, test_user, second_user, app):
        """Test qu'un admin peut exporter les astreintes de tous les utilisateurs."""
        with app.app_context():
            # Créer des astreintes pour deux utilisateurs différents
            start_time1 = datetime(2023, 12, 1, 21, 0)
            end_time1 = start_time1 + timedelta(days=7, hours=-14)
            oncall1 = OnCall(user_id=test_user.id, start_time=start_time1, end_time=end_time1)
            
            start_time2 = datetime(2023, 12, 8, 21, 0)
            end_time2 = start_time2 + timedelta(days=7, hours=-14)
            oncall2 = OnCall(user_id=second_user.id, start_time=start_time2, end_time=end_time2)
            
            db.session.add(oncall1)
            db.session.add(oncall2)
            db.session.commit()

        response = logged_in_admin_client.get("/export/oncall?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert content.count("BEGIN:VEVENT") == 2

    def test_admin_export_all_leaves(self, logged_in_admin_client, test_user, second_user, app):
        """Test qu'un admin peut exporter les congés de tous les utilisateurs."""
        with app.app_context():
            # Créer des congés pour deux utilisateurs différents
            leave1 = Leave(
                user_id=test_user.id,
                start_date=datetime(2023, 12, 10).date(),
                end_date=datetime(2023, 12, 15).date(),
            )
            leave2 = Leave(
                user_id=second_user.id,
                start_date=datetime(2023, 12, 20).date(),
                end_date=datetime(2023, 12, 25).date(),
            )
            db.session.add(leave1)
            db.session.add(leave2)
            db.session.commit()

        response = logged_in_admin_client.get("/export/leaves?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert content.count("BEGIN:VEVENT") == 2
