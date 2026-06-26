"""
Module d'automatisation pour la génération des astreintes et des shifts.

Ce module fournit des fonctionnalités pour :
1. Générer automatiquement des astreintes avec rotation entre les membres éligibles
2. Générer automatiquement des shifts selon des règles métiers
3. Gérer les remplacements automatiques en cas de conflits
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple, Dict, Any
from app import db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType


# ============================================================================
# CONFIGURATION DES RÈGLES MÉTIERS
# ============================================================================

class BusinessRules:
    """
    Classe pour gérer les règles métiers spécifiques pour la génération des shifts.
    
    Ces règles peuvent être personnalisées selon les besoins de l'organisation.
    """
    
    @staticmethod
    def get_shift_rules() -> Dict[str, Any]:
        """
        Retourne les règles métiers pour la génération des shifts.
        
        Structure attendue :
        {
            'weekly_patterns': {
                'user_id': {
                    'monday': ['morning', 'afternoon', 'evening'],
                    'tuesday': [...],
                    ...
                }
            },
            'daily_requirements': {
                'monday': {'morning': 2, 'afternoon': 2, 'evening': 1},
                ...
            },
            'max_shifts_per_user_per_week': 5,
            'min_shifts_per_user_per_week': 2,
        }
        """
        # Exemple de règles par défaut - à personnaliser
        return {
            'weekly_patterns': {},  # Vide par défaut, à remplir via configuration
            'daily_requirements': {
                'monday': {'morning': 1, 'afternoon': 1, 'evening': 0},
                'tuesday': {'morning': 1, 'afternoon': 1, 'evening': 0},
                'wednesday': {'morning': 1, 'afternoon': 1, 'evening': 0},
                'thursday': {'morning': 1, 'afternoon': 1, 'evening': 0},
                'friday': {'morning': 1, 'afternoon': 1, 'evening': 0},
                'saturday': {},
                'sunday': {},
            },
            'max_shifts_per_user_per_week': 5,
            'min_shifts_per_user_per_week': 2,
        }
    
    @staticmethod
    def get_oncall_rules() -> Dict[str, Any]:
        """
        Retourne les règles métiers pour la génération des astreintes.
        
        Structure attendue :
        {
            'rotation_order': [user_id_1, user_id_2, ...],  # Ordre de rotation
            'start_day': 'friday',  # Jour de début (friday pour vendredi 21h)
            'start_hour': 21,  # Heure de début
            'duration_days': 7,  # Durée en jours
            'end_hour': 7,  # Heure de fin (le vendredi suivant)
        }
        """
        return {
            'rotation_order': [],  # À remplir via configuration
            'start_day': 'friday',
            'start_hour': 21,
            'duration_days': 7,
            'end_hour': 7,
        }


# ============================================================================
# GÉNÉRATION DES ASTREINTES
# ============================================================================

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
            
            # Ajouter les utilisateurs restants qui ne sont pas dans la liste
            remaining_users = [u for u in eligible_users if u.id not in rotation_order_ids]
            ordered_users.extend(sorted(remaining_users, key=lambda u: u.name))
            
            return ordered_users
        
        # Par défaut, trier par nom
        return sorted(eligible_users, key=lambda u: u.name)
    
    @staticmethod
    def check_oncall_constraint(user: User, start_time: datetime) -> bool:
        """
        Vérifie la contrainte légale : pas 2 astreintes de suite.
        Il doit y avoir au moins 2 semaines sans astreinte entre deux astreintes.
        
        Args:
            user: Utilisateur à vérifier
            start_time: Date/heure de début de l'astreinte potentielle
            
        Returns:
            True si l'utilisateur peut avoir une astreinte à cette date, False sinon
        """
        # Trouver la dernière astreinte de l'utilisateur
        last_oncall = OnCall.query.filter_by(user_id=user.id).order_by(OnCall.start_time.desc()).first()
        
        if not last_oncall:
            return True  # Pas d'astreinte précédente, donc OK
        
        # Calculer la différence en semaines
        weeks_between = (start_time - last_oncall.end_time).days / 7
        
        # Il doit y avoir au moins 2 semaines (14 jours) entre la fin de la dernière et le début de la nouvelle
        return weeks_between >= 2
    
    @staticmethod
    def find_next_available_user(
        rotation_order: List[User],
        start_time: datetime,
        end_time: datetime,
        existing_oncalls: Optional[List[OnCall]] = None
    ) -> Optional[User]:
        """
        Trouve le prochain utilisateur disponible dans l'ordre de rotation.
        
        Un utilisateur est disponible s'il n'a pas :
        - Une astreinte qui chevauche la période
        - Un congé qui chevauche la période
        - Une contrainte légale (2 astreintes de suite interdites)
        
        Args:
            rotation_order: Liste des utilisateurs dans l'ordre de rotation
            start_time: Date/heure de début de l'astreinte
            end_time: Date/heure de fin de l'astreinte
            existing_oncalls: Liste des astreintes déjà générées (pour vérifier la contrainte)
        
        Returns:
            Le premier utilisateur disponible, ou None si aucun n'est disponible
        """
        start_date = start_time.date()
        end_date = end_time.date()
        
        if not rotation_order:
            return None
        
        # Optimisation : Récupérer tous les user_ids d'un coup
        user_ids = [user.id for user in rotation_order]
        
        # Récupérer tous les utilisateurs avec des astreintes chevauchantes en une seule requête
        users_with_oncall_conflict = set()
        oncall_conflicts = db.session.query(OnCall.user_id).filter(
            OnCall.user_id.in_(user_ids),
            OnCall.start_time < end_time,
            OnCall.end_time > start_time,
        ).all()
        users_with_oncall_conflict = {oc.user_id for oc in oncall_conflicts}
        
        # Ajouter les conflits avec les astreintes déjà générées (passées en paramètre)
        if existing_oncalls:
            for oncall in existing_oncalls:
                if oncall.user_id in user_ids:
                    # Vérifier si cette astreinte chevauche la période demandée
                    if oncall.start_time < end_time and oncall.end_time > start_time:
                        users_with_oncall_conflict.add(oncall.user_id)
        
        # Récupérer tous les utilisateurs avec des congés chevauchants en une seule requête
        users_with_leave = set()
        leave_conflicts = db.session.query(Leave.user_id).filter(
            Leave.user_id.in_(user_ids),
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        ).all()
        users_with_leave = {lc.user_id for lc in leave_conflicts}
        
        # Vérifier la contrainte légale pour tous les utilisateurs
        # On récupère la dernière astreinte pour chaque utilisateur (en base + en cours de génération)
        last_oncall_map = {}
        
        # D'abord, les astreintes existantes en base
        db_last_oncalls = db.session.query(
            OnCall.user_id,
            OnCall.end_time
        ).filter(
            OnCall.user_id.in_(user_ids)
        ).order_by(
            OnCall.user_id,
            OnCall.end_time.desc()
        ).all()
        
        for user_id, end_time in db_last_oncalls:
            if user_id not in last_oncall_map:
                last_oncall_map[user_id] = end_time
        
        # Ensuite, prendre en compte les astreintes déjà générées (passées en paramètre)
        if existing_oncalls:
            for oncall in existing_oncalls:
                if oncall.user_id in user_ids:
                    # Garder la plus récente
                    if oncall.user_id not in last_oncall_map or oncall.end_time > last_oncall_map[oncall.user_id]:
                        last_oncall_map[oncall.user_id] = oncall.end_time
        
        # Parcourir les utilisateurs dans l'ordre de rotation
        for user in rotation_order:
            # Vérifier les conflits d'astreinte
            if user.id in users_with_oncall_conflict:
                continue
            
            # Vérifier les congés
            if user.id in users_with_leave:
                continue
            
            # Vérifier la contrainte légale (2 semaines minimum entre les astreintes)
            if user.id in last_oncall_map:
                last_end = last_oncall_map[user.id]
                weeks_between = (start_time - last_end).days / 7
                if weeks_between < 2:
                    continue
            
            return user
        
        return None
    
    @staticmethod
    def generate_oncall_schedule(
        start_date: date,
        end_date: date,
        rotation_order_ids: Optional[List[int]] = None,
        dry_run: bool = False
    ) -> Tuple[List[OnCall], List[str]]:
        """
        Génère automatiquement les astreintes pour une période donnée.
        
        Args:
            start_date: Date de début de la période
            end_date: Date de fin de la période
            rotation_order_ids: Liste optionnelle d'IDs pour l'ordre de rotation
            dry_run: Si True, ne sauvegarde pas en base (mode test)
        
        Returns:
            Tuple contenant :
            - Liste des astreintes générées
            - Liste des messages (succès, avertissements, erreurs)
        """
        messages = []
        generated_oncalls = []
        
        # Récupérer l'ordre de rotation
        rotation_order = OnCallAutomation.get_rotation_order(rotation_order_ids)
        
        if not rotation_order:
            messages.append("⚠️ Aucun utilisateur éligible trouvé pour les astreintes.")
            return [], messages
        
        # Calculer le premier vendredi à partir de start_date
        current_date = start_date
        while current_date.weekday() != 4:  # 4 = vendredi
            current_date += timedelta(days=1)
        
        # Si la date de début est après le premier vendredi, commencer au vendredi suivant
        if current_date < start_date:
            current_date += timedelta(days=7)
        
        # Générer les astreintes
        rotation_index = 0
        while current_date <= end_date:
            # Calculer les dates/heures
            start_time = datetime.combine(current_date, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)  # Vendredi 21h -> Vendredi suivant 07h
            
            # Vérifier que end_time ne dépasse pas la période
            # On inclut les astreintes dont end_time est <= end_date
            if end_time.date() > end_date:
                break
            
            # Trouver un utilisateur disponible
            # Passer les astreintes déjà générées pour vérifier la contrainte des 2 semaines
            user = OnCallAutomation.find_next_available_user(
                rotation_order, start_time, end_time, generated_oncalls
            )
            
            if user:
                # Créer l'astreinte
                oncall = OnCall(
                    user_id=user.id,
                    start_time=start_time,
                    end_time=end_time,
                )
                generated_oncalls.append(oncall)
                
                # Stocker pour le résumé (au lieu de messages détaillés)
                if 'oncall_created' not in locals():
                    oncall_created = []
                oncall_created.append({
                    'user': user.name,
                    'start': start_time.strftime('%d/%m/%Y %Hh'),
                    'end': end_time.strftime('%d/%m/%Y %Hh')
                })
                
                # Passer à l'utilisateur suivant dans la rotation
                rotation_index = (rotation_index + 1) % len(rotation_order)
                # Réorganiser la rotation pour commencer par l'utilisateur suivant
                rotation_order = rotation_order[rotation_index:] + rotation_order[:rotation_index]
            else:
                # Stocker pour le résumé
                if 'oncall_skipped' not in locals():
                    oncall_skipped = []
                oncall_skipped.append(start_time.strftime('%d/%m/%Y %Hh'))
                # Passer à l'utilisateur suivant dans la rotation même sans création
                rotation_index = (rotation_index + 1) % len(rotation_order)
                rotation_order = rotation_order[rotation_index:] + rotation_order[:rotation_index]
            
            # Passer au vendredi suivant
            current_date += timedelta(days=7)
        
        # Sauvegarder en base si ce n'est pas un dry run
        if not dry_run and generated_oncalls:
            try:
                db.session.add_all(generated_oncalls)
                db.session.commit()
                # Générer un résumé
                msg = f"✅ {len(generated_oncalls)} astreintes générées avec succès !"
                if 'oncall_skipped' in locals() and oncall_skipped:
                    msg += f" (⚠️ {len(oncall_skipped)} non créées)"
                messages.append(msg)
            except Exception as e:
                db.session.rollback()
                messages.insert(0, f"❌ Erreur lors de la sauvegarde : {str(e)}")
                return [], messages
        elif not generated_oncalls:
            # Aucun astreinte générée
            if 'oncall_skipped' in locals() and oncall_skipped:
                messages.append(f"⚠️ Aucune astreinte générée ({len(oncall_skipped)} périodes sans utilisateur disponible)")
            else:
                messages.append("⚠️ Aucune astreinte générée")
        else:
            # Dry run avec des astreintes générées
            msg = f"📋 Prévisualisation : {len(generated_oncalls)} astreintes seraient créées"
            if 'oncall_skipped' in locals() and oncall_skipped:
                msg += f" (⚠️ {len(oncall_skipped)} non créées)"
            messages.append(msg)
        
        return generated_oncalls, messages


# ============================================================================
# GÉNÉRATION DES SHIFTS
# ============================================================================

class ShiftAutomation:
    """
    Classe pour gérer l'automatisation des shifts.
    
    Fonctionnalités :
    - Génération automatique des shifts selon des règles métiers
    - Gestion des remplacements en cas de conflit
    - Distribution équilibrée entre les utilisateurs
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
        """Récupère tous les types de shifts disponibles."""
        return ShiftType.query.order_by(ShiftType.name).all()
    
    @staticmethod
    def can_assign_shift(user_id: int, date: date, shift_type: ShiftType) -> Tuple[bool, str]:
        """
        Vérifie si un shift peut être assigné à un utilisateur à une date donnée.
        
        Args:
            user_id: ID de l'utilisateur
            date: Date du shift
            shift_type: Type de shift
        
        Returns:
            Tuple (bool, message) où bool indique si l'assignation est possible
        """
        # Vérifier que la date est un jour de semaine (lundi-vendredi)
        if date.weekday() >= 5:
            return False, "Les shifts ne peuvent être assignés que du lundi au vendredi."
        
        # Vérifier si l'utilisateur a déjà un shift ce jour-là
        # Utilisation de exists() pour une vérification rapide
        has_shift = db.session.query(
            db.exists().where(
                Shift.user_id == user_id,
                Shift.date == date,
            )
        ).scalar()
        
        if has_shift:
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
        # (on considère qu'une astreinte couvre toute la journée)
        has_oncall = db.session.query(
            db.exists().where(
                OnCall.user_id == user_id,
                OnCall.start_time <= datetime.combine(date, datetime.max.time()),
                OnCall.end_time >= datetime.combine(date, datetime.min.time()),
            )
        ).scalar()
        
        if has_oncall:
            return False, "L'utilisateur a une astreinte à cette date."
        
        return True, ""
    
    @staticmethod
    def find_replacement_user(
        excluded_user_ids: List[int],
        date: date,
        shift_type: ShiftType
    ) -> Optional[User]:
        """
        Trouve un utilisateur de remplacement pour un shift.
        
        Args:
            excluded_user_ids: Liste des IDs d'utilisateurs à exclure
            date: Date du shift
            shift_type: Type de shift
        
        Returns:
            Le premier utilisateur disponible, ou None si aucun n'est disponible
        """
        eligible_users = ShiftAutomation.get_eligible_users()
        
        # Si pas d'utilisateurs éligibles, retourner None
        if not eligible_users:
            return None
        
        # Filtrer les utilisateurs exclus
        candidate_ids = [user.id for user in eligible_users if user.id not in excluded_user_ids]
        
        if not candidate_ids:
            return None
        
        # Vérifier que la date est un jour de semaine
        if date.weekday() >= 5:
            return None
        
        # Récupérer tous les utilisateurs qui ont déjà un shift ce jour-là
        users_with_shift = set()
        shifts = db.session.query(Shift.user_id).filter(
            Shift.user_id.in_(candidate_ids),
            Shift.date == date
        ).all()
        users_with_shift = {s.user_id for s in shifts}
        
        # Récupérer tous les utilisateurs en congé ce jour-là
        users_on_leave = set()
        leaves = db.session.query(Leave.user_id).filter(
            Leave.user_id.in_(candidate_ids),
            Leave.start_date <= date,
            Leave.end_date >= date
        ).all()
        users_on_leave = {l.user_id for l in leaves}
        
        # Récupérer tous les utilisateurs avec une astreinte ce jour-là
        users_with_oncall = set()
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())
        oncalls = db.session.query(OnCall.user_id).filter(
            OnCall.user_id.in_(candidate_ids),
            OnCall.start_time <= day_end,
            OnCall.end_time >= day_start
        ).all()
        users_with_oncall = {o.user_id for o in oncalls}
        
        # Trouver le premier utilisateur disponible
        for user in eligible_users:
            if user.id in excluded_user_ids:
                continue
            if user.id in users_with_shift:
                continue
            if user.id in users_on_leave:
                continue
            if user.id in users_with_oncall:
                continue
            return user
        
        return None
    
    @staticmethod
    def generate_shift_schedule(
        start_date: date,
        end_date: date,
        rules: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Tuple[List[Shift], List[str]]:
        """
        Génère automatiquement les shifts pour une période donnée selon des règles métiers.
        
        Args:
            start_date: Date de début de la période
            end_date: Date de fin de la période
            rules: Règles métiers spécifiques (optionnel)
            dry_run: Si True, ne sauvegarde pas en base (mode test)
        
        Returns:
            Tuple contenant :
            - Liste des shifts générés
            - Liste des messages (succès, avertissements, erreurs)
        """
        messages = []
        generated_shifts = []
        
        # Utiliser les règles par défaut si aucune n'est fournie
        if rules is None:
            rules = BusinessRules.get_shift_rules()
        
        # Récupérer les types de shifts
        shift_types = ShiftAutomation.get_shift_types()
        shift_type_map = {st.name: st for st in shift_types}
        
        # Récupérer les utilisateurs éligibles
        eligible_users = ShiftAutomation.get_eligible_users()
        
        if not eligible_users:
            messages.append("⚠️ Aucun utilisateur éligible trouvé pour les shifts.")
            return [], messages
        
        if not shift_types:
            messages.append("⚠️ Aucun type de shift disponible.")
            return [], messages
        
        # Parcourir chaque jour de la période
        current_date = start_date
        while current_date <= end_date:
            # Ne générer que pour les jours de semaine
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Récupérer les exigences pour ce jour
            day_name = current_date.strftime('%A').lower()
            day_requirements = rules.get('daily_requirements', {}).get(day_name, {})
            
            # Pour chaque type de shift requis
            for shift_type_name, count in day_requirements.items():
                if shift_type_name not in shift_type_map:
                    messages.append(
                        f"⚠️ Type de shift '{shift_type_name}' non trouvé. Ignoré pour le {current_date.strftime('%d/%m/%Y')}."
                    )
                    continue
                
                shift_type = shift_type_map[shift_type_name]
                
                # Générer 'count' shifts de ce type pour ce jour
                for _ in range(count):
                    # Trouver un utilisateur disponible
                    assigned = False
                    
                    # Essayer d'assigner selon les patterns utilisateurs
                    for user in eligible_users:
                        can_assign, error_msg = ShiftAutomation.can_assign_shift(
                            user.id, current_date, shift_type
                        )
                        
                        if can_assign:
                            # Créer le shift
                            start_time = datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.start_hour)
                            end_time = datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.end_hour)
                            
                            shift = Shift(
                                user_id=user.id,
                                shift_type_id=shift_type.id,
                                start_time=start_time,
                                end_time=end_time,
                                date=current_date,
                            )
                            generated_shifts.append(shift)
                            
                            # Stocker pour résumé
                            if 'shifts_created' not in locals():
                                shifts_created = []
                            shifts_created.append({
                                'type': shift_type.label,
                                'user': user.name,
                                'date': current_date.strftime('%d/%m/%Y')
                            })
                            assigned = True
                            break
                    
                    # Si aucun utilisateur n'est disponible, essayer de trouver un remplaçant
                    if not assigned:
                        # Collecter les IDs des utilisateurs qui ont déjà un shift ce jour
                        users_with_shift = [
                            s.user_id for s in Shift.query
                            .filter(Shift.date == current_date)
                            .all()
                        ]
                        
                        replacement = ShiftAutomation.find_replacement_user(
                            users_with_shift, current_date, shift_type
                        )
                        
                        if replacement:
                            start_time = datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.start_hour)
                            end_time = datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.end_hour)
                            
                            shift = Shift(
                                user_id=replacement.id,
                                shift_type_id=shift_type.id,
                                start_time=start_time,
                                end_time=end_time,
                                date=current_date,
                            )
                            generated_shifts.append(shift)
                            
                            # Stocker pour résumé
                            if 'shifts_created' not in locals():
                                shifts_created = []
                            shifts_created.append({
                                'type': shift_type.label,
                                'user': replacement.name,
                                'date': current_date.strftime('%d/%m/%Y')
                            })
                        else:
                            # Stocker pour résumé
                            if 'shifts_skipped' not in locals():
                                shifts_skipped = []
                            shifts_skipped.append({
                                'type': shift_type.label,
                                'date': current_date.strftime('%d/%m/%Y')
                            })
            
            current_date += timedelta(days=1)
        
        # Sauvegarder en base si ce n'est pas un dry run
        if not dry_run and generated_shifts:
            try:
                db.session.add_all(generated_shifts)
                db.session.commit()
                # Générer un résumé
                msg = f"✅ {len(generated_shifts)} shifts générés avec succès !"
                if 'shifts_skipped' in locals() and shifts_skipped:
                    msg += f" (⚠️ {len(shifts_skipped)} non créés)"
                messages.append(msg)
            except Exception as e:
                db.session.rollback()
                messages.insert(0, f"❌ Erreur lors de la sauvegarde : {str(e)}")
                return [], messages
        elif not generated_shifts:
            # Aucun shift généré
            if 'shifts_skipped' in locals() and shifts_skipped:
                messages.append(f"⚠️ Aucun shift généré ({len(shifts_skipped)} besoins non satisfaits)")
            else:
                messages.append("⚠️ Aucun shift généré")
        else:
            # Dry run avec des shifts générés
            msg = f"📋 Prévisualisation : {len(generated_shifts)} shifts seraient créés"
            if 'shifts_skipped' in locals() and shifts_skipped:
                msg += f" (⚠️ {len(shifts_skipped)} non créés)"
            messages.append(msg)
        
        return generated_shifts, messages


