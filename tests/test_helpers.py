"""
Tests pour les fonctions helpers (validation des conflits).
"""
import pytest
from datetime import datetime, timedelta
from app.utils.helpers import (
    can_add_shift,
    can_add_oncall,
    can_add_leave,
)
from app.models import Shift, OnCall, Leave, Group, User
from app import db


@pytest.fixture
def setup_db(app):
    """Prépare la base de données pour un test."""
    with app.app_context():
        db.create_all()
        yield
        db.session.rollback()
        db.drop_all()


class TestCanAddShift:
    """Tests pour can_add_shift."""
    
    def test_can_add_shift_valid(self, app):
        """Test qu'un shift peut être ajouté sur une date valide."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_valid@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            shift_date = datetime(2023, 12, 1).date()  # Lundi
            can_add, message = can_add_shift(user.id, shift_date, 'morning')
            assert can_add is True
            assert message == ""
    
    def test_can_add_shift_weekend(self, app):
        """Test qu'un shift ne peut pas être ajouté un week-end."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_weekend@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            shift_date = datetime(2023, 12, 2).date()  # Samedi
            can_add, message = can_add_shift(user.id, shift_date, 'morning')
            assert can_add is False
            assert "les shifts ne peuvent etre ajoutes que du lundi au vendredi" in message or \
                   "les shifts ne peuvent être ajoutés que du lundi au vendredi" in message
    
    def test_can_add_shift_user_on_leave(self, app):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur est en congé."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=user.id,
                start_date=start_date,
                end_date=end_date,
                reason='Test Leave'
            )
            db.session.add(leave)
            db.session.commit()
            
            shift_date = leave.start_date  # Date de début du congé
            can_add, message = can_add_shift(user.id, shift_date, 'morning')
            assert can_add is False
            assert "l'utilisateur est en conge" in message or "l'utilisateur est en congé" in message
    
    def test_can_add_shift_user_already_has_shift(self, app):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur en a déjà un."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_shift@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer un shift existant
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=user.id,
                shift_type='morning',
                start_time=start_time,
                end_time=end_time,
                date=start_time.date()
            )
            db.session.add(shift)
            db.session.commit()
            
            shift_date = shift.date
            can_add, message = can_add_shift(user.id, shift_date, 'morning')
            assert can_add is False
            assert "l'utilisateur a deja un shift" in message or "l'utilisateur a déjà un shift" in message


