"""
OnCall automation utilities for Leviia Schedule.

This module provides automation functionality for on-call duties.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from app.models import User, Group, OnCall, Leave


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
    def check_oncall_constraint(user: User, start_time: datetime) -> bool:
        """
        Vérifie la contrainte légale d'espacement minimal (2 semaines) entre deux
        astreintes consécutives pour un même utilisateur.

        Args:
            user: Utilisateur à vérifier
            start_time: Début de la nouvelle astreinte envisagée

        Returns:
            True si aucune astreinte précédente ou si l'espacement est suffisant.
        """
        last_oncall = (
            OnCall.query.filter(OnCall.user_id == user.id)
            .order_by(OnCall.end_time.desc())
            .first()
        )
        if not last_oncall:
            return True

        gap_days = (start_time - last_oncall.end_time).days
        return gap_days / 7 >= 2

    @staticmethod
    def find_next_available_user(
        users: List[User], start_time: datetime, end_time: datetime
    ) -> Optional[User]:
        """
        Trouve le premier utilisateur de la liste disponible pour la période donnée
        (pas de congé, pas d'astreinte chevauchante, contrainte légale respectée).

        Args:
            users: Liste ordonnée d'utilisateurs candidats
            start_time: Début de la période d'astreinte
            end_time: Fin de la période d'astreinte

        Returns:
            Le premier utilisateur disponible, ou None si aucun ne l'est.
        """
        for user in users:
            has_oncall_conflict = (
                OnCall.query.filter(
                    OnCall.user_id == user.id,
                    OnCall.start_time < end_time,
                    OnCall.end_time > start_time,
                ).first()
                is not None
            )
            if has_oncall_conflict:
                continue

            has_leave_conflict = (
                Leave.query.filter(
                    Leave.user_id == user.id,
                    Leave.start_date <= end_time.date(),
                    Leave.end_date >= start_time.date(),
                ).first()
                is not None
            )
            if has_leave_conflict:
                continue

            if not OnCallAutomation.check_oncall_constraint(user, start_time):
                continue

            return user

        return None

    @staticmethod
    def generate_oncall_schedule(start_date, end_date, rotation_order_ids: Optional[List[int]] = None, dry_run: bool = True):
        """
        Génère un planning d'astreintes pour une période donnée.

        Les astreintes commencent le vendredi à 21h et se terminent le vendredi
        suivant à 07h. Les utilisateurs sont assignés selon l'ordre de rotation,
        en respectant les congés, les astreintes existantes et l'espacement légal
        de 2 semaines minimum. Si aucun utilisateur ne respecte toutes ces règles,
        un utilisateur sans conflit de congé/astreinte est assigné malgré tout
        (contrainte légale ignorée en dernier recours).

        Args:
            start_date: Date de début
            end_date: Date de fin
            rotation_order_ids: Ordre de rotation personnalisé
            dry_run: Si True, ne sauvegarde rien en base

        Returns:
            Tuple: (liste des astreintes générées (objets OnCall), messages de log)
        """
        from app import db

        eligible_users = OnCallAutomation.get_eligible_users()
        if not eligible_users:
            return [], ["Aucun utilisateur éligible pour les astreintes."]

        rotation_order = OnCallAutomation.get_rotation_order(rotation_order_ids)
        if not rotation_order:
            return [], ["Impossible de déterminer l'ordre de rotation."]

        days_ahead = (4 - start_date.weekday()) % 7
        current_friday = start_date + timedelta(days=days_ahead)

        oncalls = []
        messages = []
        rotation_index = 0

        while current_friday < end_date:
            start_time = datetime.combine(current_friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)

            ordered_candidates = rotation_order[rotation_index:] + rotation_order[:rotation_index]
            assigned_user = OnCallAutomation.find_next_available_user(
                ordered_candidates, start_time, end_time
            )

            if assigned_user is None:
                # Dernier recours : ignorer la contrainte légale des 2 semaines,
                # mais toujours respecter congés et astreintes existantes.
                for user in ordered_candidates:
                    has_conflict = (
                        OnCall.query.filter(
                            OnCall.user_id == user.id,
                            OnCall.start_time < end_time,
                            OnCall.end_time > start_time,
                        ).first()
                        is not None
                    )
                    has_leave = (
                        Leave.query.filter(
                            Leave.user_id == user.id,
                            Leave.start_date <= end_time.date(),
                            Leave.end_date >= start_time.date(),
                        ).first()
                        is not None
                    )
                    if not has_conflict and not has_leave:
                        assigned_user = user
                        messages.append(
                            f"Utilisateur avec contrainte légale seulement : {user.name} pour le {current_friday.strftime('%d/%m/%Y')}."
                        )
                        break

            if assigned_user is None:
                messages.append(
                    f"Aucun utilisateur disponible pour l'astreinte du {current_friday.strftime('%d/%m/%Y')}."
                )
                current_friday += timedelta(days=7)
                continue

            oncall = OnCall(
                user_id=assigned_user.id,
                start_time=start_time,
                end_time=end_time,
            )
            oncalls.append(oncall)
            if not dry_run:
                db.session.add(oncall)

            rotation_index = (rotation_order.index(assigned_user) + 1) % len(rotation_order)
            current_friday += timedelta(days=7)

        if not dry_run and oncalls:
            db.session.commit()

        messages.append(f"Généré {len(oncalls)} astreintes.")
        return oncalls, messages
