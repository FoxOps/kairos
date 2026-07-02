"""
OnCall automation utilities for Leviia Schedule.

This module provides automation functionality for on-call duties.
"""

from typing import List, Optional
from app.models import User, Group


class OnCallAutomation:
    """
    Classe pour gérer l'automatisation des astreintes (On-Call).
    
    Fonctionnalités :
    - Génération automatique des astreintes avec rotation
    - Gestion des remplacements en cas de conflit
    - Configuration de l'ordre de rotation
    """
    
    @staticmethod
    def get_eligible_users() -> List[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les astreintes.
        Un utilisateur est éligible s'il appartient à un groupe participant aux astreintes.
        """
        return (
            User.query
            .join(Group)
            .filter(Group.is_part_of_oncall == True)
            .order_by(User.name)
            .all()
        )
    
    @staticmethod
    def get_rotation_order(rotation_order_ids: Optional[List[int]] = None) -> List[User]:
        """
        Récupère l'ordre de rotation des utilisateurs.
        
        Args:
            rotation_order_ids: Liste optionnelle d'IDs d'utilisateurs dans l'ordre souhaité.
                              Si None, utilise l'ordre alphabétique.
        
        Returns:
            Liste des utilisateurs dans l'ordre de rotation.
        """
        eligible_users = OnCallAutomation.get_eligible_users()
        
        if not eligible_users:
            return []
        
        # Si un ordre personnalisé est fourni
        if rotation_order_ids:
            # Créer un mapping id -> user pour un accès rapide
            user_map = {user.id: user for user in eligible_users}
            
            # Construire la liste dans l'ordre spécifié
            ordered_users = []
            for user_id in rotation_order_ids:
                if user_id in user_map:
                    ordered_users.append(user_map[user_id])
            
            # Ajouter les utilisateurs restants (qui n'étaient pas dans rotation_order_ids)
            remaining_users = [u for u in eligible_users if u.id not in rotation_order_ids]
            ordered_users.extend(remaining_users)
            
            return ordered_users
        
        # Sinon, retourner dans l'ordre alphabétique
        return eligible_users
    
    @staticmethod
    def generate_oncall_schedule(start_date, end_date, rotation_order_ids: Optional[List[int]] = None):
        """
        Génère un planning d'astreintes pour une période donnée.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            rotation_order_ids: Ordre de rotation personnalisé
            
        Returns:
            Tuple: (liste des astreintes générées, messages de log)
        """
        from datetime import datetime, timedelta
        from app.models import OnCall
        
        eligible_users = OnCallAutomation.get_eligible_users()
        if not eligible_users:
            return [], ["Aucun utilisateur éligible pour les astreintes."]
        
        rotation_order = OnCallAutomation.get_rotation_order(rotation_order_ids)
        if not rotation_order:
            return [], ["Impossible de déterminer l'ordre de rotation."]
        
        # Générer les astreintes
        oncalls = []
        messages = []
        current_date = start_date
        user_index = 0
        
        while current_date < end_date:
            user = rotation_order[user_index % len(rotation_order)]
            
            # Créer une astreinte pour ce jour
            oncall_data = {
                'user_id': user.id,
                'start_time': datetime.combine(current_date, datetime.min.time()),
                'end_time': datetime.combine(current_date + timedelta(days=1), datetime.min.time())
            }
            oncalls.append(oncall_data)
            
            user_index += 1
            current_date += timedelta(days=1)
        
        messages.append(f"Généré {len(oncalls)} astreintes pour {len(rotation_order)} utilisateurs.")
        return oncalls, messages
