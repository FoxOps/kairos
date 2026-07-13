"""
Tests pour le module d'automatisation avancée des shifts.
"""

from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from app import db
from app.models import Group, Leave, OnCall, Shift, ShiftType, User
from app.utils.automation import AdvancedShiftAutomation


class TestAdvancedShiftAutomationBasics:
    """Tests pour les méthodes de base de l'automatisation avancée."""

    def test_shift_constants(self, test_app):
        """Test que les constantes des créneaux sont correctes."""
        with test_app.app_context():
            assert AdvancedShiftAutomation.SHIFT_07_15 == (7, 15)
            assert AdvancedShiftAutomation.SHIFT_09_17 == (9, 17)
            assert AdvancedShiftAutomation.SHIFT_13_21 == (13, 21)

    def test_get_users_in_schedule_groups(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la récupération des utilisateurs dans les groupes schedule."""
        with test_app.app_context():
            # test_group a is_part_of_schedule=True par défaut
            users = AdvancedShiftAutomation.get_users_in_schedule_groups()

            # Doit contenir test_user et second_user
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids
            assert second_user.id in user_ids

    def test_get_users_in_schedule_groups_excludes_non_schedule(
        self, test_app, test_group, test_user, group_not_in_schedule
    ):
        """Test que les utilisateurs de groupes non-schedule sont exclus."""
        with test_app.app_context():
            # Créer un utilisateur dans un groupe non-schedule
            user_not_in_schedule = User(
                name="User Not In Schedule",
                email="notinschedule@test.com",
                password_hash=generate_password_hash("test-password"),
                is_admin=False,
                group_id=group_not_in_schedule.id,
            )
            db.session.add(user_not_in_schedule)
            db.session.commit()

            users = AdvancedShiftAutomation.get_users_in_schedule_groups()
            user_ids = [u.id for u in users]

            assert test_user.id in user_ids
            assert user_not_in_schedule.id not in user_ids

    def test_get_available_users_for_date(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la récupération des utilisateurs disponibles pour une date."""
        with test_app.app_context():
            # Sans congés, tous les utilisateurs doivent être disponibles
            test_date = date(2023, 12, 15)
            available_users = AdvancedShiftAutomation.get_available_users_for_date(
                test_date
            )

            user_ids = [u.id for u in available_users]
            assert test_user.id in user_ids
            assert second_user.id in user_ids

    def test_get_available_users_excludes_on_leave(
        self, test_app, test_group, test_user, second_user
    ):
        """Test que les utilisateurs en congé sont exclus."""
        with test_app.app_context():
            # Créer un congé pour test_user
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 10),
                end_date=date(2023, 12, 15),
            )
            db.session.add(leave)
            db.session.commit()

            # Vérifier pendant le congé
            test_date = date(2023, 12, 12)
            available_users = AdvancedShiftAutomation.get_available_users_for_date(
                test_date
            )

            user_ids = [u.id for u in available_users]
            assert test_user.id not in user_ids
            assert second_user.id in user_ids

    def test_get_oncall_user_for_date(self, test_app, test_user):
        """Test la récupération de l'utilisateur d'astreinte pour une date."""
        with test_app.app_context():
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier pendant l'astreinte
            test_date = date(2023, 12, 2)
            oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(test_date)

            assert oncall_user is not None
            assert oncall_user.id == test_user.id

    def test_get_oncall_user_for_date_no_oncall(self, test_app, test_user):
        """Test qu'aucun utilisateur n'est retourné s'il n'y a pas d'astreinte."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(test_date)

            assert oncall_user is None


class TestShiftTypeByHours:
    """Tests pour la création de types de shifts par heures."""

    def test_get_shift_type_by_hours_existing(self, test_app, test_shift_type):
        """Test la récupération d'un type de shift existant."""
        with test_app.app_context():
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(7, 15)

            assert shift_type is not None
            assert shift_type.start_hour == 7
            assert shift_type.end_hour == 15

    def test_get_shift_type_by_hours_new(self, test_app):
        """Test la création d'un nouveau type de shift."""
        with test_app.app_context():
            # S'assurer qu'aucun type 13-21 n'existe
            existing = ShiftType.query.filter_by(start_hour=13, end_hour=21).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()

            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(13, 21)

            assert shift_type is not None
            assert shift_type.start_hour == 13
            assert shift_type.end_hour == 21
            assert shift_type.name == "13-21"
            assert shift_type.label == "13h-21h"


