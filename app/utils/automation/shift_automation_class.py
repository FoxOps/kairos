"""
Shift automation class for Leviia Schedule.

This module provides the ShiftAutomation class for shift management.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta, date
from app.models import User, Group, ShiftType, Shift


class ShiftAutomation:
    """
    Classe pour gérer l'automatisation des shifts.
    
    Fonctionnalités :
    - Génération automatique des shifts
    - Gestion des types de shifts
    - Rééquilibrage des shifts après modification
    """
    
    @staticmethod
    def get_eligible_users() -> List[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les shifts.
        Un utilisateur est éligible s'il appartient à un groupe participant au schedule.
        """
        return (
            User.query
            .join(Group)
            .filter(Group.is_part_of_schedule == True)
            .order_by(User.name)
            .all()
        )
    
    @staticmethod
    def get_shift_types() -> List[ShiftType]:
        """Récupère la liste des types de shifts."""
        return ShiftType.query.order_by(ShiftType.start_hour).all()
    
    @staticmethod
    def generate_shift_schedule(start_date: date, end_date: date, 
                               shift_types: Optional[List[ShiftType]] = None,
                               users: Optional[List[User]] = None) -> Tuple[List[dict], List[str]]:
        """
        Génère un planning de shifts pour une période donnée.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            shift_types: Liste des types de shifts à utiliser
            users: Liste des utilisateurs à inclure
            
        Returns:
            Tuple: (liste des shifts générés, messages de log)
        """
        if users is None:
            users = ShiftAutomation.get_eligible_users()
        
        if not users:
            return [], ["Aucun utilisateur éligible pour les shifts."]
        
        if shift_types is None:
            shift_types = ShiftAutomation.get_shift_types()
        
        if not shift_types:
            return [], ["Aucun type de shift disponible."]
        
        shifts = []
        messages = []
        current_date = start_date
        user_index = 0
        
        while current_date < end_date:
            user = users[user_index % len(users)]
            shift_type = shift_types[0]  # Utiliser le premier type de shift par défaut
            
            # Créer un shift pour ce jour
            shift_data = {
                'user_id': user.id,
                'shift_type_id': shift_type.id,
                'date': current_date,
                'start_time': datetime.combine(current_date, datetime.min.time()),
                'end_time': datetime.combine(current_date, datetime.max.time())
            }
            shifts.append(shift_data)
            
            user_index += 1
            current_date += timedelta(days=1)
        
        messages.append(f"Généré {len(shifts)} shifts pour {len(users)} utilisateurs.")
        return shifts, messages
