# ============================================================================
# AUTOMATISATION AVANCÉE DES SHIFTS (NOUVELLES RÈGLES MÉTIERS)
# ============================================================================

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Modèles importés uniquement pour les annotations de type (en chaîne
    # dans ce fichier) - jamais au runtime, pour éviter l'import circulaire
    # que les imports différés dans chaque méthode contournent déjà (voir
    # `from app.models import ...` locaux plus bas). Avant ce bloc, ces
    # noms n'étaient importés nulle part : inoffensif au runtime (une
    # annotation entre guillemets n'est jamais évaluée), mais cassait tout
    # outil qui les résout (mypy, typing.get_type_hints()).
    from app.models import Leave, OnCall, ShiftType, User

# Sentinel distinct de None : None est une valeur valide (aucune astreinte
# ce jour-là) pour oncall_today/oncall_user_last_week dans
# determine_shift_for_user - il faut donc un marqueur séparé pour détecter
# "argument non fourni, calcule-le toi-même" (comportement historique,
# préservé pour les appelants qui invoquent la méthode isolément).
_UNSET: "object" = object()


class AdvancedShiftAutomation:
    """
    Classe pour gérer l'automatisation avancée des shifts selon les nouvelles règles métiers.

    Règles implémentées :
    1. Créneau 13h-21h : Réservé à la personne d'astreinte SI elle fait partie d'un groupe schedule
    2. Rotation des créneaux : Si une personne était sur 13h-21h une semaine, elle doit être sur 07h-15h la semaine suivante
    3. Créneau par défaut : 09h-17h pour tous les autres cas (plusieurs personnes peuvent être sur ce créneau)
    4. Cas des congés : Si seulement 2 personnes disponibles, la personne NON d'astreinte doit être sur 07h-15h
    5. Contrainte légale : Pas 2 astreintes de suite - minimum 2 semaines sans astreinte entre deux astreintes
    """

    # Créneaux horaires
    SHIFT_07_15 = (7, 15)  # 07h-15h
    SHIFT_09_17 = (9, 17)  # 09h-17h
    SHIFT_13_21 = (13, 21)  # 13h-21h

    @staticmethod
    def get_shift_type_by_hours(start_hour: int, end_hour: int) -> "ShiftType":
        """Récupère ou crée un type de shift basé sur les heures."""
        from app import db
        from app.models import ShiftType

        shift_type = ShiftType.query.filter_by(
            start_hour=start_hour, end_hour=end_hour
        ).first()
        if shift_type:
            return shift_type

        # Créer un nouveau type de shift si nécessaire
        name = f"{start_hour:02d}-{end_hour:02d}"
        label = f"{start_hour:02d}h-{end_hour:02d}h"

        new_shift_type = ShiftType(
            name=name, label=label, start_hour=start_hour, end_hour=end_hour
        )
        db.session.add(new_shift_type)
        db.session.flush()  # Pour obtenir l'ID
        return new_shift_type

    @staticmethod
    def get_users_in_schedule_groups() -> list:
        """Récupère les utilisateurs qui font partie de groupes pouvant être ajoutés au schedule."""
        from app.models import Group, User

        return User.query.join(Group).filter(Group.is_part_of_schedule.is_(True)).all()

    @staticmethod
    def get_available_users_for_date(date: "date") -> list:
        """Récupère les utilisateurs disponibles pour une date donnée (pas en congé)."""
        from app import db
        from app.models import Leave

        eligible_users = AdvancedShiftAutomation.get_users_in_schedule_groups()

        if not eligible_users:
            return []

        # Optimisation : Récupérer tous les user_ids éligibles
        user_ids = [user.id for user in eligible_users]

        # Récupérer tous les utilisateurs en congé pour cette date en une seule requête
        users_on_leave = set()
        leave_conflicts = (
            db.session.query(Leave.user_id)
            .filter(
                Leave.user_id.in_(user_ids),
                Leave.start_date <= date,
                Leave.end_date >= date,
            )
            .all()
        )
        users_on_leave = {lc.user_id for lc in leave_conflicts}

        # Filtrer les utilisateurs disponibles
        available_users = [
            user for user in eligible_users if user.id not in users_on_leave
        ]

        return available_users

    @staticmethod
    def get_oncall_for_date(date: "date") -> "OnCall | None":
        """Récupère l'astreinte (OnCall) pour une date donnée."""
        from datetime import datetime

        from app import db
        from app.models import OnCall

        # Optimisation : utiliser une requête avec JOIN pour éviter le lazy loading
        oncall = (
            db.session.query(OnCall)
            .options(db.joinedload(OnCall.user))
            .filter(
                OnCall.start_time <= datetime.combine(date, datetime.max.time()),
                OnCall.end_time >= datetime.combine(date, datetime.min.time()),
            )
            .first()
        )

        return oncall

    @staticmethod
    def get_oncall_user_for_date(date: "date") -> "User | None":
        """Récupère l'utilisateur d'astreinte pour une date donnée."""
        oncall = AdvancedShiftAutomation.get_oncall_for_date(date)
        return oncall.user if oncall else None

    @staticmethod
    def determine_shift_for_user(
        user: "User",
        date: "date",
        oncall_today: "OnCall | None | object" = _UNSET,
        oncall_user_last_week: "User | None | object" = _UNSET,
    ) -> "tuple[int, int]":
        """
        Détermine le créneau de shift pour un utilisateur à une date donnée.

        Règles :
        1. Si l'utilisateur est d'astreinte cette semaine :
           - Si c'est le premier jour ouvré de son astreinte (lundi) -> 09h-17h (par défaut)
           - Sinon (mardi-jeudi) -> 13h-21h (si éligible)
           - Le vendredi (dernier jour de l'astreinte) -> 09h-17h (par défaut)
        2. Si l'utilisateur était d'astreinte la semaine précédente (et pas cette semaine) -> 07h-15h (rotation)
        3. Sinon -> 09h-17h

        `oncall_today`/`oncall_user_last_week` : passés par l'appelant (une
        seule requête par jour dans generate_daily_shifts) au lieu d'être
        requêtés une fois par utilisateur - ils restent optionnels pour les
        appelants qui invoquent cette méthode isolément (tests notamment).
        """
        from datetime import timedelta
        from typing import cast

        # Règle 1 : Vérifier si l'utilisateur est d'astreinte cette semaine
        if oncall_today is _UNSET:
            oncall = AdvancedShiftAutomation.get_oncall_for_date(date)
        else:
            oncall = cast("OnCall | None", oncall_today)
        if oncall and oncall.user_id == user.id:
            # Vérifier si c'est le premier jour ouvré de l'astreinte (lundi)
            # ou le dernier jour (vendredi, fin de l'astreinte à 07h)
            if date.weekday() == 0 or date.weekday() == 4:  # 0 = lundi, 4 = vendredi
                return AdvancedShiftAutomation.SHIFT_09_17

            # Pour les autres jours (mardi-jeudi), vérifier l'éligibilité
            from app import db
            from app.models import Group, User

            user_in_schedule = db.session.query(
                db.exists().where(
                    User.id == user.id,
                    User.group_id == Group.id,
                    Group.is_part_of_schedule.is_(True),
                )
            ).scalar()
            if user_in_schedule:
                return AdvancedShiftAutomation.SHIFT_13_21

        # Règle 2 : Vérifier si l'utilisateur était d'astreinte la semaine précédente
        if oncall_user_last_week is _UNSET:
            previous_week_date = date - timedelta(days=7)
            previous_oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(
                previous_week_date
            )
        else:
            previous_oncall_user = cast("User | None", oncall_user_last_week)
        if previous_oncall_user and previous_oncall_user.id == user.id:
            return AdvancedShiftAutomation.SHIFT_07_15

        # Règle 3 : Créneau par défaut
        return AdvancedShiftAutomation.SHIFT_09_17

    @staticmethod
    def handle_two_users_case(available_users: list, date: "date") -> "dict":
        """
        Gère le cas spécial où il n'y a que 2 personnes disponibles.
        La personne NON d'astreinte doit être sur 07h-15h.
        """
        if len(available_users) != 2:
            return {}

        oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(date)
        assignments = {}

        for user in available_users:
            if oncall_user and user.id == oncall_user.id:
                schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
                if any(u.id == user.id for u in schedule_users):
                    assignments[user] = AdvancedShiftAutomation.SHIFT_13_21
                else:
                    assignments[user] = AdvancedShiftAutomation.SHIFT_09_17
            else:
                assignments[user] = AdvancedShiftAutomation.SHIFT_07_15

        return assignments

    @staticmethod
    def generate_daily_shifts(
        date: "date", dry_run: bool = False
    ) -> "tuple[list, list]":
        """Génère les shifts pour une journée selon les nouvelles règles."""
        from datetime import datetime, timedelta

        from app import db
        from app.models import Shift

        messages = []
        generated_shifts = []

        if date.weekday() >= 5:
            return [], [
                f"⏭️ Pas de shift généré pour le {date.strftime('%d/%m/%Y')} (week-end)"
            ]

        available_users = AdvancedShiftAutomation.get_available_users_for_date(date)

        if not available_users:
            return [], [
                f"⚠️ Aucun utilisateur disponible pour le {date.strftime('%d/%m/%Y')}"
            ]

        # Règle 6 : effectif minimum 1 personne. Quand une seule personne est
        # disponible (cas limite, en dessous du cas à 2 personnes ci-dessous),
        # elle est placée directement en 09h-17h sans passer par
        # determine_shift_for_user/handle_two_users_case.
        if len(available_users) == 1:
            sole_user = available_users[0]
            start_hour, end_hour = AdvancedShiftAutomation.SHIFT_09_17
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                start_hour, end_hour
            )
            start_time = datetime.combine(date, datetime.min.time()).replace(
                hour=start_hour
            )
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=end_hour
            )
            shift = Shift(
                user_id=sole_user.id,
                shift_type_id=shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=date,
            )
            generated_shifts.append(shift)

            if not dry_run:
                try:
                    db.session.add_all(generated_shifts)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    messages.append(f"❌ Erreur : {str(e)}")
                    return [], messages

            messages.append(
                f"✅ 1 shift généré pour le {date.strftime('%d/%m/%Y')} (effectif minimum : {sole_user.name})"
            )
            return generated_shifts, messages

        # Cas spécial : seulement 2 personnes disponibles
        if len(available_users) == 2:
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, date
            )
            if assignments:
                for user, (start_hour, end_hour) in assignments.items():
                    shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                        start_hour, end_hour
                    )
                    start_time = datetime.combine(date, datetime.min.time()).replace(
                        hour=start_hour
                    )
                    end_time = datetime.combine(date, datetime.min.time()).replace(
                        hour=end_hour
                    )

                    shift = Shift(
                        user_id=user.id,
                        shift_type_id=shift_type.id,
                        start_time=start_time,
                        end_time=end_time,
                        date=date,
                    )
                    generated_shifts.append(shift)

                if not dry_run:
                    try:
                        db.session.add_all(generated_shifts)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        messages.append(f"❌ Erreur : {str(e)}")
                        return [], messages

                return generated_shifts, messages

        # Cas normal : 3+ utilisateurs
        # Optimisation : utiliser un set pour les user_ids disponibles pour éviter les lookups linéaires
        available_user_ids = {user.id for user in available_users}
        schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()

        # Récupérées une seule fois pour la journée (au lieu d'une requête
        # OnCall par utilisateur dans determine_shift_for_user - l'astreinte
        # du jour ne dépend pas de l'utilisateur itéré).
        oncall_today = AdvancedShiftAutomation.get_oncall_for_date(date)
        previous_week_date = date - timedelta(days=7)
        oncall_user_last_week = AdvancedShiftAutomation.get_oncall_user_for_date(
            previous_week_date
        )

        for user in schedule_users:
            if user.id not in available_user_ids:
                continue

            start_hour, end_hour = AdvancedShiftAutomation.determine_shift_for_user(
                user, date, oncall_today, oncall_user_last_week
            )
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                start_hour, end_hour
            )
            start_time = datetime.combine(date, datetime.min.time()).replace(
                hour=start_hour
            )
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=end_hour
            )

            shift = Shift(
                user_id=user.id,
                shift_type_id=shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=date,
            )
            generated_shifts.append(shift)

        if not dry_run and generated_shifts:
            try:
                db.session.add_all(generated_shifts)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                messages.append(f"❌ Erreur : {str(e)}")
                return [], messages

        # Retourner un résumé au lieu de messages détaillés
        if generated_shifts:
            return generated_shifts, [
                f"✅ {len(generated_shifts)} shifts générés pour le {date.strftime('%d/%m/%Y')}"
            ]
        elif date.weekday() >= 5:
            return [], [
                f"⏭️ Pas de shift généré pour le {date.strftime('%d/%m/%Y')} (week-end)"
            ]
        else:
            return [], [f"⚠️ Aucun shift généré pour le {date.strftime('%d/%m/%Y')}"]

    @staticmethod
    def generate_full_schedule(
        start_date: "date", end_date: "date", dry_run: bool = False
    ) -> "tuple[list, list]":
        """Génère les shifts pour toute une période."""
        all_shifts = []
        days_with_shifts = 0
        days_skipped = 0
        from datetime import timedelta

        current_date = start_date
        while current_date <= end_date:
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                current_date, dry_run=dry_run
            )
            all_shifts.extend(shifts)
            if shifts:
                days_with_shifts += 1
            else:
                days_skipped += 1
            current_date += timedelta(days=1)

        # Retourner un résumé
        if dry_run:
            msg = f"📋 Prévisualisation : {len(all_shifts)} shifts seraient générés pour la période du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
        else:
            msg = f"🎉 {len(all_shifts)} shifts générés pour la période du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
        if days_skipped > 0:
            msg += f" ({days_with_shifts} jours avec shifts, {days_skipped} jours sans)"
        return all_shifts, [msg]

    @staticmethod
    def rebalance_after_leave(
        leave: "Leave", dry_run: bool = False
    ) -> "tuple[list, list]":
        """
        Rééquilibre les shifts et astreintes après l'ajout/modification d'un congé.
        Appelé automatiquement lors de l'ajout d'un congé.
        Les congés sont prioritaires : ils suppriment et recalculent les shifts et astreintes chevauchantes.
        """
        from datetime import datetime, timedelta

        from app import db
        from app.models import OnCall, Shift
        from app.utils.automation import OnCallAutomation

        messages = []
        regenerated_shifts = []
        regenerated_oncalls = []

        # Récupérer toutes les dates du congé
        leave_dates = []
        current_date = leave.start_date
        while current_date <= leave.end_date:
            leave_dates.append(current_date)
            current_date += timedelta(days=1)

        # Trouver la période des astreintes à recalculer
        # Les astreintes couvrent du vendredi 21h au vendredi suivant 07h
        # Nous devons trouver tous les vendredis qui ont des astreintes chevauchantes
        oncall_periods_to_regenerate = set()

        # Trouver les astreintes qui chevauchent le congé
        overlapping_oncalls = OnCall.query.filter(
            OnCall.user_id == leave.user_id,
            OnCall.start_time
            < datetime.combine(leave.end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(leave.start_date, datetime.min.time()),
        ).all()

        for oncall in overlapping_oncalls:
            # Trouver le vendredi de début de cette astreinte
            friday_start = oncall.start_time.date()
            oncall_periods_to_regenerate.add(friday_start)

        # Supprimer les astreintes chevauchantes
        if overlapping_oncalls and not dry_run:
            for oncall in overlapping_oncalls:
                db.session.delete(oncall)
            db.session.commit()
            messages.append(
                f"🗑️ {len(overlapping_oncalls)} astreintes supprimées pour l'utilisateur {leave.user_id}"
            )

        # Déterminer la période complète à recalculer
        # Si des astreintes ont été supprimées, nous devons recalculer les shifts pour toute la période affectée
        shift_period_start = leave.start_date
        shift_period_end = leave.end_date

        if oncall_periods_to_regenerate:
            # Trouver la période à couvrir : du premier vendredi avant le congé
            # au dernier vendredi après la fin du congé + 7 jours (pour couvrir toute l'astreinte)

            # Trouver le premier vendredi avant ou pendant le congé
            first_friday = leave.start_date
            while first_friday.weekday() != 4:  # 4 = vendredi
                first_friday -= timedelta(days=1)

            # Trouver le dernier vendredi après ou pendant le congé
            last_friday = leave.end_date
            while last_friday.weekday() != 4:
                last_friday += timedelta(days=1)

            # Étendre la période pour couvrir les astreintes complètes
            shift_period_start = first_friday - timedelta(
                days=7
            )  # Prendre une semaine avant
            shift_period_end = last_friday + timedelta(
                days=7
            )  # Prendre une semaine après

        # Supprimer et régénérer les shifts pour toute la période affectée
        current_date = shift_period_start
        while current_date <= shift_period_end:
            if current_date.weekday() < 5:  # Seulement du lundi au vendredi
                # Supprimer les shifts existants
                existing_shifts = Shift.query.filter_by(date=current_date).all()
                if existing_shifts and not dry_run:
                    for shift in existing_shifts:
                        db.session.delete(shift)
                    db.session.commit()
                    messages.append(
                        f"🗑️ {len(existing_shifts)} shifts supprimés pour le {current_date.strftime('%d/%m/%Y')}"
                    )

                # Régénérer les shifts avec les règles métiers avancées
                shifts, date_messages = AdvancedShiftAutomation.generate_daily_shifts(
                    current_date, dry_run=dry_run
                )
                regenerated_shifts.extend(shifts)
                messages.extend(date_messages)
            current_date += timedelta(days=1)

        # Régénérer les astreintes pour la période affectée
        # Si des astreintes ont été supprimées, nous devons les recalculer
        if oncall_periods_to_regenerate and not dry_run:
            try:
                # Utiliser la même période que pour les shifts
                from app.models import AutomationConfig
                from app.utils.automation import OnCallAutomation

                oncalls, oncall_messages = OnCallAutomation.generate_oncall_schedule(
                    shift_period_start,
                    shift_period_end,
                    rotation_order_ids=AutomationConfig.get_rotation_order(),
                    dry_run=False,
                )
                regenerated_oncalls.extend(oncalls)
                messages.extend(oncall_messages)
                messages.append(
                    f"🔄 {len(oncalls)} astreintes régénérées pour la période {shift_period_start.strftime('%d/%m/%Y')} - {shift_period_end.strftime('%d/%m/%Y')}"
                )
            except Exception as e:
                messages.append(f"⚠️ Erreur lors du recalcul des astreintes: {str(e)}")

        return regenerated_shifts, messages