class TestDetermineShiftForUser:
    """Tests pour la détermination du créneau de shift pour un utilisateur."""

    def test_determine_shift_rotation_after_oncall(
        self, test_app, test_group, test_user
    ):
        """Test la rotation : après une astreinte, l'utilisateur doit être sur 07h-15h."""
        with test_app.app_context():
            # Créer une astreinte pour la semaine précédente
            previous_friday = date(2023, 12, 1)  # vendredi
            start_time = datetime.combine(previous_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier la semaine suivante (lundi, après l'astreinte)
            test_date = date(2023, 12, 11)  # lundi de la semaine suivante
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_07_15

    def test_determine_shift_oncall_user_in_schedule(
        self, test_app, test_group, test_user
    ):
        """Test qu'un utilisateur d'astreinte dans un groupe schedule a le créneau 13h-21h."""
        with test_app.app_context():
            # Créer une astreinte pour cette semaine
            friday = date(2023, 12, 1)  # vendredi
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier pendant l'astreinte
            test_date = date(2023, 12, 2)  # samedi (mais dans la période d'astreinte)
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_13_21

    def test_determine_shift_default(self, test_app, test_group, test_user):
        """Test que le créneau par défaut est 09h-17h."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            shift_hours = AdvancedShiftAutomation.determine_shift_for_user(
                test_user, test_date
            )

            assert shift_hours == AdvancedShiftAutomation.SHIFT_09_17


class TestHandleTwoUsersCase:
    """Tests pour le cas spécial avec 2 utilisateurs disponibles."""

    def test_handle_two_users_case_oncall_gets_13_21(
        self, test_app, test_group, test_user, second_user
    ):
        """Test que l'utilisateur d'astreinte obtient 13h-21h."""
        with test_app.app_context():
            # Créer une astreinte pour test_user
            friday = date(2023, 12, 1)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Tester avec les deux utilisateurs disponibles
            test_date = date(2023, 12, 2)
            available_users = [test_user, second_user]
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            assert len(assignments) == 2
            assert assignments[test_user] == AdvancedShiftAutomation.SHIFT_13_21
            assert assignments[second_user] == AdvancedShiftAutomation.SHIFT_07_15

    def test_handle_two_users_case_no_oncall(
        self, test_app, test_group, test_user, second_user
    ):
        """Test le cas avec 2 utilisateurs mais sans astreinte."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            available_users = [test_user, second_user]
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            # Sans astreinte, selon la logique actuelle, les deux obtiennent 07h-15h
            # car la méthode vérifie si oncall_user existe et si user.id == oncall_user.id
            # Si oncall_user est None, alors user.id == oncall_user.id sera False
            # et donc assignments[user] = SHIFT_07_15
            assert len(assignments) == 2
            assert assignments[test_user] == AdvancedShiftAutomation.SHIFT_07_15
            assert assignments[second_user] == AdvancedShiftAutomation.SHIFT_07_15

    def test_handle_two_users_case_not_two_users(
        self, test_app, test_group, test_user, second_user
    ):
        """Test que la méthode retourne un dict vide si ce n'est pas exactement 2 utilisateurs."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            available_users = [
                test_user,
                second_user,
                test_user,
            ]  # 3 utilisateurs (test_user en double)
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, test_date
            )

            assert assignments == {}


class TestGenerateDailyShifts:
    """Tests pour la génération quotidienne des shifts."""

    def test_generate_daily_shifts_weekend(self, test_app):
        """Test qu'aucun shift n'est généré le week-end."""
        with test_app.app_context():
            saturday = date(2023, 12, 2)  # samedi
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                saturday, dry_run=True
            )

            assert len(shifts) == 0
            assert any("week-end" in msg.lower() for msg in messages)

    def test_generate_daily_shifts_no_available_users(self, test_app, test_group):
        """Test qu'aucun shift n'est généré s'il n'y a pas d'utilisateurs disponibles."""
        with test_app.app_context():
            # Créer un congé pour tous les utilisateurs
            users = User.query.all()
            for user in users:
                leave = Leave(
                    user_id=user.id,
                    start_date=date(2023, 12, 15),
                    end_date=date(2023, 12, 20),
                )
                db.session.add(leave)
            db.session.commit()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            assert len(shifts) == 0
            assert any("disponible" in msg.lower() for msg in messages)

    def test_generate_daily_shifts_with_two_users(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        """Test la génération avec exactement 2 utilisateurs disponibles."""
        with test_app.app_context():
            # S'assurer qu'il n'y a que ces deux utilisateurs dans le groupe schedule
            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Doit générer des shifts pour les deux utilisateurs
            assert len(shifts) == 2
            assert any(test_user.id == s.user_id for s in shifts)
            assert any(second_user.id == s.user_id for s in shifts)

    def test_generate_daily_shifts_with_three_users(
        self, test_app, test_group, test_user, second_user
    ):
        """Test la génération avec 3 utilisateurs disponibles."""
        with test_app.app_context():
            # Créer un troisième utilisateur
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Doit générer des shifts pour les 3 utilisateurs
            assert len(shifts) == 3

    def test_generate_daily_shifts_dry_run_no_commit(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test que dry_run=True ne commite pas les changements."""
        with test_app.app_context():
            # Compter les shifts existants
            initial_count = Shift.query.count()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=True
            )

            # Vérifier qu'aucun shift n'a été ajouté à la base
            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_generate_daily_shifts_with_commit(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test que dry_run=False commite les changements."""
        with test_app.app_context():
            # Compter les shifts existants
            initial_count = Shift.query.count()

            test_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                test_date, dry_run=False
            )

            # Vérifier que les shifts ont été ajoutés
            final_count = Shift.query.count()
            assert final_count > initial_count


class TestGenerateFullSchedule:
    """Tests pour la génération complète du planning."""

    def test_generate_full_schedule_single_day(self, test_app, test_group, test_user):
        """Test la génération pour un seul jour."""
        with test_app.app_context():
            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 15)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(shifts) > 0

    def test_generate_full_schedule_multiple_days(
        self, test_app, test_group, test_user
    ):
        """Test la génération pour plusieurs jours."""
        with test_app.app_context():
            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            # Doit générer des shifts pour chaque jour ouvré
            # 15, 16, 17, 18, 19, 20 = 6 jours (lundi à vendredi + samedi)
            # Mais seulement du lundi au vendredi
            workdays = [
                d
                for d in range((end_date - start_date).days + 1)
                if (start_date + timedelta(days=d)).weekday() < 5
            ]
            assert (
                len(shifts)
                == len(workdays)
                * User.query.join(Group).filter(Group.is_part_of_schedule).count()
            )

    def test_generate_full_schedule_dry_run(self, test_app, test_group, test_user):
        """Test que dry_run=True ne commite pas."""
        with test_app.app_context():
            initial_count = Shift.query.count()

            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )

            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_generate_full_schedule_with_commit(self, test_app, test_group, test_user):
        """Test que dry_run=False commite les changements."""
        with test_app.app_context():
            initial_count = Shift.query.count()

            start_date = date(2023, 12, 15)
            end_date = date(2023, 12, 20)
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=False
            )

            final_count = Shift.query.count()
            assert final_count > initial_count


