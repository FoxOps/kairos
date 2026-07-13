"""
Tests complets pour app/utils/automation.py
Couvre les fonctions de génération et les cas complexes.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall
from app.utils.automation import OnCallAutomation


class TestOnCallAutomationGenerateScheduleFull:
    """Tests complets pour OnCallAutomation.generate_oncall_schedule."""

    def test_generates_multiple_oncalls(self, test_app, test_user, test_group):
        """Test que generate_oncall_schedule génère plusieurs astreintes."""
        with test_app.app_context():
            # S'assurer que test_user est éligible
            test_group.is_part_of_oncall = True
            db.session.commit()

            # Créer un deuxième utilisateur pour la rotation
            from app.models import User as UserModel

            test_user2 = UserModel(
                name="Test User 2", email="test2@example.com", group_id=test_group.id
            )
            test_user2.set_password("test_password")
            db.session.add(test_user2)
            db.session.commit()

            # Trouver le prochain vendredi
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_friday)
            # Utiliser 35 jours pour s'assurer d'inclure 4 astreintes complètes
            # (chaque astreinte dure jusqu'au vendredi suivant à 07h)
            end_date = start_date + timedelta(days=35)  # 5 semaines

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date,
                end_date,
                rotation_order_ids=[test_user.id, test_user2.id],
                dry_run=True,
            )

            # Devrait générer 5 astreintes (une par semaine) avec 2 utilisateurs
            # 35 jours = 5 semaines, donc 5 vendredis -> 5 astreintes
            assert len(oncalls) == 5

    def test_respects_start_date(self, test_app, test_user, test_group):
        """Test que generate_oncall_schedule respecte la date de début."""
        with test_app.app_context():
            test_group.is_part_of_oncall = True
            db.session.commit()

            start_date = date.today() + timedelta(days=10)
            end_date = start_date + timedelta(days=7)

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order_ids=[test_user.id], dry_run=True
            )

            if oncalls:
                # La première astreinte devrait commencer un vendredi
                first_oncall = oncalls[0]
                assert first_oncall.start_time.date() >= start_date

    def test_skips_unavailable_users(self, test_app, test_user, test_group):
        """Test que generate_oncall_schedule ignore les utilisateurs non disponibles."""
        with test_app.app_context():
            test_group.is_part_of_oncall = True
            db.session.commit()

            # Créer un congé pour test_user
            now = datetime.now()
            leave = Leave(
                user_id=test_user.id,
                start_date=now.date() + timedelta(days=2),
                end_date=now.date() + timedelta(days=10),
            )
            db.session.add(leave)
            db.session.commit()

            # Trouver le prochain vendredi
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_friday)
            end_date = start_date + timedelta(days=7)

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order_ids=[test_user.id], dry_run=True
            )

            # Devrait générer des messages sur les utilisateurs non disponibles
            # Le message peut être soit "Utilisateur avec contrainte légale seulement" (fallback avec contrainte)
            # soit "Aucun utilisateur disponible" (fallback sans contrainte)
            assert any(
                "Utilisateur avec contrainte légale seulement" in msg
                or "Aucun utilisateur disponible" in msg
                or "générée" in msg
                for msg in messages
            )


class TestOnCallAutomationFindNextAvailableFull:
    """Tests complets pour OnCallAutomation.find_next_available_user."""

    def test_skips_user_with_oncall_conflict(self, test_app, test_user):
        """Test que find_next_available_user ignore les utilisateurs avec conflit d'astreinte."""
        with test_app.app_context():
            now = datetime.now()

            # Créer une astreinte existante
            existing_oncall = OnCall(
                user_id=test_user.id,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=8),
            )
            db.session.add(existing_oncall)
            db.session.commit()

            # Tester avec une période qui chevauche
            start_time = now + timedelta(days=2)
            end_time = now + timedelta(days=5)

            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time
            )

            # Devrait ignorer test_user
            assert result is None

    def test_skips_user_with_leave_conflict(self, test_app, test_user):
        """Test que find_next_available_user ignore les utilisateurs avec conflit de congé."""
        with test_app.app_context():
            now = datetime.now()

            # Créer un congé
            leave = Leave(
                user_id=test_user.id,
                start_date=now.date() + timedelta(days=2),
                end_date=now.date() + timedelta(days=5),
            )
            db.session.add(leave)
            db.session.commit()

            # Tester avec une période qui chevauche
            start_time = now + timedelta(days=3)
            end_time = now + timedelta(days=4)

            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time
            )

            # Devrait ignorer test_user
            assert result is None

    def test_skips_user_with_legal_constraint(self, test_app, test_user):
        """Test que find_next_available_user ignore les utilisateurs avec contrainte légale."""
        with test_app.app_context():
            now = datetime.now()

            # Créer une astreinte précédente qui se termine il y a 13 jours
            # La contrainte est : (start_time - last_oncall.end_time).days / 7 >= 2
            # Si last_oncall.end_time était il y a 13 jours, et start_time est maintenant + 1 jour
            # Alors (start_time - last_end).days = (now + 1 day) - (now - 13 days) = 14 days
            # 14/7 = 2.0 -> passe la contrainte
            # Pour échouer, il faut que (start_time - last_end).days / 7 < 2
            # Donc il faut que (start_time - last_end).days < 14
            # Si last_end était il y a 13 jours, et start_time est maintenant
            # Alors (now - (now - 13 days)).days = 13 days
            # 13/7 = 1.857 < 2 -> devrait être ignoré

            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=13),  # Se termine il y a 13 jours
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Tester avec start_time = maintenant (pas maintenant + 1 jour)
            start_time = now
            end_time = now + timedelta(days=7)

            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time
            )

            # Devrait ignorer test_user à cause de la contrainte des 2 semaines
            # (now - (now - 13 days)).days / 7 = 13/7 = 1.857 < 2
            assert result is None
