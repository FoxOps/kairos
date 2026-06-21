# =============================================================================
# CLASSE DE BASE POUR L'AUTOMATISATION
# =============================================================================
"""
Module contenant les classes et méthodes de base communes à toutes les classes
d'automatisation (OnCallAutomation, ShiftAutomation, AdvancedShiftAutomation).

Ce module vise à éliminer la duplication de code et à fournir une base commune
pour toutes les opérations d'automatisation.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any
from app import db
from app.models import User, Group, Leave, OnCall, Shift
from app.config.automation_rules import AutomationConfig
import logging

# Configuration du logger
logger = logging.getLogger(__name__)


class BaseAutomation:
    """
    Classe de base pour toutes les opérations d'automatisation.
    
    Cette classe fournit des méthodes communes pour :
    - Récupérer les utilisateurs éligibles
    - Vérifier les disponibilités (congés, astreintes existantes)
    - Gérer les conflits
    """
    
    @staticmethod
    def get_users_by_group_names(group_names: List[str]) -> List[User]:
        """
        Récupère les utilisateurs appartenant à des groupes spécifiques.
        
        Args:
            group_names: Liste des noms de groupes
            
        Returns:
            Liste des utilisateurs appartenant à ces groupes
        """
        if not group_names:
            logger.warning("Aucun nom de groupe fourni, retourne une liste vide")
            return []
        
        try:
            users = (
                User.query
                .join(Group)
                .filter(Group.name.in_(group_names))
                .order_by(User.name)
                .all()
            )
            logger.debug(f"Récupérés {len(users)} utilisateurs pour les groupes: {group_names}")
            return users
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs par groupes: {str(e)}")
            return []
    
    @staticmethod
    def get_eligible_users_for_oncall() -> List[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les astreintes.
        Un utilisateur est éligible s'il appartient à un groupe participant aux astreintes.
        
        Returns:
            Liste des utilisateurs éligibles pour les astreintes
        """
        oncall_group_names = AutomationConfig.get_oncall_group_names()
        return BaseAutomation.get_users_by_group_names(oncall_group_names)
    
    @staticmethod
    def get_eligible_users_for_shifts() -> List[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les shifts.
        Un utilisateur est éligible s'il appartient à un groupe participant au schedule.
        
        Returns:
            Liste des utilisateurs éligibles pour les shifts
        """
        schedule_group_names = AutomationConfig.get_schedule_group_names()
        return BaseAutomation.get_users_by_group_names(schedule_group_names)
    
    @staticmethod
    def get_available_users_for_date(date: date, group_names: Optional[List[str]] = None) -> List[User]:
        """
        Récupère les utilisateurs disponibles pour une date donnée (pas en congé).
        
        Args:
            date: Date à vérifier
            group_names: Liste optionnelle de noms de groupes pour filtrer les utilisateurs
            
        Returns:
            Liste des utilisateurs disponibles pour la date
        """
        # Récupérer les utilisateurs éligibles
        if group_names:
            eligible_users = BaseAutomation.get_users_by_group_names(group_names)
        else:
            # Par défaut, utiliser tous les utilisateurs
            eligible_users = User.query.order_by(User.name).all()
        
        available_users = []
        for user in eligible_users:
            # Vérifier si l'utilisateur est en congé
            has_leave = db.session.query(
                db.exists().where(
                    Leave.user_id == user.id,
                    Leave.start_date <= date,
                    Leave.end_date >= date,
                )
            ).scalar()
            
            if not has_leave:
                available_users.append(user)
        
        logger.debug(f"Trouvés {len(available_users)} utilisateurs disponibles pour le {date}")
        return available_users
    
    @staticmethod
    def user_has_oncall_on_date(user_id: int, date: date) -> bool:
        """
        Vérifie si un utilisateur a une astreinte à une date donnée.
        
        Args:
            user_id: ID de l'utilisateur
            date: Date à vérifier
            
        Returns:
            True si l'utilisateur a une astreinte à cette date, False sinon
        """
        has_oncall = db.session.query(
            db.exists().where(
                OnCall.user_id == user_id,
                OnCall.start_time <= datetime.combine(date, datetime.max.time()),
                OnCall.end_time >= datetime.combine(date, datetime.min.time()),
            )
        ).scalar()
        
        return bool(has_oncall)
    
    @staticmethod
    def user_has_shift_on_date(user_id: int, date: date) -> bool:
        """
        Vérifie si un utilisateur a un shift à une date donnée.
        
        Args:
            user_id: ID de l'utilisateur
            date: Date à vérifier
            
        Returns:
            True si l'utilisateur a un shift à cette date, False sinon
        """
        has_shift = db.session.query(
            db.exists().where(
                Shift.user_id == user_id,
                Shift.date == date,
            )
        ).scalar()
        
        return bool(has_shift)
    
    @staticmethod
    def can_assign_oncall(user_id: int, start_time: datetime, end_time: datetime) -> Tuple[bool, str]:
        """
        Vérifie si une astreinte peut être assignée à un utilisateur à une période donnée.
        
        Args:
            user_id: ID de l'utilisateur
            start_time: Date/heure de début de l'astreinte
            end_time: Date/heure de fin de l'astreinte
            
        Returns:
            Tuple (bool, message) où bool indique si l'assignation est possible
        """
        # Vérifier les astreintes existantes qui chevauchent
        has_conflict = db.session.query(
            db.exists().where(
                OnCall.user_id == user_id,
                OnCall.start_time < end_time,
                OnCall.end_time > start_time,
            )
        ).scalar()
        
        if has_conflict:
            return False, "L'utilisateur a déjà une astreinte qui chevauche cette période."
        
        # Vérifier les congés qui chevauchent
        start_date = start_time.date()
        end_date = end_time.date()
        
        has_leave = db.session.query(
            db.exists().where(
                Leave.user_id == user_id,
                Leave.start_date <= end_date,
                Leave.end_date >= start_date,
            )
        ).scalar()
        
        if has_leave:
            return False, "L'utilisateur est en congé pendant cette période."
        
        # Vérifier la contrainte légale (minimum de jours entre deux astreintes)
        min_days = AutomationConfig.get_min_days_between_oncalls()
        
        last_oncall = OnCall.query.filter_by(user_id=user_id).order_by(OnCall.start_time.desc()).first()
        if last_oncall:
            days_between = (start_time - last_oncall.end_time).days
            if days_between < min_days:
                return False, f"Contrainte légale : il doit y avoir au moins {min_days} jours entre deux astreintes."
        
        return True, ""
    
    @staticmethod
    def can_assign_shift(user_id: int, date: date, shift_type_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Vérifie si un shift peut être assigné à un utilisateur à une date donnée.
        
        Args:
            user_id: ID de l'utilisateur
            date: Date du shift
            shift_type_name: Nom optionnel du type de shift (pour validation future)
            
        Returns:
            Tuple (bool, message) où bool indique si l'assignation est possible
        """
        # Vérifier que la date est un jour de travail
        work_days = AutomationConfig.get_work_days()
        if date.weekday() not in work_days:
            return False, "Les shifts ne peuvent être assignés que les jours de travail configurés."
        
        # Vérifier si l'utilisateur a déjà un shift ce jour-là
        if BaseAutomation.user_has_shift_on_date(user_id, date):
            return False, "L'utilisateur a déjà un shift ce jour-là."
        
        # Vérifier si l'utilisateur est en congé
        has_leave = db.session.query(
            db.exists().where(
                Leave.user_id == user_id,
                Leave.start_date <= date,
                Leave.end_date >= date,
            )
        ).scalar()
        
        if has_leave:
            return False, "L'utilisateur est en congé à cette date."
        
        # Vérifier si l'utilisateur a une astreinte qui chevauche
        if BaseAutomation.user_has_oncall_on_date(user_id, date):
            return False, "L'utilisateur a une astreinte à cette date."
        
        return True, ""
    
    @staticmethod
    def find_next_available_user(
        user_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        for_oncall: bool = True
    ) -> Optional[User]:
        """
        Trouve le prochain utilisateur disponible dans une liste d'IDs.
        
        Args:
            user_ids: Liste des IDs d'utilisateurs dans l'ordre de préférence
            start_time: Date/heure de début de la période
            end_time: Date/heure de fin de la période
            for_oncall: Si True, vérifie pour une astreinte, sinon pour un shift
            
        Returns:
            Le premier utilisateur disponible, ou None si aucun n'est disponible
        """
        for user_id in user_ids:
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"Utilisateur ID {user_id} introuvable")
                continue
            
            if for_oncall:
                can_assign, _ = BaseAutomation.can_assign_oncall(user_id, start_time, end_time)
            else:
                # Pour les shifts, vérifier chaque jour de la période
                can_assign = True
                current_date = start_time.date()
                while current_date <= end_time.date():
                    shift_can_assign, _ = BaseAutomation.can_assign_shift(user_id, current_date)
                    if not shift_can_assign:
                        can_assign = False
                        break
                    current_date += timedelta(days=1)
            
            if can_assign:
                logger.debug(f"Utilisateur {user.name} (ID: {user_id}) disponible pour la période")
                return user
        
        logger.warning("Aucun utilisateur disponible trouvé")
        return None
    
    @staticmethod
    def get_work_days() -> List[int]:
        """
        Récupère les jours de travail configurés.
        
        Returns:
            Liste des jours de travail (0=lundi, 6=dimanche)
        """
        return AutomationConfig.get_work_days()
    
    @staticmethod
    def get_min_days_between_oncalls() -> int:
        """
        Récupère le nombre minimum de jours entre deux astreintes.
        
        Returns:
            Nombre minimum de jours
        """
        return AutomationConfig.get_min_days_between_oncalls()
