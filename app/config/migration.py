# =============================================================================
# MODULE DE MIGRATION DES DONNÉES EXISTANTES VERS LE FORMAT TOML
# =============================================================================
"""
Module pour migrer les données de configuration existantes (en base de données)
vers le nouveau format TOML.

Ce module fournit des fonctions pour :
1. Extraire la configuration actuelle depuis la base de données
2. Générer un fichier TOML avec ces données
3. Synchroniser la base de données avec le fichier TOML
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app import db
from app.models import Group, User, ShiftType
from app.config.automation_rules import AutomationConfig


class DatabaseConfigMigrator:
    """Classe pour migrer la configuration depuis la base de données vers TOML."""
    
    @staticmethod
    def extract_groups_config() -> Dict[str, List[str]]:
        """Extrait la configuration des groupes depuis la base de données."""
        schedule_groups = []
        oncall_groups = []
        
        groups = Group.query.all()
        for group in groups:
            if group.is_part_of_schedule:
                schedule_groups.append(group.name)
            if group.is_part_of_oncall:
                oncall_groups.append(group.name)
        
        return {
            'schedule_groups': schedule_groups,
            'oncall_groups': oncall_groups
        }
    
    @staticmethod
    def extract_shift_types_config() -> List[Dict[str, Any]]:
        """Extrait les types de shifts depuis la base de données."""
        shift_types = ShiftType.query.order_by(ShiftType.start_hour).all()
        
        result = []
        for st in shift_types:
            result.append({
                'name': st.name,
                'start': st.start_hour,
                'end': st.end_hour,
                'label': st.label
            })
        
        return result
    
    @staticmethod
    def extract_rotation_order() -> List[int]:
        """Extrait l'ordre de rotation depuis les utilisateurs éligibles."""
        # Récupérer les utilisateurs éligibles pour les astreintes
        oncall_groups = AutomationConfig.get_oncall_group_names()
        
        # Si oncall_groups est vide (premier chargement), utiliser les groupes de la base
        if not oncall_groups:
            groups = Group.query.filter_by(is_part_of_oncall=True).all()
            oncall_group_ids = [g.id for g in groups]
            users = User.query.filter(User.group_id.in_(oncall_group_ids)).order_by(User.name).all()
        else:
            # Filtrer les utilisateurs dont le groupe est dans oncall_groups
            users = User.query.join(Group).filter(
                Group.name.in_(oncall_groups),
                User.is_admin == False  # Exclure les admins par défaut
            ).order_by(User.name).all()
        
        return [user.id for user in users]
    
    @staticmethod
    def extract_oncall_timing() -> Dict[str, Any]:
        """Extrait les paramètres de timing des astreintes depuis les données existantes."""
        # Par défaut, les astreintes commencent le vendredi à 21h et finissent le vendredi suivant à 07h
        # Vérifier si des astreintes existent pour confirmer
        from app.models import OnCall
        
        oncall = OnCall.query.first()
        if oncall:
            start_day = oncall.start_time.weekday()
            start_hour = oncall.start_time.hour
            end_day = oncall.end_time.weekday()
            end_hour = oncall.end_time.hour
            
            return {
                'start_day': start_day,
                'start_hour': start_hour,
                'end_day': end_day,
                'end_hour': end_hour
            }
        
        # Valeurs par défaut
        return {
            'start_day': 4,  # Vendredi
            'start_hour': 21,
            'end_day': 4,    # Vendredi
            'end_hour': 7
        }
    
    @staticmethod
    def migrate_to_toml() -> Dict[str, Any]:
        """
        Migre toutes les données de configuration depuis la base vers un dictionnaire
        compatible avec le format TOML.
        """
        config = AutomationConfig.DEFAULT_CONFIG.copy()
        
        # Migrer les groupes
        groups_config = DatabaseConfigMigrator.extract_groups_config()
        config['groups'].update(groups_config)
        
        # Migrer les types de shifts
        shift_types = DatabaseConfigMigrator.extract_shift_types_config()
        if shift_types:
            config['shifts']['shift_types'] = shift_types
        
        # Migrer l'ordre de rotation
        rotation_order = DatabaseConfigMigrator.extract_rotation_order()
        if rotation_order:
            config['oncall']['rotation_order'] = rotation_order
        
        # Migrer le timing des astreintes
        oncall_timing = DatabaseConfigMigrator.extract_oncall_timing()
        config['oncall'].update(oncall_timing)
        
        return config
    
    @staticmethod
    def sync_toml_from_database() -> str:
        """
        Synchronise le fichier TOML avec les données de la base de données.
        Retourne un message indiquant ce qui a été migré.
        """
        try:
            # Extraire la configuration depuis la base
            new_config = DatabaseConfigMigrator.migrate_to_toml()
            
            # Sauvegarder dans le fichier TOML
            AutomationConfig.save(new_config)
            
            # Recharger la configuration
            AutomationConfig.reload()
            
            messages = []
            
            # Générer un résumé de ce qui a été migré
            if new_config['groups']['schedule_groups']:
                messages.append(f"Groupes schedule: {new_config['groups']['schedule_groups']}")
            if new_config['groups']['oncall_groups']:
                messages.append(f"Groupes astreintes: {new_config['groups']['oncall_groups']}")
            if new_config['oncall']['rotation_order']:
                messages.append(f"Ordre de rotation: {len(new_config['oncall']['rotation_order'])} utilisateurs")
            if new_config['shifts']['shift_types']:
                messages.append(f"Types de shifts: {len(new_config['shifts']['shift_types'])} types")
            
            return "✅ Migration terminée. " + ", ".join(messages)
            
        except Exception as e:
            return f"❌ Erreur lors de la migration: {str(e)}"
    
    @staticmethod
    def sync_database_from_toml() -> str:
        """
        Synchronise la base de données avec le fichier TOML.
        Cela permet de mettre à jour les groupes et autres paramètres.
        Retourne un message indiquant ce qui a été synchronisé.
        """
        try:
            config = AutomationConfig.load()
            messages = []
            
            # Synchroniser les groupes
            schedule_group_names = config['groups']['schedule_groups']
            oncall_group_names = config['groups']['oncall_groups']
            
            # Mettre à jour les flags des groupes existants
            for group in Group.query.all():
                was_updated = False
                
                if group.name in schedule_group_names and not group.is_part_of_schedule:
                    group.is_part_of_schedule = True
                    was_updated = True
                    messages.append(f"Groupe '{group.name}' marqué comme éligible pour les shifts")
                
                if group.name not in schedule_group_names and group.is_part_of_schedule:
                    group.is_part_of_schedule = False
                    was_updated = True
                    messages.append(f"Groupe '{group.name}' retiré des shifts")
                
                if group.name in oncall_group_names and not group.is_part_of_oncall:
                    group.is_part_of_oncall = True
                    was_updated = True
                    messages.append(f"Groupe '{group.name}' marqué comme éligible pour les astreintes")
                
                if group.name not in oncall_group_names and group.is_part_of_oncall:
                    group.is_part_of_oncall = False
                    was_updated = True
                    messages.append(f"Groupe '{group.name}' retiré des astreintes")
                
                if was_updated:
                    db.session.add(group)
            
            db.session.commit()
            
            if messages:
                return "✅ Synchronisation terminée. " + ", ".join(messages)
            else:
                return "✅ Aucune modification nécessaire, la base est déjà synchronisée."
            
        except Exception as e:
            db.session.rollback()
            return f"❌ Erreur lors de la synchronisation: {str(e)}"