# ============================================================================
# FONCTIONS UTILITAIRES POUR L'AUTOMATISATION COMPLÈTE
# ============================================================================

def generate_full_schedule(
    start_date: date,
    end_date: date,
    oncall_rotation_order: Optional[List[int]] = None,
    shift_rules: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
    use_advanced_rules: bool = True
) -> Dict[str, Any]:
    """
    Génère un schedule complet (astreintes + shifts) pour une période donnée.
    
    Args:
        start_date: Date de début de la période
        end_date: Date de fin de la période
        oncall_rotation_order: Ordre de rotation pour les astreintes
        shift_rules: Règles métiers pour les shifts (ignoré si use_advanced_rules=True)
        dry_run: Si True, ne sauvegarde pas en base
        use_advanced_rules: Si True, utilise AdvancedShiftAutomation avec les nouvelles règles
    
    Returns:
        Dictionnaire contenant les résultats et messages
    """
    result = {
        'oncall': {'generated': [], 'messages': []},
        'shift': {'generated': [], 'messages': []},
        'summary': []
    }
    
    # Générer les astreintes
    oncalls, oncall_messages = OnCallAutomation.generate_oncall_schedule(
        start_date, end_date, oncall_rotation_order, dry_run
    )
    result['oncall']['generated'] = oncalls
    result['oncall']['messages'] = oncall_messages
    
    # Générer les shifts
    if use_advanced_rules:
        # Utiliser les nouvelles règles métiers
        from app.utils.advanced_shift_automation import AdvancedShiftAutomation
        shifts, shift_messages = AdvancedShiftAutomation.generate_full_schedule(
            start_date, end_date, dry_run
        )
    else:
        # Utiliser l'ancienne méthode
        shifts, shift_messages = ShiftAutomation.generate_shift_schedule(
            start_date, end_date, shift_rules, dry_run
        )
    result['shift']['generated'] = shifts
    result['shift']['messages'] = shift_messages
    
    # Résumé
    result['summary'] = [
        f"Astreintes générées : {len(oncalls)}",
        f"Shifts générés : {len(shifts)}",
        f"Total : {len(oncalls) + len(shifts)} entrées"
    ]
    
    return result


