"""
Tests pour le module d'automatisation des astreintes et des shifts.
"""

import pytest
from datetime import datetime, date, timedelta
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from app.utils.automation import (
    OnCallAutomation,
    ShiftAutomation,
    BusinessRules,
    
    get_automation_status,
)
from app import db


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
    
    def test_get_rotation_order_default(self, test_app, test_group, test_user, second_user):
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
    
    def test_get_rotation_order_custom(self, test_app, test_group, test_user, second_user):
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
    
    def test_find_next_available_user(self, test_app, test_group, test_user, second_user):
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
            
            oncall = OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
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
    
    def test_generate_oncall_schedule_dry_run(self, test_app, test_group, test_user, second_user):
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
                assert oncalls[i].start_time == oncalls[i-1].start_time + timedelta(days=7)
    
    def test_generate_oncall_schedule_with_rotation(self, test_app, test_group, test_user, second_user):
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
            
            assert len(oncalls) == 2
            # La première astreinte devrait être pour second_user
            assert oncalls[0].user_id == second_user.id
            # La deuxième astreinte devrait être pour test_user
            assert oncalls[1].user_id == test_user.id


class TestShiftAutomation:
    """Tests pour l'automatisation des shifts."""
    
    def test_get_eligible_users(self, test_app, test_group, test_user, second_user):
        """Test la récupération des utilisateurs éligibles pour les shifts."""
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
            
            eligible_users = ShiftAutomation.get_eligible_users()
            # Tous les utilisateurs du groupe sont éligibles (is_part_of_schedule=True)
            assert len(eligible_users) == 3
    
    def test_get_shift_types(self, test_app, test_shift_type, afternoon_shift_type):
        """Test la récupération des types de shifts."""
        with test_app.app_context():
            shift_types = ShiftAutomation.get_shift_types()
            assert len(shift_types) == 2
    
    def test_can_assign_shift(self, test_app, test_user, test_shift_type):
        """Test la vérification de l'assignation d'un shift."""
        with test_app.app_context():
            # Test avec une date valide (lundi)
            test_date = date(2024, 1, 8)  # Lundi
            can_assign, message = ShiftAutomation.can_assign_shift(
                test_user.id, test_date, test_shift_type
            )
            assert can_assign is True
            assert message == ""
            
            # Test avec une date invalide (samedi)
            test_date = date(2024, 1, 6)  # Samedi
            can_assign, message = ShiftAutomation.can_assign_shift(
                test_user.id, test_date, test_shift_type
            )
            assert can_assign is False
            assert "lundi au vendredi" in message
    
    def test_can_assign_shift_with_conflict(self, test_app, test_user, test_shift_type):
        """Test la vérification avec un conflit existant."""
        with test_app.app_context():
            test_date = date(2024, 1, 8)  # Lundi
            
            # Créer un shift existant pour test_user
            start_time = datetime(2024, 1, 8, 7, 0)
            end_time = datetime(2024, 1, 8, 15, 0)
            existing_shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=test_date
            )
            db.session.add(existing_shift)
            db.session.commit()
            
            # Vérifier qu'on ne peut pas assigner un autre shift
            can_assign, message = ShiftAutomation.can_assign_shift(
                test_user.id, test_date, test_shift_type
            )
            assert can_assign is False
            assert "déjà un shift" in message
            
            # Nettoyer
            db.session.delete(existing_shift)
            db.session.commit()
    
    def test_find_replacement_user(self, test_app, test_group, test_user, second_user):
        """Test la recherche d'un utilisateur de remplacement."""
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
            
            test_date = date(2024, 1, 8)  # Lundi
            
            # Exclure test_user et second_user
            excluded_ids = [test_user.id, second_user.id]
            
            replacement = ShiftAutomation.find_replacement_user(
                excluded_ids, test_date, ShiftType.query.first()
            )
            
            assert replacement is not None
            assert replacement.id == user3.id
    
    def test_generate_shift_schedule_dry_run(self, test_app, test_group, test_user, second_user, test_shift_type):
        """Test la génération des shifts en mode dry run."""
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
            
            start_date = date(2024, 1, 8)  # Lundi
            end_date = date(2024, 1, 12)  # Vendredi
            
            # Règles : 1 shift de chaque type par jour
            rules = {
                'daily_requirements': {
                    'monday': {'morning': 1},
                    'tuesday': {'morning': 1},
                    'wednesday': {'morning': 1},
                    'thursday': {'morning': 1},
                    'friday': {'morning': 1},
                }
            }
            
            shifts, messages = ShiftAutomation.generate_shift_schedule(
                start_date, end_date, rules, dry_run=True
            )
            
            # Devrait générer 1 shift par jour * 5 jours = 5 shifts
            assert len(shifts) == 5
            assert len(messages) > 0


