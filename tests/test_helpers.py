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
    _has_overlapping_oncall,
    _get_overlapping_leave,
    _get_overlapping_shift,
    _get_overlapping_oncall,
)
from app.models import Shift, OnCall, Leave, Group, User, ShiftType
from app import db


class TestHelperFunctions:
    """Tests pour les fonctions helpers internes."""

    def \1(self, test_app, test_user, test_shift_type):
        """Test qu'un utilisateur a un shift à une date donnée."""
        with test_app.app_context():
            # Créer un shift pour l'utilisateur
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            result = is_user_on_shift(test_user.id, shift_date)
            assert result is True

    def \1(self, test_app, test_user):
        """Test qu'un utilisateur n'a pas de shift à une date donnée."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            result = is_user_on_shift(test_user.id, shift_date)
            assert result is False

    def \1(self, test_app, test_user):
        """Test qu'un utilisateur est en congé à une date donnée."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Vérifier au milieu du congé
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 12).date())
            assert result is True

    def \1(self, test_app, test_user):
        """Test qu'un utilisateur n'est pas en congé à une date donnée."""
        with test_app.app_context():
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 1).date())
            assert result is False

    def \1(self, test_app, test_user):
        """Test qu'un utilisateur a une astreinte chevauchante."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier le chevauchement
            new_start = datetime(2023, 12, 2, 10, 0)
            new_end = datetime(2023, 12, 5, 10, 0)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is True

    def \1(self, test_app, test_user):
        """Test qu'un utilisateur n'a pas d'astreinte chevauchante."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier sans chevauchement
            new_start = datetime(2023, 12, 15, 21, 0)
            new_end = new_start + timedelta(days=7, hours=-14)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is False

    def \1(self, test_app, test_user):
        """Test la récupération d'un congé chevauchant."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Chercher un congé chevauchant
            result = _get_overlapping_leave(
                test_user.id,
                datetime(2023, 12, 12).date(),
                datetime(2023, 12, 14).date(),
            )
            assert result is not None
            assert result.id == leave.id

    def \1(self, test_app, test_user):
        """Test qu'aucun congé chevauchant n'est trouvé."""
        with test_app.app_context():
            result = _get_overlapping_leave(
                test_user.id, datetime(2023, 12, 1).date(), datetime(2023, 12, 5).date()
            )
            assert result is None


class TestCanAddShift:
    """Tests pour can_add_shift."""

    def \1(self, test_app, test_user):
        """Test qu'un shift peut être ajouté sur une date valide."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Lundi
            can_add, message = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add is True
            assert message == ""

    def \1(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté un samedi."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 2).date()  # Samedi
            can_add, message = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add is False
            assert (
                "les shifts ne peuvent être ajoutés que du lundi au vendredi" in message
            )

    def \1(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté un dimanche."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 3).date()  # Dimanche
            can_add, message = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add is False
            assert (
                "les shifts ne peuvent être ajoutés que du lundi au vendredi" in message
            )

    def \1(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur est en congé."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            shift_date = leave.start_date  # Date de début du congé
            can_add, message = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add is False
            assert "l'utilisateur est en congé" in message

    def test_can_add_shift_user_already_has_shift(
        self, app, test_user, test_shift_type
    ):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur en a déjà un."""
        with test_app.app_context():
            # Créer un shift existant
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            shift_date = shift.date
            can_add, message = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add is False
            assert "l'utilisateur a déjà un shift" in message

    def \1(self, test_app, test_user, second_user):
        """Test que plusieurs utilisateurs peuvent avoir des shifts le même jour."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Lundi

            # Ajouter un shift pour le premier utilisateur
            can_add1, _ = can_add_shift(test_user.id, shift_date, "morning")
            assert can_add1 is True

            # Ajouter un shift pour le deuxième utilisateur le même jour
            can_add2, _ = can_add_shift(second_user.id, shift_date, "morning")
            assert can_add2 is True


class TestCanAddOnCall:
    """Tests pour can_add_oncall."""

    def \1(self, test_app, test_user):
        """Test qu'une astreinte peut être ajoutée un vendredi à 21h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is True
            assert message == ""

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée un samedi."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 2, 21, 0)  # Samedi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi à 21h" in message

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée un lundi."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 4, 21, 0)  # Lundi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi à 21h" in message

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée à 20h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 20, 0)  # Vendredi 20h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi à 21h" in message

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée à 22h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 22, 0)  # Vendredi 22h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is False
            assert "L'astreinte doit commencer un vendredi à 21h" in message

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée si l'utilisateur est en congé."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Créer une astreinte qui chevauche le congé
            start_time = datetime(2023, 12, 8, 21, 0)  # Vendredi avant le congé
            end_time = start_time + timedelta(days=7, hours=-14)  # Chevauche le congé
            can_add, message = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add is False
            assert "l'utilisateur est en congé" in message

    def \1(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée si elle chevauche une autre."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Essayer d'ajouter une astreinte qui chevauche
            new_start_time = datetime(2023, 12, 1, 21, 0)  # Même date
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            can_add, message = can_add_oncall(
                test_user.id, new_start_time, new_end_time
            )
            assert can_add is False
            assert "l'utilisateur a déjà une astreinte sur cette période" in message

    def test_can_add_oncall_different_users_same_period(
        self, app, test_user, second_user
    ):
        """Test que différents utilisateurs peuvent avoir des astreintes à la même période."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            # Ajouter une astreinte pour le premier utilisateur
            can_add1, _ = can_add_oncall(test_user.id, start_time, end_time)
            assert can_add1 is True

            # Ajouter une astreinte pour le deuxième utilisateur à la même période
            can_add2, _ = can_add_oncall(second_user.id, start_time, end_time)
            assert can_add2 is True


class TestCanAddLeave:
    """Tests pour can_add_leave."""

    def \1(self, test_app, test_user):
        """Test qu'un congé peut être ajouté sur une période valide."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()
            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            assert can_add is True
            assert message == ""

    def \1(self, test_app, test_user):
        """Test qu'un congé ne peut pas être ajouté si la date de fin est avant la date de début."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 25).date()
            end_date = datetime(
                2023, 12, 20
            ).date()  # Date de fin avant la date de début
            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            assert can_add is False
            assert "La date de début doit être antérieure à la date de fin" in message

    def \1(self, test_app, test_user):
        """Test qu'un congé peut être ajouté pour un seul jour."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 20).date()
            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            assert can_add is True
            assert message == ""

    def \1(self, test_app, test_user):
        """Test qu'un congé ne peut pas être ajouté s'il chevauche un autre congé."""
        with test_app.app_context():
            # Créer un congé existant
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            assert can_add is False
            assert "un congé existe déjà sur cette période" in message

    def \1(self, test_app, test_user, test_shift_type):
        """Test qu'un congé peut être ajouté même si l'utilisateur a un shift (les congés sont prioritaires)."""
        with test_app.app_context():
            # Créer un shift
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            start_date = shift.date
            end_date = shift.date + timedelta(days=1)
            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            # Les congés sont prioritaires, donc cela doit être autorisé
            assert can_add is True
            assert message == ""

    def \1(self, test_app, test_user):
        """Test qu'un congé peut être ajouté même si l'utilisateur a une astreinte (les congés sont prioritaires)."""
        with test_app.app_context():
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            start_date = oncall.start_time.date()
            end_date = oncall.end_time.date()
            can_add, message = can_add_leave(test_user.id, start_date, end_date)
            # Les congés sont prioritaires, donc cela doit être autorisé
            assert can_add is True
            assert message == ""

    def test_can_add_leave_different_users_overlapping(
        self, app, test_user, second_user
    ):
        """Test que différents utilisateurs peuvent avoir des congés qui se chevauchent."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()

            # Ajouter un congé pour le premier utilisateur
            can_add1, _ = can_add_leave(test_user.id, start_date, end_date)
            assert can_add1 is True

            # Ajouter un congé pour le deuxième utilisateur à la même période
            can_add2, _ = can_add_leave(second_user.id, start_date, end_date)
            assert can_add2 is True