def get_automation_status() -> Dict[str, Any]:
    """
    Retourne l'état actuel de l'automatisation.
    
    Returns:
        Dictionnaire contenant :
        - Nombre d'astreintes existantes
        - Nombre de shifts existants
        - Nombre d'utilisateurs éligibles pour les astreintes
        - Nombre d'utilisateurs éligibles pour les shifts
        - Prochaine date disponible pour la génération
    """
    # Compter les astreintes existantes
    oncall_count = OnCall.query.count()
    
    # Compter les shifts existants
    shift_count = Shift.query.count()
    
    # Compter les utilisateurs éligibles
    oncall_eligible = len(OnCallAutomation.get_eligible_users())
    shift_eligible = len(ShiftAutomation.get_eligible_users())
    
    # Trouver la prochaine date disponible (le premier vendredi dans le futur sans astreinte)
    today = date.today()
    current_date = today
    while current_date.weekday() != 4:
        current_date += timedelta(days=1)
    
    # Vérifier si une astreinte existe déjà pour ce vendredi
    next_oncall_date = None
    while next_oncall_date is None:
        start_time = datetime.combine(current_date, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)
        
        has_oncall = OnCall.query.filter(
            OnCall.start_time == start_time
        ).first()
        
        if not has_oncall:
            next_oncall_date = current_date
        else:
            current_date += timedelta(days=7)
    
    return {
        'oncall_count': oncall_count,
        'shift_count': shift_count,
        'oncall_eligible_users': oncall_eligible,
        'shift_eligible_users': shift_eligible,
        'next_available_oncall_date': next_oncall_date.strftime('%Y-%m-%d') if next_oncall_date else None,
    }


