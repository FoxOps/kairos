"""
Test pour vérifier que la rotation des shifts fonctionne correctement.
Ce test vérifie que le premier jour d'astreinte (lundi) utilise 09h-17h et non 13h-21h.
"""

from datetime import date, datetime, timedelta

import pytest

from app import create_app, db
from app.models import Group, OnCall, User
from app.utils.automation import AdvancedShiftAutomation


@pytest.fixture
def app_context():
    """Crée un contexte d'application pour les tests."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_shift_rotation_first_day_of_oncall(app_context):
    """Test que le premier jour d'astreinte (lundi) utilise 09h-17h et non 13h-21h."""
    with app_context.app_context():
        # Créer un groupe éligible pour les shifts et astreintes
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Créer un utilisateur
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Créer une astreinte pour l'utilisateur (du vendredi 21h au vendredi suivant 07h)
        friday = date(2024, 6, 21)  # Vendredi
        start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)  # Vendredi suivant 07h

        oncall = OnCall(user_id=user.id, start_time=start_time, end_time=end_time)
        db.session.add(oncall)
        db.session.commit()

        # Tester le lundi (premier jour ouvré de l'astreinte)
        monday = date(2024, 6, 24)  # Lundi
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"Le lundi (premier jour d'astreinte) devrait être 09h-17h, mais obtenu {shift}"

        # Tester le mardi (2ème jour)
        tuesday = date(2024, 6, 25)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, tuesday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Le mardi (2ème jour d'astreinte) devrait être 13h-21h, mais obtenu {shift}"

        # Tester le mercredi (3ème jour)
        wednesday = date(2024, 6, 26)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, wednesday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Le mercredi (3ème jour d'astreinte) devrait être 13h-21h, mais obtenu {shift}"

        # Tester le jeudi (4ème jour)
        thursday = date(2024, 6, 27)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, thursday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_13_21
        ), f"Le jeudi (4ème jour d'astreinte) devrait être 13h-21h, mais obtenu {shift}"

        # Tester le vendredi (dernier jour de l'astreinte)
        friday = date(2024, 6, 28)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, friday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"Le vendredi (dernier jour d'astreinte) devrait être 09h-17h, mais obtenu {shift}"


def test_shift_rotation_after_previous_oncall(app_context):
    """Test que la rotation fonctionne après une astreinte la semaine précédente."""
    with app_context.app_context():
        # Créer un groupe éligible
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Créer un utilisateur
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Créer une astreinte pour la semaine précédente (du vendredi 21h au vendredi suivant 07h)
        previous_friday = date(2024, 6, 14)  # Vendredi de la semaine précédente
        start_time = datetime.combine(previous_friday, datetime.min.time()).replace(
            hour=21
        )
        end_time = start_time + timedelta(days=7, hours=-14)

        previous_oncall = OnCall(
            user_id=user.id, start_time=start_time, end_time=end_time
        )
        db.session.add(previous_oncall)
        db.session.commit()

        # Tester le lundi de la semaine suivante (après l'astreinte)
        next_monday = date(2024, 6, 24)  # Lundi de la semaine suivante
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, next_monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_07_15
        ), f"Le lundi après une astreinte devrait être 07h-15h (rotation), mais obtenu {shift}"


def test_shift_default_for_non_oncall_user(app_context):
    """Test que les utilisateurs non d'astreinte utilisent le créneau par défaut (09h-17h)."""
    with app_context.app_context():
        # Créer un groupe éligible
        group = Group(
            name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        # Créer un utilisateur
        user = User(name="Test User", email="test@example.com", group_id=group.id)
        db.session.add(user)
        db.session.commit()

        # Ne pas créer d'astreinte pour cet utilisateur

        # Tester un lundi quelconque
        monday = date(2024, 6, 24)
        shift = AdvancedShiftAutomation.determine_shift_for_user(user, monday)
        assert (
            shift == AdvancedShiftAutomation.SHIFT_09_17
        ), f"Un utilisateur non d'astreinte devrait être 09h-17h, mais obtenu {shift}"
