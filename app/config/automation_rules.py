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
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime, timedelta


class AutomationConfig:
    """Classe pour gérer la configuration des règles d'automatisation."""
    
    _config = None
    _config_path = Path(__file__).parent / "automation_rules.toml"
    
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
    def load(cls) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier TOML."""
        if cls._config is None:
            try:
                with open(cls._config_path, 'r', encoding='utf-8') as f:
                    cls._config = toml.load(f)
                # Appliquer les valeurs par défaut pour les clés manquantes
                cls._config = cls._merge_with_defaults(cls._config)
            except FileNotFoundError:
                # Si le fichier n'existe pas, créer une configuration par défaut
                cls._config = cls.DEFAULT_CONFIG.copy()
                cls.save(cls._config)
            except Exception as e:
                # En cas d'erreur de parsing, utiliser la config par défaut
                cls._config = cls.DEFAULT_CONFIG.copy()
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
        """Sauvegarde la configuration dans le fichier TOML."""
        cls._config = config
        try:
            with open(cls._config_path, 'w', encoding='utf-8') as f:
                toml.dump(config, f)
        except Exception as e:
            raise Exception(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
    
    @classmethod
    def reload(cls) -> None:
        """Recharge la configuration depuis le fichier."""
        cls._config = None
        cls.load()
    
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
    def sync_groups_to_toml(cls) -> None:
        """
        Synchronise les groupes de la base de données avec la configuration TOML.
        Met à jour schedule_groups et oncall_groups dans le fichier TOML
        en fonction des flags is_part_of_schedule et is_part_of_oncall.
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
            
        except Exception as e:
            # Ne pas faire échouer l'opération principale
            pass