# ============================================================================
# NETTOYAGE AUTOMATIQUE DES DONNÉES
# ============================================================================

class DataCleanupConfig:
    """
    Configuration du nettoyage automatique des données.
    
    Variables d'environnement disponibles:
    - DATA_CLEANUP_ENABLED: true/false (défaut: false - désactivé par défaut)
    - DATA_CLEANUP_RETENTION: durée de rétention (ex: '1y', '6m', '30d', '365' en jours)
    - DATA_CLEANUP_BATCH_SIZE: taille des lots pour la suppression (défaut: 1000)
    - DATA_CLEANUP_SCHEDULE: planification cron (ex: '0 0 * * *' pour minuit)
    """
    
    # Désactivé par défaut pour la sécurité
    ENABLED = False
    
    # Durée de rétention par défaut: 1 an
    RETENTION_DAYS = 365
    
    # Taille des lots pour la suppression
    BATCH_SIZE = 1000
    
    # Planification par défaut: tous les jours à minuit
    SCHEDULE = '0 0 * * *'
    
    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement."""
        import os
        
        def get_bool(env_var, default=False):
            value = os.environ.get(env_var, '').lower()
            return value in ('true', '1', 'yes', 'y', 'on') if value else default
        
        def get_int(env_var, default=0):
            value = os.environ.get(env_var, '')
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        def parse_retention(retention_str):
            """Parse une chaîne de rétention (ex: '1y', '6m', '30d') en jours."""
            if not retention_str:
                return cls.RETENTION_DAYS
            
            retention_str = retention_str.lower().strip()
            
            if retention_str.endswith('y'):
                years = int(retention_str[:-1])
                return years * 365
            elif retention_str.endswith('m'):
                months = int(retention_str[:-1])
                return months * 30
            elif retention_str.endswith('d'):
                days = int(retention_str[:-1])
                return days
            else:
                try:
                    return int(retention_str)
                except ValueError:
                    return cls.RETENTION_DAYS
        
        cls.ENABLED = get_bool('DATA_CLEANUP_ENABLED', cls.ENABLED)
        
        retention_str = os.environ.get('DATA_CLEANUP_RETENTION', f'{cls.RETENTION_DAYS}d')
        cls.RETENTION_DAYS = parse_retention(retention_str)
        
        cls.BATCH_SIZE = get_int('DATA_CLEANUP_BATCH_SIZE', cls.BATCH_SIZE)
        cls.SCHEDULE = os.environ.get('DATA_CLEANUP_SCHEDULE', cls.SCHEDULE)


# Charger la configuration depuis l'environnement
DataCleanupConfig.from_env()


def cleanup_old_data(days=None):
    """
    Supprime les données anciennes (shifts, astreintes, congés).
    
    Args:
        days: Nombre de jours à conserver (par défaut: DataCleanupConfig.RETENTION_DAYS)
    
    Returns:
        Dict: Statistiques de nettoyage
    """
    if not DataCleanupConfig.ENABLED:
        return {'status': 'disabled', 'message': 'Nettoyage automatique désactivé'}
    
    if days is None:
        days = DataCleanupConfig.RETENTION_DAYS
    
    from datetime import datetime, timedelta
    from app import db, app
    
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_date_obj = cutoff_date.date()
    
    stats = {
        'cutoff_date': cutoff_date.isoformat(),
        'shifts_deleted': 0,
        'on_calls_deleted': 0,
        'leaves_deleted': 0,
        'errors': []
    }
    
    batch_size = DataCleanupConfig.BATCH_SIZE
    
    try:
        while True:
            old_shifts = Shift.query.filter(Shift.end_time < cutoff_date).limit(batch_size).all()
            if not old_shifts:
                break
            for shift in old_shifts:
                db.session.delete(shift)
            db.session.commit()
            stats['shifts_deleted'] += len(old_shifts)
            app.logger.info(f"Nettoyage: {len(old_shifts)} shifts supprimés")
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Erreur lors de la suppression des shifts: {str(e)}")
        app.logger.error(f"Erreur nettoyage shifts: {str(e)}")
    
    try:
        while True:
            old_on_calls = OnCall.query.filter(OnCall.end_time < cutoff_date).limit(batch_size).all()
            if not old_on_calls:
                break
            for on_call in old_on_calls:
                db.session.delete(on_call)
            db.session.commit()
            stats['on_calls_deleted'] += len(old_on_calls)
            app.logger.info(f"Nettoyage: {len(old_on_calls)} astreintes supprimées")
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Erreur lors de la suppression des astreintes: {str(e)}")
        app.logger.error(f"Erreur nettoyage astreintes: {str(e)}")
    
    try:
        while True:
            old_leaves = Leave.query.filter(Leave.end_date < cutoff_date_obj).limit(batch_size).all()
            if not old_leaves:
                break
            for leave in old_leaves:
                db.session.delete(leave)
            db.session.commit()
            stats['leaves_deleted'] += len(old_leaves)
            app.logger.info(f"Nettoyage: {len(old_leaves)} congés supprimés")
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Erreur lors de la suppression des congés: {str(e)}")
        app.logger.error(f"Erreur nettoyage congés: {str(e)}")
    
    stats['status'] = 'completed'
    stats['total_deleted'] = stats['shifts_deleted'] + stats['on_calls_deleted'] + stats['leaves_deleted']
    app.logger.info(f"Nettoyage automatique terminé: {stats['total_deleted']} éléments supprimés")
    return stats


def setup_data_cleanup(app):
    """Configure le nettoyage automatique des données."""
    if not DataCleanupConfig.ENABLED:
        app.logger.info("Nettoyage automatique des données désactivé")
        return
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(cleanup_old_data, 'cron', **parse_cron_schedule(DataCleanupConfig.SCHEDULE))
        scheduler.start()
        app.extensions['data_cleanup_scheduler'] = scheduler
        app.logger.info(f"Nettoyage automatique configuré: {DataCleanupConfig.SCHEDULE}")
    except ImportError:
        app.logger.warning("APScheduler non installé. Le nettoyage automatique ne sera pas disponible.")
    except Exception as e:
        app.logger.error(f"Erreur lors de la configuration du nettoyage automatique: {str(e)}")


def parse_cron_schedule(schedule_str):
    """Parse une chaîne cron en dictionnaire pour APScheduler."""
    parts = schedule_str.split()
    if len(parts) == 5:
        return {'minute': parts[0], 'hour': parts[1], 'day': parts[2], 'month': parts[3], 'day_of_week': parts[4]}
    elif len(parts) == 6:
        return {'second': parts[0], 'minute': parts[1], 'hour': parts[2], 'day': parts[3], 'month': parts[4], 'day_of_week': parts[5]}
    else:
        return {'minute': '0', 'hour': '0'}
