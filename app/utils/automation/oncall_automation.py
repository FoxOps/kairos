"""
OnCall automation utilities for Leviia Schedule.

This module provides automation functionality for on-call duties.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from app.models import Group, Leave, OnCall, User


class AvailabilityIndex:
    """Vue en mémoire des astreintes/congés existants pour un ensemble
    d'utilisateurs, construite par UNE requête bulk par source (OnCall,
    Leave) puis mise à jour localement via record_assignment() au fil des
    affectations faites pendant une génération.

    Remplace des requêtes DB répétées par candidat/semaine (jusqu'à 3 par
    candidat testé : conflit d'astreinte, conflit de congé, contrainte
    d'espacement légal) - sur une génération de 6 mois avec plusieurs
    utilisateurs testés par semaine, ça représentait 1500+ requêtes.
    record_assignment() est indispensable (pas seulement le préchargement
    initial) : sans lui, une astreinte tout juste attribuée à un
    utilisateur plus tôt dans la même génération ne serait pas vue par les
    vérifications des semaines suivantes pour ce même utilisateur - avant
    ce correctif, c'est l'autoflush de SQLAlchemy qui garantissait cette
    visibilité implicitement à chaque requête.
    """

    def __init__(self, user_ids: Iterable[int]):
        user_id_set = set(user_ids)
        self._oncall_intervals: dict[int, list[tuple[datetime, datetime]]] = (
            defaultdict(list)
        )
        self._last_oncall_end: dict[int, datetime] = {}
        self._leave_intervals: dict[int, list[tuple[date, date]]] = defaultdict(list)

        if not user_id_set:
            return

        for oncall in OnCall.query.filter(OnCall.user_id.in_(user_id_set)).all():
            self._oncall_intervals[oncall.user_id].append(
                (oncall.start_time, oncall.end_time)
            )
            current_last = self._last_oncall_end.get(oncall.user_id)
            if current_last is None or oncall.end_time > current_last:
                self._last_oncall_end[oncall.user_id] = oncall.end_time

        for leave in Leave.query.filter(Leave.user_id.in_(user_id_set)).all():
            self._leave_intervals[leave.user_id].append(
                (leave.start_date, leave.end_date)
            )

    def has_oncall_conflict(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        return any(
            existing_start < end_time and existing_end > start_time
            for existing_start, existing_end in self._oncall_intervals.get(user_id, [])
        )

    def has_leave_conflict(
        self, user_id: int, start_date: date, end_date: date
    ) -> bool:
        return any(
            leave_start <= end_date and leave_end >= start_date
            for leave_start, leave_end in self._leave_intervals.get(user_id, [])
        )

    def meets_spacing_constraint(self, user_id: int, start_time: datetime) -> bool:
        last_end = self._last_oncall_end.get(user_id)
        if last_end is None:
            return True
        gap_days = (start_time - last_end).days
        return gap_days / 7 >= 2

    def record_assignment(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> None:
        self._oncall_intervals[user_id].append((start_time, end_time))
        current_last = self._last_oncall_end.get(user_id)
        if current_last is None or end_time > current_last:
            self._last_oncall_end[user_id] = end_time


class OnCallAutomation:
    """
    Classe pour gérer l'automatisation des astreintes (On-Call).

    Fonctionnalités :
    - Génération automatique des astreintes avec rotation
    - Gestion des remplacements en cas de conflit
    - Configuration de l'ordre de rotation
    """

    @staticmethod
    def get_eligible_users() -> list[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les astreintes.
        Un utilisateur est éligible s'il appartient à un groupe participant aux astreintes.
        """
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_oncall.is_(True))
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def get_rotation_order(rotation_order_ids: list[int] | None = None) -> list[User]:
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
            remaining_users = [
                u for u in eligible_users if u.id not in rotation_order_ids
            ]
            ordered_users.extend(remaining_users)

            return ordered_users

        # Sinon, retourner dans l'ordre alphabétique
        return eligible_users

    @staticmethod
    def check_oncall_constraint(
        user: User, start_time: datetime, index: AvailabilityIndex
    ) -> bool:
        """
        Vérifie la contrainte légale d'espacement minimal (2 semaines) entre deux
        astreintes consécutives pour un même utilisateur.

        Args:
            user: Utilisateur à vérifier
            start_time: Début de la nouvelle astreinte envisagée
            index: Vue en mémoire des astreintes/congés existants (voir
                AvailabilityIndex) - évite une requête DB par appel.

        Returns:
            True si aucune astreinte précédente ou si l'espacement est suffisant.
        """
        return index.meets_spacing_constraint(user.id, start_time)

    @staticmethod
    def find_next_available_user(
        users: list[User],
        start_time: datetime,
        end_time: datetime,
        index: AvailabilityIndex,
    ) -> User | None:
        """
        Trouve le premier utilisateur de la liste disponible pour la période donnée
        (pas de congé, pas d'astreinte chevauchante, contrainte légale respectée).

        Args:
            users: Liste ordonnée d'utilisateurs candidats
            start_time: Début de la période d'astreinte
            end_time: Fin de la période d'astreinte
            index: Vue en mémoire des astreintes/congés existants (voir
                AvailabilityIndex) - évite une requête DB par candidat testé.

        Returns:
            Le premier utilisateur disponible, ou None si aucun ne l'est.
        """
        for user in users:
            if index.has_oncall_conflict(user.id, start_time, end_time):
                continue

            if index.has_leave_conflict(user.id, start_time.date(), end_time.date()):
                continue

            if not OnCallAutomation.check_oncall_constraint(user, start_time, index):
                continue

            return user

        return None

    @staticmethod
    def generate_oncall_schedule(
        start_date,
        end_date,
        rotation_order_ids: list[int] | None = None,
        dry_run: bool = True,
        commit: bool = True,
    ):
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
            commit: Si False (utilisé par rebalance_after_leave pour rendre
                tout le rééquilibrage atomique), flush() au lieu de commit()
                - laisse l'appelant décider quand committer/rollback.

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

        # Une requête bulk par source (OnCall, Leave) au lieu de plusieurs
        # requêtes par candidat testé à chaque semaine - voir AvailabilityIndex.
        index = AvailabilityIndex(user.id for user in eligible_users)

        days_ahead = (4 - start_date.weekday()) % 7
        current_friday = start_date + timedelta(days=days_ahead)

        oncalls = []
        messages = []
        rotation_index = 0

        # end_date inclusif, comme AdvancedShiftAutomation.generate_full_schedule
        # (`current_date <= end_date`) - les deux reçoivent la même période
        # depuis admin_automation_routes.py::automation_full, elles doivent
        # traiter end_date de la même façon. Avant : `<` ignorait la semaine
        # dont le vendredi tombait exactement sur end_date.
        while current_friday <= end_date:
            start_time = datetime.combine(current_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)

            ordered_candidates = (
                rotation_order[rotation_index:] + rotation_order[:rotation_index]
            )
            assigned_user = OnCallAutomation.find_next_available_user(
                ordered_candidates, start_time, end_time, index
            )

            if assigned_user is None:
                # Dernier recours : ignorer la contrainte légale des 2 semaines,
                # mais toujours respecter congés et astreintes existantes.
                for user in ordered_candidates:
                    has_conflict = index.has_oncall_conflict(
                        user.id, start_time, end_time
                    )
                    has_leave = index.has_leave_conflict(
                        user.id, start_time.date(), end_time.date()
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
            # Indispensable même en dry_run : les semaines suivantes de
            # cette même génération doivent voir cette affectation pour
            # respecter l'espacement légal et éviter les doublons.
            index.record_assignment(assigned_user.id, start_time, end_time)

            rotation_index = (rotation_order.index(assigned_user) + 1) % len(
                rotation_order
            )
            current_friday += timedelta(days=7)

        if not dry_run and oncalls:
            if commit:
                db.session.commit()
            else:
                db.session.flush()

        messages.append(f"Généré {len(oncalls)} astreintes.")
        return oncalls, messages