class TestCanAddOnCall:
    """Tests pour can_add_oncall."""
    
    def test_can_add_oncall_valid(self, app):
        """Test qu'une astreinte peut être ajoutée un vendredi à 21h."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_oncall_valid@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(user.id, start_time, end_time)
            assert can_add is True
            assert message == ""
    
    def test_can_add_oncall_wrong_day(self, app):
        """Test qu'une astreinte ne peut pas être ajoutée un jour autre que vendredi."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_oncall_wrong_day@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            start_time = datetime(2023, 12, 2, 21, 0)  # Samedi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi a 21h" in message or \
                   "L'astreinte doit commencer un vendredi à 21h" in message
    
    def test_can_add_oncall_wrong_hour(self, app):
        """Test qu'une astreinte ne peut pas être ajoutée à une heure autre que 21h."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_oncall_wrong_hour@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            start_time = datetime(2023, 12, 1, 20, 0)  # Vendredi 20h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi a 21h" in message or \
                   "L'astreinte doit commencer un vendredi à 21h" in message
    
    def test_can_add_oncall_user_on_leave(self, app):
        """Test qu'une astreinte ne peut pas être ajoutée si l'utilisateur est en congé."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_oncall_leave@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=user.id,
                start_date=start_date,
                end_date=end_date,
                reason='Test Leave'
            )
            db.session.add(leave)
            db.session.commit()
            
            # Créer une astreinte qui chevauche le congé
            start_time = datetime(2023, 12, 8, 21, 0)  # Vendredi avant le congé
            end_time = start_time + timedelta(days=7, hours=-14)  # Chevauche le congé
            can_add, message = can_add_oncall(user.id, start_time, end_time)
            assert can_add is False
            assert "l'utilisateur est en conge" in message or "l'utilisateur est en congé" in message
    
    def test_can_add_oncall_overlapping(self, app):
        """Test qu'une astreinte ne peut pas être ajoutée si elle chevauche une autre."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_oncall_overlapping@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer une astreinte existante (du vendredi 1er décembre 21h au vendredi 8 décembre 7h)
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)  # Vendredi suivant 7h
            oncall = OnCall(
                user_id=user.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()
            
            # Créer une astreinte qui chevauche (du vendredi 1er décembre 22h au vendredi 8 décembre 8h)
            # Cela chevauche la première astreinte (21h-7h)
            new_start_time = datetime(2023, 12, 1, 22, 0)  # Vendredi 1er décembre 22h
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(user.id, new_start_time, new_end_time)
            # La vérification du vendredi à 21h échouera, mais on peut contourner cela en utilisant une heure valide
            # Utilisons plutôt le vendredi 8 décembre 21h (qui chevauche la première astreinte qui se termine à 7h le 8 décembre)
            new_start_time = datetime(2023, 12, 8, 21, 0)  # Vendredi 8 décembre 21h
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            # Mais cela ne chevauche pas non plus... Utilisons une astreinte qui commence avant la fin de la première
            new_start_time = datetime(2023, 12, 7, 21, 0)  # Jeudi 7 décembre 21h (non, ce n'est pas un vendredi)
            # Le 8 décembre 2023 est un vendredi, mais l'astreinte du 1er au 8 se termine à 7h le 8
            # Donc une astreinte du 8 décembre 21h ne chevauche pas
            # Utilisons une astreinte du 1er décembre 20h au 8 décembre 6h (chevauche 21h-7h)
            new_start_time = datetime(2023, 12, 1, 20, 0)  # Vendredi 1er décembre 20h
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            # Mais cela déclenchera la vérification du vendredi à 21h
            # Solution: Utiliser une astreinte qui commence un vendredi à 21h mais chevauche une autre
            # Créons une deuxième astreinte pour le même utilisateur qui commence le 1er décembre 21h
            # Cela déclenchera la vérification de chevauchement
            new_start_time = datetime(2023, 12, 1, 21, 0)  # Même date que la première
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(user.id, new_start_time, new_end_time)
            assert can_add is False
            assert "l'utilisateur a deja une astreinte sur cette periode" in message or \
                   "l'utilisateur a déjà une astreinte sur cette période" in message


class TestCanAddLeave:
    """Tests pour can_add_leave."""
    
    def test_can_add_leave_valid(self, app):
        """Test qu'un congé peut être ajouté sur une période valide."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave_valid@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()
            can_add, message = can_add_leave(user.id, start_date, end_date)
            assert can_add is True
            assert message == ""
    
    def test_can_add_leave_invalid_dates(self, app):
        """Test qu'un congé ne peut pas être ajouté si la date de fin est avant la date de début."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave_invalid@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            start_date = datetime(2023, 12, 25).date()
            end_date = datetime(2023, 12, 20).date()  # Date de fin avant la date de début
            can_add, message = can_add_leave(user.id, start_date, end_date)
            assert can_add is False
            assert "La date de debut doit etre anterieure a la date de fin" in message or \
                   "La date de début doit être antérieure à la date de fin" in message
    
    def test_can_add_leave_overlapping(self, app):
        """Test qu'un congé ne peut pas être ajouté s'il chevauche un autre congé."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave_overlapping@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer un congé existant
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=user.id,
                start_date=start_date,
                end_date=end_date,
                reason='Test Leave'
            )
            db.session.add(leave)
            db.session.commit()
            
            can_add, message = can_add_leave(user.id, start_date, end_date)
            assert can_add is False
            assert "un conge existe deja sur cette periode" in message or \
                   "un congé existe déjà sur cette période" in message
    
    def test_can_add_leave_user_has_shift(self, app):
        """Test qu'un congé ne peut pas être ajouté si l'utilisateur a un shift."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave_shift@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer un shift
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=user.id,
                shift_type='morning',
                start_time=start_time,
                end_time=end_time,
                date=start_time.date()
            )
            db.session.add(shift)
            db.session.commit()
            
            start_date = shift.date
            end_date = shift.date + timedelta(days=1)
            can_add, message = can_add_leave(user.id, start_date, end_date)
            assert can_add is False
            assert "l'utilisateur a un shift" in message
    
    def test_can_add_leave_user_has_oncall(self, app):
        """Test qu'un congé ne peut pas être ajouté si l'utilisateur a une astreinte."""
        with app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name='Test Group', is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name='Test User', email='test_leave_oncall@example.com', group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=user.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()
            
            start_date = oncall.start_time.date()
            end_date = oncall.end_time.date()
            can_add, message = can_add_leave(user.id, start_date, end_date)
            assert can_add is False
            assert "l'utilisateur a une astreinte sur cette periode" in message or \
                   "l'utilisateur a une astreinte sur cette période" in message