class ConfigValidator:
    """Classe pour valider la configuration avant sauvegarde."""
    
    @staticmethod
    def validate_oncall_config(config: Dict[str, Any]) -> List[str]:
        """Valide la configuration des astreintes."""
        errors = []
        oncall_config = config.get('oncall', {})
        
        # Vérifier start_day
        start_day = oncall_config.get('start_day')
        if start_day is not None and (start_day < 0 or start_day > 6):
            errors.append("start_day doit être entre 0 (lundi) et 6 (dimanche)")
        
        # Vérifier start_hour
        start_hour = oncall_config.get('start_hour')
        if start_hour is not None and (start_hour < 0 or start_hour > 23):
            errors.append("start_hour doit être entre 0 et 23")
        
        # Vérifier end_day
        end_day = oncall_config.get('end_day')
        if end_day is not None and (end_day < 0 or end_day > 6):
            errors.append("end_day doit être entre 0 (lundi) et 6 (dimanche)")
        
        # Vérifier end_hour
        end_hour = oncall_config.get('end_hour')
        if end_hour is not None and (end_hour < 0 or end_hour > 23):
            errors.append("end_hour doit être entre 0 et 23")
        
        # Vérifier min_days_between_oncalls
        min_days = oncall_config.get('min_days_between_oncalls')
        if min_days is not None and min_days < 0:
            errors.append("min_days_between_oncalls doit être positif")
        
        return errors
    
    @staticmethod
    def validate_shift_config(config: Dict[str, Any]) -> List[str]:
        """Valide la configuration des shifts."""
        errors = []
        shift_config = config.get('shifts', {})
        
        # Vérifier shift_types
        shift_types = shift_config.get('shift_types', [])
        for i, st in enumerate(shift_types):
            if st.get('start') is not None and (st.get('start') < 0 or st.get('start') > 23):
                errors.append(f"shift_types[{i}].start doit être entre 0 et 23")
            if st.get('end') is not None and (st.get('end') < 0 or st.get('end') > 23):
                errors.append(f"shift_types[{i}].end doit être entre 0 et 23")
            if st.get('start') is not None and st.get('end') is not None:
                if st.get('start') >= st.get('end'):
                    errors.append(f"shift_types[{i}].start doit être < end")
        
        # Vérifier work_days
        work_days = shift_config.get('work_days', [])
        for day in work_days:
            if day < 0 or day > 6:
                errors.append(f"work_days contient une valeur invalide: {day}")
        
        return errors
    
    @staticmethod
    def validate_groups_config(config: Dict[str, Any]) -> List[str]:
        """Valide la configuration des groupes."""
        errors = []
        groups_config = config.get('groups', {})
        
        # Vérifier que les groupes existent en base (optionnel, pour validation avancée)
        schedule_groups = groups_config.get('schedule_groups', [])
        oncall_groups = groups_config.get('oncall_groups', [])
        
        # Pour l'instant, on ne valide pas l'existence des groupes
        # (car ils peuvent être créés plus tard)
        
        return errors
    
    @staticmethod
    def validate_generation_config(config: Dict[str, Any]) -> List[str]:
        """Valide la configuration de génération."""
        errors = []
        gen_config = config.get('generation', {})
        
        default_period = gen_config.get('default_period_days')
        if default_period is not None and default_period <= 0:
            errors.append("default_period_days doit être positif")
        
        return errors
    
    @staticmethod
    def validate_all(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valide toute la configuration."""
        all_errors = []
        
        all_errors.extend(ConfigValidator.validate_oncall_config(config))
        all_errors.extend(ConfigValidator.validate_shift_config(config))
        all_errors.extend(ConfigValidator.validate_groups_config(config))
        all_errors.extend(ConfigValidator.validate_generation_config(config))
        
        return (len(all_errors) == 0, all_errors)



