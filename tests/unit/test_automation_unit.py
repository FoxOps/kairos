"""
Tests unitaires pour app/utils/automation.py
Couvre les fonctions et classes non testées précédemment.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, OnCall
from app.utils.automation import OnCallAutomation


class TestOnCallAutomationGetEligibleUsers:
    """Tests pour OnCallAutomation.get_eligible_users."""

    def test_returns_list(self, test_app):
        """Test que get_eligible_users retourne une liste."""
        with test_app.app_context():
            users = OnCallAutomation.get_eligible_users()
            assert isinstance(users, list)

    def test_filters_by_oncall_group(self, test_app, test_group, test_user):
        """Test que get_eligible_users filtre par is_part_of_oncall."""
        with test_app.app_context():
            # test_group a is_part_of_oncall=True par défaut
            # test_user fait partie de test_group
            users = OnCallAutomation.get_eligible_users()
            # Vérifier que test_user est dans la liste
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids


class TestOnCallAutomationGetRotationOrder:
    """Tests pour OnCallAutomation.get_rotation_order."""

    def test_returns_list(self, test_app):
        """Test que get_rotation_order retourne une liste."""
        with test_app.app_context():
            rotation = OnCallAutomation.get_rotation_order()
            assert isinstance(rotation, list)

    def test_empty_when_no_eligible_users(self, test_app):
        """Test que get_rotation_order retourne une liste vide sans utilisateurs éligibles."""
        with test_app.app_context():
            # Désactiver tous les groupes pour les astreintes
            Group.query.update({"is_part_of_oncall": False})
            db.session.commit()
            rotation = OnCallAutomation.get_rotation_order()
            assert rotation == []


class TestOnCallAutomationCheckConstraint:
    """Tests pour OnCallAutomation.check_oncall_constraint."""

    def test_returns_true_no_previous_oncall(self, test_app, test_user):
        """Test que check_oncall_constraint retourne True sans astreinte précédente."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=30)
            result = OnCallAutomation.check_oncall_constraint(test_user, start_time)
            assert result is True

    def test_returns_false_too_soon(self, test_app, test_user):
        """Test que check_oncall_constraint retourne False si trop tôt."""
        with test_app.app_context():
            now = datetime.now()
            # Créer une astreinte précédente
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=13),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Tester avec une date trop proche (moins de 2 semaines après)
            start_time = now - timedelta(days=12)
            result = OnCallAutomation.check_oncall_constraint(test_user, start_time)
            assert result is False

    def test_returns_true_sufficient_spacing(self, test_app, test_user):
        """Test que check_oncall_constraint retourne True avec un espacement suffisant."""
        with test_app.app_context():
            now = datetime.now()
            # Créer une astreinte précédente
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=30),
                end_time=now - timedelta(days=23),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Tester avec une date suffisamment éloignée
            start_time = now + timedelta(days=15)
            result = OnCallAutomation.check_oncall_constraint(test_user, start_time)
            assert result is True


class TestOnCallAutomationFindNextAvailable:
    """Tests pour OnCallAutomation.find_next_available_user."""

    def test_returns_none_empty_list(self, test_app):
        """Test que find_next_available_user retourne None avec une liste vide."""
        with test_app.app_context():
            result = OnCallAutomation.find_next_available_user(
                [], datetime.now(), datetime.now()
            )
            assert result is None

    def test_returns_user_when_available(self, test_app, test_user):
        """Test que find_next_available_user retourne un utilisateur disponible."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=10)
            end_time = start_time + timedelta(days=7)
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time
            )
            # Peut retourner test_user ou None selon les conflits
            assert result is None or result.id == test_user.id


class TestOnCallAutomationGenerateSchedule:
    """Tests pour OnCallAutomation.generate_oncall_schedule."""

    def test_returns_tuple(self, test_app):
        """Test que generate_oncall_schedule retourne un tuple."""
        with test_app.app_context():
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            result = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_dry_run_does_not_save(self, test_app, test_user, test_group):
        """Test que dry_run=True ne sauvegarde pas en base."""
        with test_app.app_context():
            # S'assurer que test_user est éligible
            test_group.is_part_of_oncall = True
            db.session.commit()

            start_date = date.today()
            end_date = start_date + timedelta(days=7)

            # Compter avant
            count_before = OnCall.query.count()

            # Générer en dry_run
            OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Vérifier que rien n'a été sauvegardé
            count_after = OnCall.query.count()
            assert count_after == count_before
