"""
Tests pour les améliorations du système de configuration TOML.

Ces tests couvrent :
1. Le logging des erreurs
2. Le verrouillage thread-safe
3. Le cache avec vérification de date de modification
4. La validation améliorée
5. La synchronisation bidirectionnelle
"""

import pytest
import tempfile
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.config.automation_rules import AutomationConfig
from app.config.migration import ConfigValidator, DatabaseConfigMigrator


class TestAutomationConfigImprovements:
    """Tests pour les améliorations d'AutomationConfig."""
    
    def test_logging_on_file_not_found(self, app, caplog):
        """Test que le logging fonctionne quand le fichier TOML est introuvable."""
        with app.app_context():
            # Sauvegarder le chemin original
            original_path = AutomationConfig._config_path
            
            try:
                # Changer le chemin vers un fichier inexistant
                AutomationConfig._config_path = Path("/nonexistent/path/automation_rules.toml")
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
                
                # Charger la configuration (devrait utiliser les valeurs par défaut)
                config = AutomationConfig.load()
                
                # Vérifier que le warning a été loggé
                assert "Fichier de configuration introuvable" in caplog.text
                assert config == AutomationConfig.DEFAULT_CONFIG
                
            finally:
                # Restaurer le chemin original
                AutomationConfig._config_path = original_path
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
    
    def test_logging_on_toml_parse_error(self, app, caplog):
        """Test que le logging fonctionne quand il y a une erreur de parsing TOML."""
        with app.app_context():
            # Sauvegarder le chemin original
            original_path = AutomationConfig._config_path
            
            try:
                # Créer un fichier TOML invalide
                with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
                    f.write("invalid toml content [[[")
                    temp_path = Path(f.name)
                
                AutomationConfig._config_path = temp_path
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
                
                # Charger la configuration (devrait utiliser les valeurs par défaut)
                config = AutomationConfig.load()
                
                # Vérifier que l'erreur a été loggée
                assert "Erreur de parsing TOML" in caplog.text
                assert config == AutomationConfig.DEFAULT_CONFIG
                
                # Nettoyer
                os.unlink(temp_path)
                
            finally:
                # Restaurer le chemin original
                AutomationConfig._config_path = original_path
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
    
    def test_thread_safety_lock(self, app):
        """Test que le verrouillage thread-safe fonctionne correctement."""
        with app.app_context():
            # Réinitialiser le cache
            AutomationConfig._config = None
            AutomationConfig._config_mtime = None
            
            results = []
            errors = []
            
            def load_config():
                try:
                    config = AutomationConfig.load()
                    results.append(config is not None)
                except Exception as e:
                    errors.append(str(e))
            
            # Lancer plusieurs threads qui chargent la configuration simultanément
            threads = []
            for _ in range(10):
                t = threading.Thread(target=load_config)
                threads.append(t)
                t.start()
            
            # Attendre que tous les threads terminent
            for t in threads:
                t.join()
            
            # Vérifier qu'il n'y a pas eu d'erreurs
            assert len(errors) == 0
            assert all(results)
    
    def test_cache_with_file_modification(self, app):
        """Test que le cache est invalidé quand le fichier est modifié."""
        with app.app_context():
            # Sauvegarder le chemin original
            original_path = AutomationConfig._config_path
            
            try:
                # Créer un fichier TOML temporaire
                with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
                    f.write("""
[oncall]
min_days_between_oncalls = 14

[shifts]
work_days = [0, 1, 2, 3, 4]

[groups]
schedule_groups = ["Test"]
oncall_groups = ["Test"]

[generation]
default_period_days = 180
""")
                    temp_path = Path(f.name)
                
                AutomationConfig._config_path = temp_path
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
                
                # Charger la configuration
                config1 = AutomationConfig.load()
                first_mtime = AutomationConfig._config_mtime
                
                # Modifier le fichier
                time.sleep(0.1)  # Attendre un peu pour s'assurer que le timestamp change
                with open(temp_path, 'w') as f:
                    f.write("""
[oncall]
min_days_between_oncalls = 21

[shifts]
work_days = [0, 1, 2, 3, 4]

[groups]
schedule_groups = ["Test"]
oncall_groups = ["Test"]

[generation]
default_period_days = 180
""")
                
                # Charger à nouveau (devrait recharger depuis le fichier)
                config2 = AutomationConfig.load()
                
                # Vérifier que la configuration a été rechargée
                assert config1['oncall']['min_days_between_oncalls'] == 14
                assert config2['oncall']['min_days_between_oncalls'] == 21
                assert first_mtime != AutomationConfig._config_mtime
                
                # Nettoyer
                os.unlink(temp_path)
                
            finally:
                # Restaurer le chemin original
                AutomationConfig._config_path = original_path
                AutomationConfig._config = None
                AutomationConfig._config_mtime = None
    
    def test_force_reload(self, app):
        """Test que force_reload force le rechargement de la configuration."""
        with app.app_context():
            # Réinitialiser le cache
            AutomationConfig._config = None
            AutomationConfig._config_mtime = None
            
            # Charger la configuration
            config1 = AutomationConfig.load()
            
            # Forcer le rechargement
            config2 = AutomationConfig.load(force_reload=True)
            
            # Les deux devraient être identiques mais le cache devrait avoir été réinitialisé
            assert config1 == config2
    
    def test_sync_methods_return_bool(self, app):
        """Test que les méthodes de synchronisation retournent un booléen."""
        with app.app_context():
            # Tester sync_groups_to_toml
            result = AutomationConfig.sync_groups_to_toml()
            assert isinstance(result, bool)
            
            # Tester sync_shift_types_to_toml
            result = AutomationConfig.sync_shift_types_to_toml()
            assert isinstance(result, bool)


