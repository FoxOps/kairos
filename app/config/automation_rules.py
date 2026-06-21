# =============================================================================
# MODULE DE CONFIGURATION DES RÈGLES D'AUTOMATISATION
# =============================================================================
"""
Module pour charger, valider et gérer la configuration des règles d'automatisation
depuis un fichier TOML.

Utilisation :
    from app.config.automation_rules import AutomationConfig
    
    # Charger la configuration
    config = AutomationConfig.load()
    
    # Accéder à une section
    oncall_config = AutomationConfig.get_oncall_rules()
    shift_config = AutomationConfig.get_shift_rules()
    
    # Sauvegarder la configuration
    AutomationConfig.save(new_config)
"""

import toml
import threading
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime, timedelta

# Configuration du logger
logger = logging.getLogger(__name__)


class AutomationConfig:
    """Classe pour gérer la configuration des règles d'automatisation."""
    
    _config = None
    _config_path = Path(__file__).parent / "automation_rules.toml"
    _config_mtime = None  # Date de modification du fichier
    _lock = threading.Lock()  # Verrou pour la synchronisation thread-safe
    
    # Valeurs par défaut pour la validation
    DEFAULT_CONFIG = {
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
                {'name': 'morning', 'start': 7, 'end': 15, 'label': '07h-15h'},
                {'name': 'day', 'start': 9, 'end': 17, 'label': '09h-17h'},
                {'name': 'evening', 'start': 13, 'end': 21, 'label': '13h-21h'}
            ],
            'rules': [
                {'rule': 'oncall_has_evening_shift', 'enabled': True, 'priority': 1, 
                 'description': 'Personne en astreinte = shift 13h-21h (si dans groupe schedule)'},
                {'rule': 'rotation_after_oncall', 'enabled': True, 'priority': 2,
                 'description': 'Rotation : après astreinte = shift 07h-15h la semaine suivante'},
                {'rule': 'default_shift', 'enabled': True, 'priority': 3,
                 'description': 'Shift par défaut : 09h-17h'},
                {'rule': 'two_users_special_case', 'enabled': True, 'priority': 4,
                 'description': '2 utilisateurs : non-astreinte = 07h-15h, astreinte = 13h-21h'}
            ],
            'work_days': [0, 1, 2, 3, 4],
            'daily_requirements': {
                'monday': {'morning': 1, 'day': 1, 'evening': 1},
                'tuesday': {'morning': 1, 'day': 1, 'evening': 1},
                'wednesday': {'morning': 1, 'day': 1, 'evening': 1},
                'thursday': {'morning': 1, 'day': 1, 'evening': 1},
                'friday': {'morning': 1, 'day': 1, 'evening': 1}
            }
        },
        'groups': {
            'schedule_groups': ['Technique', 'Support'],
            'oncall_groups': ['Astreinte', 'Technique']
        },
        'generation': {
            'default_period_days': 180,
            'advance_generation_enabled': True,
            'rebalance_on_leave_change': True
        }
    }
    
    @classmethod
    def _get_file_mtime(cls) -> float:
        """Récupère la date de modification du fichier TOML."""
        try:
            return cls._config_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0
    
    @classmethod
    def _load_from_file(cls) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier TOML avec gestion des erreurs."""
        try:
            with open(cls._config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            logger.info(f"Configuration chargée depuis {cls._config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Fichier de configuration introuvable: {cls._config_path}. Utilisation de la configuration par défaut.")
            return cls.DEFAULT_CONFIG.copy()
        except toml.TomlDecodeError as e:
            logger.error(f"Erreur de parsing TOML dans {cls._config_path}: {str(e)}. Utilisation de la configuration par défaut.")
            return cls.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Erreur inattendue lors du chargement de la configuration: {str(e)}. Utilisation de la configuration par défaut.")
            return cls.DEFAULT_CONFIG.copy()
    
    @classmethod
    def load(cls, force_reload: bool = False) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier TOML.
        
        Args:
            force_reload: Si True, force le rechargement depuis le fichier
            
        Returns:
            Dictionnaire de configuration
        """
        with cls._lock:
            # Vérifier si le fichier a été modifié depuis le dernier chargement
            current_mtime = cls._get_file_mtime()
            
            if force_reload or cls._config is None or cls._config_mtime != current_mtime:
                cls._config = cls._load_from_file()
                cls._config = cls._merge_with_defaults(cls._config)
                cls._config_mtime = current_mtime
                logger.debug("Configuration rechargée (fichier modifié ou premier chargement)")
            
            return cls._config
    
    @classmethod
    def _merge_with_defaults(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne la configuration chargée avec les valeurs par défaut."""
        merged = cls.DEFAULT_CONFIG.copy()
        
        # Fusionner chaque section
        for section in cls.DEFAULT_CONFIG.keys():
            if section in config:
                if isinstance(cls.DEFAULT_CONFIG[section], dict):
                    merged[section].update(config[section])
                else:
                    merged[section] = config[section]
        
        return merged
    
    @classmethod
    def save(cls, config: Dict[str, Any]) -> None:
        """
        Sauvegarde la configuration dans le fichier TOML.
        
        Args:
            config: Dictionnaire de configuration à sauvegarder
            
        Raises:
            Exception: En cas d'erreur de sauvegarde
        """
        with cls._lock:
            try:
                # Créer une copie pour éviter de modifier l'original
                config_to_save = config.copy()
                
                # Sauvegarder dans le fichier
                with open(cls._config_path, 'w', encoding='utf-8') as f:
                    toml.dump(config_to_save, f)
                
                # Mettre à jour le cache et le timestamp
                cls._config = config_to_save
                cls._config_mtime = cls._get_file_mtime()
                
                logger.info(f"Configuration sauvegardée dans {cls._config_path}")
                
            except PermissionError as e:
                logger.error(f"Permission refusée lors de la sauvegarde de la configuration: {str(e)}")
                raise Exception(f"Permission refusée: {str(e)}")
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
                raise Exception(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
    
    @classmethod
    def reload(cls) -> None:
        """Recharge la configuration depuis le fichier."""
        with cls._lock:
            cls._config = None
            cls._config_mtime = None
            cls.load()
            logger.info("Configuration rechargée manuellement")
    
    # =========================================================================
    # Méthodes d'accès aux sections de configuration
    # =========================================================================
    
    @classmethod
    def get_oncall_rules(cls) -> Dict[str, Any]:
        """Récupère la configuration des astreintes."""
        return cls.load().get('oncall', cls.DEFAULT_CONFIG['oncall'])
    
    @classmethod
    def get_shift_rules(cls) -> Dict[str, Any]:
        """Récupère la configuration des shifts."""
        return cls.load().get('shifts', cls.DEFAULT_CONFIG['shifts'])
    
    @classmethod
    def get_group_rules(cls) -> Dict[str, Any]:
        """Récupère la configuration des groupes."""
        return cls.load().get('groups', cls.DEFAULT_CONFIG['groups'])
    
    @classmethod
    def get_generation_rules(cls) -> Dict[str, Any]:
        """Récupère la configuration de génération."""
        return cls.load().get('generation', cls.DEFAULT_CONFIG['generation'])
    
    # =========================================================================
    # Méthodes utilitaires pour les astreintes
    # =========================================================================
    
    @classmethod
    def get_rotation_order(cls) -> List[int]:
        """Récupère l'ordre de rotation des astreintes."""
        return cls.get_oncall_rules().get('rotation_order', [])
    
    @classmethod
    def get_min_days_between_oncalls(cls) -> int:
        """Récupère le nombre minimum de jours entre deux astreintes."""
        return cls.get_oncall_rules().get('min_days_between_oncalls', 14)
    
    @classmethod
    def get_oncall_start_datetime(cls, base_date: date) -> datetime:
        """Calcule la date/heure de début d'une astreinte à partir d'une date de base."""
        oncall_config = cls.get_oncall_rules()
        start_day = oncall_config.get('start_day', 4)
        start_hour = oncall_config.get('start_hour', 21)
        
        # Trouver le prochain jour correspondant à start_day
        current_date = base_date
        while current_date.weekday() != start_day:
            current_date += timedelta(days=1)
        
        return datetime.combine(current_date, datetime.min.time()).replace(hour=start_hour)
    
    @classmethod
    def get_oncall_end_datetime(cls, start_datetime: datetime) -> datetime:
        """Calcule la date/heure de fin d'une astreinte à partir de son début."""
        oncall_config = cls.get_oncall_rules()
        end_day = oncall_config.get('end_day', 4)
        end_hour = oncall_config.get('end_hour', 7)
        
        # L'astreinte dure 7 jours - 14 heures (du vendredi 21h au vendredi suivant 07h)
        # Mais avec la config, on peut calculer la fin basée sur end_day et end_hour
        start_date = start_datetime.date()
        
        # Trouver le jour de fin (end_day de la semaine suivante)
        end_date = start_date + timedelta(days=7)
        while end_date.weekday() != end_day:
            end_date += timedelta(days=1)
        
        return datetime.combine(end_date, datetime.min.time()).replace(hour=end_hour)
    
    @classmethod
    def get_oncall_duration(cls) -> Tuple[int, int]:
        """Récupère la durée de l'astreinte en jours et heures."""
        # Par défaut : 7 jours - 14 heures (vendredi 21h -> vendredi suivant 07h)
        # Mais calculé à partir de la config
        start_day = cls.get_oncall_rules().get('start_day', 4)
        start_hour = cls.get_oncall_rules().get('start_hour', 21)
        end_day = cls.get_oncall_rules().get('end_day', 4)
        end_hour = cls.get_oncall_rules().get('end_hour', 7)
        
        # Calculer la différence
        # Exemple : vendredi 21h -> vendredi suivant 07h = 6 jours + 10 heures
        if end_day >= start_day:
            days_diff = end_day - start_day
        else:
            days_diff = (7 - start_day) + end_day
        
        hours_diff = end_hour - start_hour
        
        return days_diff, hours_diff
    
    # =========================================================================
    # Méthodes utilitaires pour les shifts
    # =========================================================================
    
    @classmethod
    def get_shift_types(cls) -> List[Dict[str, Any]]:
        """Récupère les types de shifts configurés."""
        return cls.get_shift_rules().get('shift_types', [])
    
    @classmethod
    def get_work_days(cls) -> List[int]:
        """Récupère les jours de travail (0=lundi, 6=dimanche)."""
        return cls.get_shift_rules().get('work_days', [0, 1, 2, 3, 4])
    
    @classmethod
    def get_daily_requirements(cls) -> Dict[str, Dict[str, int]]:
        """Récupère les besoins quotidiens en shifts."""
        return cls.get_shift_rules().get('daily_requirements', {})
    
    @classmethod
    def get_enabled_rules(cls) -> List[Dict[str, Any]]:
        """Récupère les règles activées, triées par priorité."""
        rules = cls.get_shift_rules().get('rules', [])
        enabled_rules = [rule for rule in rules if rule.get('enabled', False)]
        return sorted(enabled_rules, key=lambda x: x.get('priority', 0))
    
    @classmethod
    def is_rule_enabled(cls, rule_name: str) -> bool:
        """Vérifie si une règle spécifique est activée."""
        rules = cls.get_shift_rules().get('rules', [])
        for rule in rules:
            if rule.get('rule') == rule_name:
                return rule.get('enabled', False)
        return False
    
    # =========================================================================
    # Méthodes utilitaires pour les groupes
    # =========================================================================
    
    @classmethod
    def get_schedule_group_names(cls) -> List[str]:
        """Récupère les noms des groupes éligibles pour les shifts."""
        return cls.get_group_rules().get('schedule_groups', ['Technique', 'Support'])
    
    @classmethod
    def get_oncall_group_names(cls) -> List[str]:
        """Récupère les noms des groupes éligibles pour les astreintes."""
        return cls.get_group_rules().get('oncall_groups', ['Astreinte', 'Technique'])
    
    # =========================================================================
    # Méthodes utilitaires pour la génération
    # =========================================================================
    
    @classmethod
    def get_default_period_days(cls) -> int:
        """Récupère la période par défaut en jours."""
        return cls.get_generation_rules().get('default_period_days', 180)
    
    @classmethod
    def is_advance_generation_enabled(cls) -> bool:
        """Vérifie si la génération automatique à l'avance est activée."""
        return cls.get_generation_rules().get('advance_generation_enabled', True)
    
    @classmethod
    def is_rebalance_on_leave_change_enabled(cls) -> bool:
        """Vérifie si le rééquilibrage automatique lors des changements de congés est activé."""
        return cls.get_generation_rules().get('rebalance_on_leave_change', True)
    
    # =========================================================================
    # Méthodes de synchronisation avec la base de données
    # =========================================================================
    
    @classmethod
    def sync_groups_to_toml(cls) -> bool:
        """
        Synchronise les groupes de la base de données avec la configuration TOML.
        Met à jour schedule_groups et oncall_groups dans le fichier TOML
        en fonction des flags is_part_of_schedule et is_part_of_oncall.
        
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        from app import db
        from app.models import Group
        
        try:
            config = cls.load()
            
            # Récupérer tous les groupes
            groups = Group.query.all()
            
            # Construire les listes de groupes
            schedule_groups = []
            oncall_groups = []
            
            for group in groups:
                if group.is_part_of_schedule:
                    schedule_groups.append(group.name)
                if group.is_part_of_oncall:
                    oncall_groups.append(group.name)
            
            # Mettre à jour la configuration
            config['groups']['schedule_groups'] = schedule_groups
            config['groups']['oncall_groups'] = oncall_groups
            
            # Sauvegarder
            cls.save(config)
            cls.reload()
            
            logger.info(f"Synchronisation des groupes vers TOML: {len(schedule_groups)} groupes schedule, {len(oncall_groups)} groupes oncall")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation des groupes vers TOML: {str(e)}")
            return False
    
    @classmethod
    def sync_shift_types_to_toml(cls) -> bool:
        """
        Synchronise les types de shifts de la base de données avec la configuration TOML.
        Met à jour shift_types dans le fichier TOML à partir de la table ShiftType.
        
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        from app import db
        from app.models import ShiftType
        
        try:
            config = cls.load()
            
            # Récupérer tous les types de shifts
            shift_types = ShiftType.query.order_by(ShiftType.start_hour).all()
            
            # Construire la liste des types de shifts
            shift_types_list = []
            for st in shift_types:
                shift_types_list.append({
                    'name': st.name,
                    'start': st.start_hour,
                    'end': st.end_hour,
                    'label': st.label
                })
            
            # Mettre à jour la configuration
            config['shifts']['shift_types'] = shift_types_list
            
            # Sauvegarder
            cls.save(config)
            cls.reload()
            
            logger.info(f"Synchronisation des types de shifts vers TOML: {len(shift_types_list)} types")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation des types de shifts vers TOML: {str(e)}")
            return False
    
    @classmethod
    def sync_shift_types_from_toml(cls) -> bool:
        """
        Synchronise les types de shifts de la configuration TOML vers la base de données.
        Crée ou met à jour les ShiftType en base à partir de la configuration.
        
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        from app import db
        from app.models import ShiftType
        
        try:
            config = cls.load()
            shift_types_config = config['shifts']['shift_types']
            
            # Récupérer les types de shifts existants
            existing_shift_types = ShiftType.query.all()
            existing_names = {st.name for st in existing_shift_types}
            
            # Mettre à jour ou créer les types de shifts
            for st_config in shift_types_config:
                name = st_config['name']
                start = st_config['start']
                end = st_config['end']
                label = st_config['label']
                
                if name in existing_names:
                    # Mettre à jour le type existant
                    shift_type = ShiftType.query.filter_by(name=name).first()
                    shift_type.label = label
                    shift_type.start_hour = start
                    shift_type.end_hour = end
                    db.session.add(shift_type)
                else:
                    # Créer un nouveau type
                    new_shift_type = ShiftType(
                        name=name,
                        label=label,
                        start_hour=start,
                        end_hour=end
                    )
                    db.session.add(new_shift_type)
                
                existing_names.discard(name)
            
            # Supprimer les types qui ne sont plus dans la configuration
            for name in existing_names:
                shift_type = ShiftType.query.filter_by(name=name).first()
                db.session.delete(shift_type)
            
            db.session.commit()
            logger.info(f"Synchronisation des types de shifts depuis TOML: {len(shift_types_config)} types synchronisés")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la synchronisation des types de shifts depuis TOML: {str(e)}")
            return False
    
    @classmethod
    def sync_rotation_order_from_toml(cls) -> bool:
        """
        Synchronise l'ordre de rotation de la configuration TOML vers la base de données.
        Met à jour les flags is_part_of_oncall des utilisateurs selon rotation_order.
        
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        from app import db
        from app.models import User
        
        try:
            config = cls.load()
            rotation_order_ids = config['oncall'].get('rotation_order', [])
            
            # Récupérer tous les utilisateurs
            all_users = User.query.all()
            
            # Marquer tous les utilisateurs comme non éligibles pour les astreintes
            for user in all_users:
                user.is_part_of_oncall = False
                db.session.add(user)
            
            # Marquer les utilisateurs dans rotation_order comme éligibles
            for user_id in rotation_order_ids:
                user = User.query.get(user_id)
                if user:
                    user.is_part_of_oncall = True
                    db.session.add(user)
                else:
                    logger.warning(f"Utilisateur ID {user_id} introuvable dans la base de données")
            
            db.session.commit()
            logger.info(f"Synchronisation de l'ordre de rotation depuis TOML: {len(rotation_order_ids)} utilisateurs marqués comme éligibles")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la synchronisation de l'ordre de rotation depuis TOML: {str(e)}")
            return False
    
    @classmethod
    def sync_all_from_toml(cls) -> Dict[str, bool]:
        """
        Synchronise toutes les données de la configuration TOML vers la base de données.
        
        Returns:
            Dict[str, bool]: Dictionnaire avec le statut de chaque synchronisation
        """
        results = {}
        
        # Synchroniser les groupes
        results['groups'] = cls.sync_groups_from_toml()
        
        # Synchroniser les types de shifts
        results['shift_types'] = cls.sync_shift_types_from_toml()
        
        # Synchroniser l'ordre de rotation
        results['rotation_order'] = cls.sync_rotation_order_from_toml()
        
        logger.info(f"Synchronisation complète depuis TOML: {results}")
        return results
    
    @classmethod
    def sync_groups_from_toml(cls) -> bool:
        """
        Synchronise les groupes de la configuration TOML vers la base de données.
        Met à jour les flags is_part_of_schedule et is_part_of_oncall.
        
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        from app import db
        from app.models import Group
        
        try:
            config = cls.load()
            schedule_group_names = config['groups'].get('schedule_groups', [])
            oncall_group_names = config['groups'].get('oncall_groups', [])
            
            # Mettre à jour les flags des groupes existants
            for group in Group.query.all():
                was_updated = False
                
                if group.name in schedule_group_names and not group.is_part_of_schedule:
                    group.is_part_of_schedule = True
                    was_updated = True
                elif group.name not in schedule_group_names and group.is_part_of_schedule:
                    group.is_part_of_schedule = False
                    was_updated = True
                
                if group.name in oncall_group_names and not group.is_part_of_oncall:
                    group.is_part_of_oncall = True
                    was_updated = True
                elif group.name not in oncall_group_names and group.is_part_of_oncall:
                    group.is_part_of_oncall = False
                    was_updated = True
                
                if was_updated:
                    db.session.add(group)
            
            db.session.commit()
            logger.info(f"Synchronisation des groupes depuis TOML: {len(schedule_group_names)} groupes schedule, {len(oncall_group_names)} groupes oncall")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la synchronisation des groupes depuis TOML: {str(e)}")
            return False
