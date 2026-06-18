"""
Tests pour les fonctions helpers (validation des conflits).
"""
import pytest
from datetime import datetime, timedelta
from app.utils.helpers import (
    can_add_shift,
    can_add_oncall,
    can_add_leave,
    is_user_on_shift,
    is_user_on_leave,
    _has_overlapping_oncall
)
from app.models import Shift, OnCall, Leave


class TestCanAddShift:
    """Tests pour can_add_shift."""
    
    def test_can_add_shift_valid(self, test_user):
        """Test qu'un shift peut être ajouté sur une date valide."""
        shift_date = datetime(2023, 12, 1).date()  # Lundi
        can_add, message = can_add_shift(test_user.id, shift_date, 'morning')
        assert can_add is True
        assert message == ""
    
    def test_can_add_shift_weekend(self, test_user):
        """Test qu'un shift ne peut pas être ajouté un week-end."""
        shift_date = datetime(2023, 12, 2).date()  # Samedi
        can_add, message = can_add_shift(test_user.id, shift_date, 'morning')
        assert can_add is False
        assert "les shifts ne peuvent être ajoutés que du lundi au vendredi" in message
    
    def test_can_add_shift_user_on_leave(self, test_user, test_leave):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur est en congé."""
        shift_date = test_leave.start_date  # Date de début du congé
        can_add, message = can_add_shift(test_user.id, shift_date, 'morning')
        assert can_add is False
        assert "l'utilisateur est en congé" in message
    
    def test_can_add_shift_user_already_has_shift(self, test_user, test_shift):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur en a déjà un."""
        shift_date = test_shift.date
        can_add, message = can_add_shift(test_user.id, shift_date, 'morning')
        assert can_add is False
        assert "l'utilisateur a déjà un shift" in message


class TestCanAddOnCall:
    """Tests pour can_add_oncall."""
    
    def test_can_add_oncall_valid(self, test_user):
        """Test qu'une astreinte peut être ajoutée un vendredi à 21h."""
        start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
        end_time = start_time + timedelta(days=7, hours=-14)
        can_add, message = can_add_oncall(test_user.id, start_time, end_time)
        assert can_add is True
        assert message == ""
    
    def test_can_add_oncall_wrong_day(self, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée un jour autre que vendredi."""
        start_time = datetime(2023, 12, 2, 21, 0)  # Samedi 21h
        end_time = start_time + timedelta(days=7, hours=-14)
        can_add, message = can_add_oncall(test_user.id, start_time, end_time)
        assert can_add is False
        assert "L'astreinte doit commencer un vendredi à 21h" in message
    
    def test_can_add_oncall_wrong_hour(self, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée à une heure autre que 21h."""
        start_time = datetime(2023, 12, 1, 20, 0)  # Vendredi 20h
        end_time = start_time + timedelta(days=7, hours=-14)
        can_add, message = can_add_oncall(test_user.id, start_time, end_time)
        assert can_add is False
        assert "L'astreinte doit commencer un vendredi à 21h" in message
    
    def test_can_add_oncall_user_on_leave(self, test_user, test_leave):
        """Test qu'une astreinte ne peut pas être ajoutée si l'utilisateur est en congé."""
        # Créer une astreinte qui chevauche le congé
        start_time = datetime(2023, 12, 8, 21, 0)  # Vendredi avant le congé
        end_time = start_time + timedelta(days=7, hours=-14)  # Chevauche le congé
        can_add, message = can_add_oncall(test_user.id, start_time, end_time)
        assert can_add is False
        assert "l'utilisateur est en congé" in message
    
    def test_can_add_oncall_overlapping(self, test_user, test_oncall):
        """Test qu'une astreinte ne peut pas être ajoutée si elle chevauche une autre."""
        # Créer une astreinte qui chevauche test_oncall
        start_time = test_oncall.start_time + timedelta(days=1)
        end_time = test_oncall.end_time + timedelta(days=1)
        can_add, message = can_add_oncall(test_user.id, start_time, end_time)
        assert can_add is False
        assert "l'utilisateur a déjà une astreinte sur cette période" in message


class TestCanAddLeave:
    """Tests pour can_add_leave."""
    
    def test_can_add_leave_valid(self, test_user):
        """Test qu'un congé peut être ajouté sur une période valide."""
        start_date = datetime(2023, 12, 20).date()
        end_date = datetime(2023, 12, 25).date()
        can_add, message = can_add_leave(test_user.id, start_date, end_date)
        assert can_add is True
        assert message == ""
    
    def test_can_add_leave_invalid_dates(self, test_user):
        """Test qu'un congé ne peut pas être ajouté si la date de fin est avant la date de début."""
        start_date = datetime(2023, 12, 25).date()
        end_date = datetime(2023, 12, 20).date()
        can_add, message = can_add_leave(test_user.id, start_date, end_date)
        assert can_add is False
        assert "La date de début doit être antérieure à la date de fin" in message
    
    def test_can_add_leave_overlapping(self, test_user, test_leave):
        """Test qu'un congé ne peut pas être ajouté s'il chevauche un autre congé."""
        start_date = test_leave.start_date
        end_date = test_leave.end_date
        can_add, message = can_add_leave(test_user.id, start_date, end_date)
        assert can_add is False
        assert "un congé existe déjà sur cette période" in message
    
    def test_can_add_leave_user_has_shift(self, test_user, test_shift):
        """Test qu'un congé ne peut pas être ajouté si l'utilisateur a un shift."""
        start_date = test_shift.date
        end_date = test_shift.date + timedelta(days=1)
        can_add, message = can_add_leave(test_user.id, start_date, end_date)
        assert can_add is False
        assert "l'utilisateur a un shift" in message
    
    def test_can_add_leave_user_has_oncall(self, test_user, test_oncall):
        """Test qu'un congé ne peut pas être ajouté si l'utilisateur a une astreinte."""
        start_date = test_oncall.start_time.date()
        end_date = test_oncall.end_time.date()
        can_add, message = can_add_leave(test_user.id, start_date, end_date)
        assert can_add is False
        assert "l'utilisateur a une astreinte sur cette période" in message