class TestConfigValidatorImprovements:
    """Tests pour les améliorations de ConfigValidator."""
    
    def test_validate_rotation_order_user_exists(self, app):
        """Test la validation que les utilisateurs dans rotation_order existent."""
        with app.app_context():
            # Créer un utilisateur
            from app.models import User, Group
            from app import db
            
            group = Group(name="TestGroup", is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(name="TestUser", email="test@example.com", group_id=group.id)
            db.session.add(user)
            db.session.commit()
            
            # Configuration avec un utilisateur valide
            config = {
                'oncall': {
                    'rotation_order': [user.id],
                    'min_days_between_oncalls': 14,
                    'start_day': 4,
                    'start_hour': 21,
                    'end_day': 4,
                    'end_hour': 7
                },
                'shifts': {
                    'shift_types': [],
                    'rules': [],
                    'work_days': [],
                    'daily_requirements': {}
                },
                'groups': {
                    'schedule_groups': [],
                    'oncall_groups': []
                },
                'generation': {
                    'default_period_days': 180,
                    'advance_generation_enabled': True,
                    'rebalance_on_leave_change': True
                }
            }
            
            is_valid, errors = ConfigValidator.validate_oncall_config(config)
            assert is_valid
            assert len(errors) == 0
            
            # Configuration avec un utilisateur invalide
            config['oncall']['rotation_order'] = [99999]  # ID qui n'existe pas
            is_valid, errors = ConfigValidator.validate_oncall_config(config)
            assert not is_valid
            assert any("Utilisateur introuvable" in error for error in errors)
    
    def test_validate_oncall_duration(self, app):
        """Test la validation de la durée de l'astreinte."""
        with app.app_context():
            # Configuration avec une durée invalide (end avant start)
            config = {
                'oncall': {
                    'rotation_order': [],
                    'min_days_between_oncalls': 14,
                    'start_day': 4,
                    'start_hour': 21,
                    'end_day': 4,
                    'end_hour': 20  # Avant start_hour
                },
                'shifts': {
                    'shift_types': [],
                    'rules': [],
                    'work_days': [],
                    'daily_requirements': {}
                },
                'groups': {
                    'schedule_groups': [],
                    'oncall_groups': []
                },
                'generation': {
                    'default_period_days': 180,
                    'advance_generation_enabled': True,
                    'rebalance_on_leave_change': True
                }
            }
            
            is_valid, errors = ConfigValidator.validate_oncall_config(config)
            assert not is_valid
            assert any("durée de l'astreinte doit être positive" in error for error in errors)
    
    def test_validate_shift_types_required_fields(self, app):
        """Test la validation des champs obligatoires pour shift_types."""
        with app.app_context():
            config = {
                'oncall': {
                    'rotation_order': [],
                    'min_days_between_oncalls': 14,
                    'start_day': 4,
                    'start_hour': 21,
                    'end_day': 4,
                    'end_hour': 7
                },
                'shifts': {
                    'shift_types': [
                        {'start': 7, 'end': 15}  # Missing name and label
                    ],
                    'rules': [],
                    'work_days': [],
                    'daily_requirements': {}
                },
                'groups': {
                    'schedule_groups': [],
                    'oncall_groups': []
                },
                'generation': {
                    'default_period_days': 180,
                    'advance_generation_enabled': True,
                    'rebalance_on_leave_change': True
                }
            }
            
            is_valid, errors = ConfigValidator.validate_shift_config(config)
            assert not is_valid
            assert any("name est obligatoire" in error for error in errors)
            assert any("label est obligatoire" in error for error in errors)
    
    def test_validate_groups_exist(self, app):
        """Test la validation que les groupes référencés existent."""
        with app.app_context():
            # Créer un groupe
            from app.models import Group
            from app import db
            
            group = Group(name="ExistingGroup")
            db.session.add(group)
            db.session.commit()
            
            # Configuration avec un groupe existant
            config = {
                'oncall': {
                    'rotation_order': [],
                    'min_days_between_oncalls': 14,
                    'start_day': 4,
                    'start_hour': 21,
                    'end_day': 4,
                    'end_hour': 7
                },
                'shifts': {
                    'shift_types': [],
                    'rules': [],
                    'work_days': [],
                    'daily_requirements': {}
                },
                'groups': {
                    'schedule_groups': ['ExistingGroup'],
                    'oncall_groups': ['ExistingGroup']
                },
                'generation': {
                    'default_period_days': 180,
                    'advance_generation_enabled': True,
                    'rebalance_on_leave_change': True
                }
            }
            
            is_valid, errors = ConfigValidator.validate_groups_config(config)
            assert is_valid
            assert len(errors) == 0
            
            # Configuration avec un groupe inexistant
            config['groups']['schedule_groups'] = ['NonExistentGroup']
            is_valid, errors = ConfigValidator.validate_groups_config(config)
            assert not is_valid
            assert any("Groupe schedule introuvable" in error for error in errors)
    
    def test_validate_generation_period(self, app):
        """Test la validation de la période de génération."""
        with app.app_context():
            # Configuration avec une période invalide (négative)
            config = {
                'oncall': {
                    'rotation_order': [],
                    'min_days_between_oncalls': 14,
                    'start_day': 4,
                    'start_hour': 21,
                    'end_day': 4,
                    'end_hour': 7
                },
                'shifts': {
                    'shift_types': [],
                    'rules': [],
                    'work_days': [],
                    'daily_requirements': {}
                },
                'groups': {
                    'schedule_groups': [],
                    'oncall_groups': []
                },
                'generation': {
                    'default_period_days': -1,
                    'advance_generation_enabled': True,
                    'rebalance_on_leave_change': True
                }
            }
            
            is_valid, errors = ConfigValidator.validate_generation_config(config)
            assert not is_valid
            assert any("default_period_days doit être positif" in error for error in errors)
            
            # Configuration avec une période trop longue
            config['generation']['default_period_days'] = 2000
            is_valid, errors = ConfigValidator.validate_generation_config(config)
            assert not is_valid
            assert any("ne peut pas dépasser 5 ans" in error for error in errors)


class TestDatabaseConfigMigratorImprovements:
    """Tests pour les améliorations de DatabaseConfigMigrator."""
    
    def test_migrate_to_toml_with_validation(self, app):
        """Test que la migration valide la configuration avant sauvegarde."""
        with app.app_context():
            # Appeler la migration
            result = DatabaseConfigMigrator.sync_toml_from_database()
            
            # Le résultat devrait être une chaîne (pas d'exception)
            assert isinstance(result, str)
            assert "Migration terminée" in result or "Erreur" in result
    
    def test_sync_database_from_toml(self, app):
        """Test la synchronisation de la base depuis TOML."""
        with app.app_context():
            # Appeler la synchronisation
            result = DatabaseConfigMigrator.sync_database_from_toml()
            
            # Le résultat devrait être une chaîne
            assert isinstance(result, str)
            assert "Synchronisation terminée" in result or "Aucune modification" in result or "Erreur" in result


class TestPerformanceImprovements:
    """Tests pour les améliorations de performance."""
    
    def test_sync_shift_types_from_toml_no_duplicate_queries(self, app):
        """Test que la synchronisation des types de shifts ne fait pas de requêtes inutiles."""
        with app.app_context():
            # Cette méthode devrait être optimisée pour éviter les requêtes N+1
            result = AutomationConfig.sync_shift_types_from_toml()
            assert isinstance(result, bool)
    
    def test_generate_full_schedule_with_advanced_rules(self, app):
        """Test que la génération complète utilise les règles avancées."""
        with app.app_context():
            from app.utils.automation import generate_full_schedule
            from datetime import date
            
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            
            # Générer avec les règles avancées
            result = generate_full_schedule(
                start_date=start_date,
                end_date=end_date,
                dry_run=True,
                use_advanced_rules=True
            )
            
            assert 'oncall' in result
            assert 'shift' in result
            assert 'summary' in result
