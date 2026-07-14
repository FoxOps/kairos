"""
Tests pour le module d'automatisation des astreintes et des shifts.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, Leave, OnCall, User
from app.utils.automation import (
    AdvancedShiftAutomation,
    OnCallAutomation,
    get_automation_status,
)


class TestOnCallAutomation:
    """Tests pour l'automatisation des astreintes."""

    def test_get_eligible_users(self, test_app, test_group, test_user, second_user):
        """Test la récupération des utilisateurs éligibles pour les astreintes."""
        with test_app.app_context():
            # Créer un troisième utilisateur dans le même groupe
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            eligible_users = OnCallAutomation.get_eligible_users()
            # Tous les utilisateurs du groupe sont éligibles (is_part_of_oncall=True)
            assert len(eligible_users) == 3
            assert all(user.group.is_part_of_oncall for user in eligible_users)

    def test_get_rotation_order_default(
        self, test_app, test_group, test_user, second_user
    ):
        """Test l'ordre de rotation par défaut (alphabétique)."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Zebra User",  # Z pour être dernier alphabétiquement
                email="zebra@test.com",
                password_hash="zebra123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = OnCallAutomation.get_rotation_order()
            assert len(rotation_order) == 3
            # Vérifier que l'ordre est alphabétique
            # Note: Admin User commence par 'A', Second User par 'S', Zebra User par 'Z'
            names = [u.name for u in rotation_order]
            assert names == sorted(names)

    def test_get_rotation_order_custom(
        self, test_app, test_group, test_user, second_user
    ):
        """Test l'ordre de rotation personnalisé."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Ordre personnalisé : second_user, user3, test_user
            custom_order = [second_user.id, user3.id, test_user.id]
            rotation_order = OnCallAutomation.get_rotation_order(custom_order)

            assert len(rotation_order) == 3
            assert rotation_order[0].id == second_user.id
            assert rotation_order[1].id == user3.id
            assert rotation_order[2].id == test_user.id

    def test_find_next_available_user(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la recherche du prochain utilisateur disponible."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = [test_user, second_user, user3]

            # Créer une astreinte existante pour test_user
            start_time = datetime(2024, 1, 5, 21, 0)  # Vendredi 5 janvier 2024 à 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Trouver un utilisateur disponible pour la même période
            available_user = OnCallAutomation.find_next_available_user(
                rotation_order, start_time, end_time
            )

            # test_user n'est pas disponible, donc second_user devrait être retourné
            assert available_user is not None
            assert available_user.id == second_user.id

            # Nettoyer
            db.session.delete(oncall)
            db.session.commit()

    def test_generate_oncall_schedule_dry_run(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la génération des astreintes en mode dry run."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Vendredi
            end_date = date(2024, 2, 23)  # 8 semaines plus tard

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Devrait générer 7 ou 8 astreintes selon la date de fin exacte
            assert len(oncalls) >= 7
            assert len(messages) > 0

            # Vérifier que les astreintes sont bien espacées d'une semaine
            for i in range(1, len(oncalls)):
                assert oncalls[i].start_time == oncalls[i - 1].start_time + timedelta(
                    days=7
                )

    def test_generate_oncall_schedule_with_rotation(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la génération avec un ordre de rotation personnalisé."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Vendredi
            end_date = date(2024, 1, 19)  # 2 semaines plus tard

            # Ordre personnalisé : second_user, test_user, user3
            rotation_order = [second_user.id, test_user.id, user3.id]

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order, dry_run=True
            )

            # end_date inclusif : 3 vendredis (05/01, 12/01, 19/01).
            assert len(oncalls) == 3
            # La première astreinte devrait être pour second_user
            assert oncalls[0].user_id == second_user.id
            # La deuxième astreinte devrait être pour test_user
            assert oncalls[1].user_id == test_user.id


class TestFullScheduleGeneration:
    """Tests pour la génération complète du schedule."""

    def test_generate_full_schedule_dry_run(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        """Test la génération complète en mode dry run."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Vendredi
            end_date = date(2024, 1, 19)  # 2 semaines plus tard

            # AdvancedShiftAutomation.generate_full_schedule ne génère que des shifts
            # (jours ouvrés) ; les astreintes sont générées séparément par
            # OnCallAutomation.generate_oncall_schedule.
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(shifts) > 0
            assert len(messages) > 0

            oncalls, oncall_messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            # end_date inclusif : 3 vendredis (05/01, 12/01, 19/01).
            assert len(oncalls) == 3

    def test_get_automation_status(self, test_app, test_group, test_user, second_user):
        """Test la récupération de l'état de l'automatisation."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            status = get_automation_status()

            assert "oncall_count" in status
            assert "shift_count" in status
            assert "oncall_eligible_users" in status
            assert "shift_eligible_users" in status
            assert "next_available_oncall_date" in status

            # Vérifier les valeurs
            assert status["oncall_eligible_users"] == 3
            assert status["shift_eligible_users"] == 3


class TestEdgeCases:
    """Tests pour les cas particuliers."""

    def test_generate_oncall_no_eligible_users(self, test_app):
        """Test la génération d'astreintes sans utilisateurs éligibles."""
        with test_app.app_context():
            # Créer un groupe sans is_part_of_oncall
            group = Group(
                name="No OnCall", is_part_of_schedule=True, is_part_of_oncall=False
            )
            db.session.add(group)
            db.session.commit()

            start_date = date(2024, 1, 5)
            end_date = date(2024, 1, 19)

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(oncalls) == 0
            assert any("Aucun utilisateur éligible" in msg for msg in messages)

    def test_generate_oncall_with_leave_conflict(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la génération d'astreintes avec un conflit de congé."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Créer un congé pour test_user
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 5),
                end_date=date(2024, 1, 12),
            )
            db.session.add(leave)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Vendredi
            end_date = date(2024, 1, 19)  # 2 semaines plus tard

            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Devrait générer 3 astreintes (end_date inclusif), mais
            # test_user ne devrait pas être assigné
            assert len(oncalls) == 3
            assert all(oncall.user_id != test_user.id for oncall in oncalls)

            # Nettoyer
            db.session.delete(leave)
            db.session.commit()