class TestRebalanceAfterLeave:
    """Tests pour le rééquilibrage après l'ajout d'un congé."""

    def test_rebalance_after_leave_dry_run(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Test le rééquilibrage en mode dry_run."""
        with test_app.app_context():
            # Créer un congé
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 15),
                end_date=date(2023, 12, 20),
            )
            db.session.add(leave)
            db.session.commit()

            # Compter les shifts initiaux
            initial_count = Shift.query.count()

            # Exécuter le rééquilibrage en dry_run
            shifts, messages = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )

            # Aucun changement ne doit être commité
            final_count = Shift.query.count()
            assert final_count == initial_count

    def test_rebalance_after_leave_with_oncall(self, test_app, test_group, test_user):
        """Test le rééquilibrage avec une astreinte chevauchante."""
        with test_app.app_context():
            # Créer une astreinte
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            # Créer un congé qui chevauche l'astreinte
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            # Exécuter le rééquilibrage
            shifts, messages = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )

            # Doit mentionner la suppression de l'astreinte ou des shifts
            # Le message peut être en français ou anglais
            assert any(
                "astreinte" in msg.lower()
                or "supprim" in msg.lower()
                or "shift" in msg.lower()
                or "delete" in msg.lower()
                or "removed" in msg.lower()
                for msg in messages
            )

    def test_rebalance_after_leave_no_overlap(self, test_app, test_group, test_user):
        """Test le rééquilibrage avec un congé qui ne chevauche rien."""
        with test_app.app_context():
            # Créer un congé dans le futur sans chevauchement
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 5),
            )
            db.session.add(leave)
            db.session.commit()

            shifts, messages = AdvancedShiftAutomation.rebalance_after_leave(
                leave, dry_run=True
            )

            # Doit générer des messages mais pas de suppression
            assert len(messages) > 0


class TestOnCallConstraint:
    """Tests pour la contrainte légale des astreintes."""

    def test_check_oncall_constraint_first_oncall(self, test_app, test_user):
        """Test qu'un utilisateur sans astreinte précédente passe la vérification."""
        with test_app.app_context():
            test_date = date(2023, 12, 15)
            result = AdvancedShiftAutomation.check_oncall_constraint(
                test_user, test_date
            )

            assert result is True

    def test_check_oncall_constraint_sufficient_gap(self, test_app, test_user):
        """Test qu'un utilisateur avec un écart suffisant passe la vérification."""
        with test_app.app_context():
            # Créer une astreinte il y a 3 semaines
            old_friday = date(2023, 11, 24)  # vendredi
            start_time = datetime.combine(old_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier pour une nouvelle astreinte
            test_date = date(2023, 12, 15)  # 3 semaines plus tard
            result = AdvancedShiftAutomation.check_oncall_constraint(
                test_user, test_date
            )

            assert result is True

    def test_check_oncall_constraint_insufficient_gap(self, test_app, test_user):
        """Test qu'un utilisateur avec un écart insuffisant échoue la vérification."""
        with test_app.app_context():
            # Créer une astreinte la semaine dernière
            last_friday = date(2023, 12, 8)  # vendredi
            start_time = datetime.combine(last_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier pour une nouvelle astreinte (seulement 1 semaine d'écart)
            test_date = date(2023, 12, 15)  # 1 semaine plus tard
            result = AdvancedShiftAutomation.check_oncall_constraint(
                test_user, test_date
            )

            assert result is False
