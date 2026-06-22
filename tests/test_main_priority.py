"""
Tests prioritaires pour main.py.
"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType


class TestDeleteAllShifts:
    """Tests pour /shift/delete-all."""

    def test_delete_all_shifts(self, logged_in_admin_client, test_shift):
        """Test la suppression de tous les shifts."""
        initial_count = Shift.query.count()
        assert initial_count > 0
        
        response = logged_in_admin_client.post("/shift/delete-all", follow_redirects=True)
        assert response.status_code == 200
        assert Shift.query.count() == 0


class TestDeleteAllShiftsForUser:
    """Tests pour /shift/delete-all-for-user/<user_id>."""

    def test_delete_all_shifts_for_user(self, logged_in_admin_client, test_user, test_shift_type):
        """Test la suppression de tous les shifts d'un utilisateur."""
        # Créer des shifts
        for i in range(3):
            start_time = datetime.now() + timedelta(days=i+1)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=start_time.date(),
            )
            db.session.add(shift)
        db.session.commit()
        
        response = logged_in_admin_client.post(
            f"/shift/delete-all-for-user/{test_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Shift.query.filter_by(user_id=test_user.id).count() == 0


class TestDeleteAllShiftsForDay:
    """Tests pour /shift/delete-day/<date_str>."""

    def test_delete_all_shifts_for_day(self, logged_in_admin_client, test_user, test_shift_type):
        """Test la suppression de tous les shifts pour un jour."""
        today = datetime.now().date()
        # Créer des shifts pour aujourd'hui
        for i in range(3):
            start_time = datetime.combine(today, datetime.min.time()).replace(hour=9 + i*2)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=today,
            )
            db.session.add(shift)
        db.session.commit()
        
        response = logged_in_admin_client.post(
            f"/shift/delete-day/{today.strftime('%Y-%m-%d')}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Shift.query.filter_by(date=today).count() == 0


class TestDeleteAllShiftsForWeek:
    """Tests pour /shift/delete-week/<date_str>."""

    def test_delete_all_shifts_for_week(self, logged_in_admin_client, test_user, test_shift_type):
        """Test la suppression de tous les shifts pour une semaine."""
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        
        # Créer des shifts pour la semaine
        for day in range(5):
            current_date = monday + timedelta(days=day)
            start_time = datetime.combine(current_date, datetime.min.time()).replace(hour=9)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=current_date,
            )
            db.session.add(shift)
        db.session.commit()
        
        response = logged_in_admin_client.post(
            f"/shift/delete-week/{monday.strftime('%Y-%m-%d')}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Shift.query.filter(
            Shift.date >= monday,
            Shift.date <= monday + timedelta(days=4)
        ).count() == 0


class TestDeleteAllOnCalls:
    """Tests pour /oncall/delete-all."""

    def test_delete_all_oncalls(self, logged_in_admin_client, test_oncall):
        """Test la suppression de toutes les astreintes."""
        initial_count = OnCall.query.count()
        assert initial_count > 0
        
        response = logged_in_admin_client.post("/oncall/delete-all", follow_redirects=True)
        assert response.status_code == 200
        assert OnCall.query.count() == 0


class TestDeleteAllOnCallsForUser:
    """Tests pour /oncall/delete-all-for-user/<user_id>."""

    def test_delete_all_oncalls_for_user(self, logged_in_admin_client, test_user):
        """Test la suppression de toutes les astreintes d'un utilisateur."""
        # Créer des astreintes
        for i in range(3):
            now = datetime.now()
            days_until_friday = (4 - now.weekday() + i*7) % 7
            start_time = datetime.combine(now.date(), datetime.min.time()).replace(
                hour=21
            ) + timedelta(days=days_until_friday + i*7)
            end_time = start_time + timedelta(days=7, hours=-14)
            
            oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            db.session.add(oncall)
        db.session.commit()
        
        response = logged_in_admin_client.post(
            f"/oncall/delete-all-for-user/{test_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert OnCall.query.filter_by(user_id=test_user.id).count() == 0


class TestCalendarFunctions:
    """Tests pour les fonctions utilitaires du calendrier."""

    def test_calendar_window(self, app):
        """Test _calendar_window."""
        from app.routes.main import _calendar_window, CALENDAR_WINDOW_DAYS
        
        start, end = _calendar_window()
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        
        now = datetime.now()
        expected_start = now - timedelta(days=CALENDAR_WINDOW_DAYS)
        expected_end = now + timedelta(days=CALENDAR_WINDOW_DAYS)
        
        assert abs((start - expected_start).total_seconds()) < 10
        assert abs((end - expected_end).total_seconds()) < 10

    def test_build_calendar_events_empty(self, app):
        """Test _build_calendar_events avec des listes vides."""
        from app.routes.main import _build_calendar_events
        
        events = _build_calendar_events([], [], [])
        assert events == []

    def test_build_calendar_events_with_data(self, app, test_user, test_shift_type):
        """Test _build_calendar_events avec des données."""
        from app.routes.main import _build_calendar_events
        
        start_time = datetime.now() + timedelta(days=1)
        shift = Shift(
            user_id=test_user.id,
            shift_type_id=test_shift_type.id,
            start_time=start_time,
            end_time=start_time + timedelta(hours=8),
            date=start_time.date(),
            user=test_user,
            shift_type=test_shift_type,
        )
        
        events = _build_calendar_events([shift], [], [])
        assert len(events) == 1
        assert events[0]["title"] == f"{test_user.name} - {test_shift_type.label}"