class TestBusinessRules:
    """Tests pour les règles métiers."""
    
    def test_get_shift_rules(self):
        """Test la récupération des règles par défaut pour les shifts."""
        rules = BusinessRules.get_shift_rules()
        
        assert 'daily_requirements' in rules
        assert 'max_shifts_per_user_per_week' in rules
        assert 'min_shifts_per_user_per_week' in rules
        
        # Vérifier que les jours de la semaine sont présents
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            assert day in rules['daily_requirements']
    
    def test_get_oncall_rules(self):
        """Test la récupération des règles par défaut pour les astreintes."""
        rules = BusinessRules.get_oncall_rules()
        
        assert 'rotation_order' in rules
        assert 'start_day' in rules
        assert 'start_hour' in rules
        assert rules['start_day'] == 'friday'
        assert rules['start_hour'] == 21


class TestFullScheduleGeneration:
    """Tests pour la génération complète du schedule."""
    
    def test_generate_full_schedule_dry_run(self, test_app, test_group, test_user, second_user, test_shift_type):
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
            
            result = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=True
            )
            
            assert 'oncall' in result
            assert 'shift' in result
            assert 'summary' in result
            
            # Devrait générer des astreintes
            assert len(result['oncall']['generated']) == 2
            # Devrait générer des shifts (selon les règles par défaut)
            assert len(result['shift']['generated']) > 0
    
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
            
            assert 'oncall_count' in status
            assert 'shift_count' in status
            assert 'oncall_eligible_users' in status
            assert 'shift_eligible_users' in status
            assert 'next_available_oncall_date' in status
            
            # Vérifier les valeurs
            assert status['oncall_eligible_users'] == 3
            assert status['shift_eligible_users'] == 3


class TestEdgeCases:
    """Tests pour les cas particuliers."""
    
    def test_generate_oncall_no_eligible_users(self, test_app):
        """Test la génération d'astreintes sans utilisateurs éligibles."""
        with test_app.app_context():
            # Créer un groupe sans is_part_of_oncall
            group = Group(name="No OnCall", is_part_of_schedule=True, is_part_of_oncall=False)
            db.session.add(group)
            db.session.commit()
            
            start_date = date(2024, 1, 5)
            end_date = date(2024, 1, 19)
            
            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            
            assert len(oncalls) == 0
            assert any("Aucun utilisateur éligible" in msg for msg in messages)
    
    def test_generate_shift_no_eligible_users(self, test_app):
        """Test la génération de shifts sans utilisateurs éligibles."""
        with test_app.app_context():
            # Créer un groupe sans is_part_of_schedule
            group = Group(name="No Schedule", is_part_of_schedule=False, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            start_date = date(2024, 1, 8)
            end_date = date(2024, 1, 12)
            
            shifts, messages = ShiftAutomation.generate_shift_schedule(
                start_date, end_date, dry_run=True
            )
            
            assert len(shifts) == 0
            assert any("Aucun utilisateur éligible" in msg for msg in messages)
    
    def test_generate_oncall_with_leave_conflict(self, test_app, test_group, test_user, second_user):
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
                end_date=date(2024, 1, 12)
            )
            db.session.add(leave)
            db.session.commit()
            
            start_date = date(2024, 1, 5)  # Vendredi
            end_date = date(2024, 1, 19)  # 2 semaines plus tard
            
            oncalls, messages = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            
            # Devrait générer 2 astreintes, mais test_user ne devrait pas être assigné
            assert len(oncalls) == 2
            assert all(oncall.user_id != test_user.id for oncall in oncalls)
            
            # Nettoyer
            db.session.delete(leave)
            db.session.commit()
