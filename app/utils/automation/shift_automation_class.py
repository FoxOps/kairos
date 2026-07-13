"""
Shift automation class for Leviia Schedule.

This module provides the ShiftAutomation class for shift management.
"""

from datetime import date, datetime, timedelta

from app.models import Group, Leave, OnCall, Shift, ShiftType, User


class ShiftAutomation:
    """
    Classe pour gérer l'automatisation des shifts.

    Fonctionnalités :
    - Génération automatique des shifts
    - Gestion des types de shifts
    - Rééquilibrage des shifts après modification
    """

    @staticmethod
    def get_eligible_users() -> list[User]:
        """
        Récupère la liste des utilisateurs éligibles pour les shifts.
        Un utilisateur est éligible s'il appartient à un groupe participant au schedule.
        """
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_schedule.is_(True))
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def get_shift_types() -> list[ShiftType]:
        """Récupère la liste des types de shifts."""
        return ShiftType.query.order_by(ShiftType.start_hour).all()

    @staticmethod
    def can_assign_shift(
        user_id: int, check_date: date, shift_type: ShiftType
    ) -> tuple[bool, str]:
        """
        Vérifie si un shift peut être assigné à un utilisateur pour une date donnée.

        Args:
            user_id: ID de l'utilisateur
            check_date: Date du shift envisagé
            shift_type: Type de shift envisagé

        Returns:
            Tuple (autorisé, message d'erreur si refusé sinon chaîne vide).
        """
        if check_date.weekday() >= 5:
            return (
                False,
                "Les shifts ne peuvent être assignés que du lundi au vendredi.",
            )

        existing_shift = Shift.query.filter(
            Shift.user_id == user_id, Shift.date == check_date
        ).first()
        if existing_shift:
            return False, "L'utilisateur a déjà un shift ce jour-là."

        on_leave = Leave.query.filter(
            Leave.user_id == user_id,
            Leave.start_date <= check_date,
            Leave.end_date >= check_date,
        ).first()
        if on_leave:
            return False, "L'utilisateur est en congé ce jour-là."

        day_start = datetime.combine(check_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        on_oncall = OnCall.query.filter(
            OnCall.user_id == user_id,
            OnCall.start_time < day_end,
            OnCall.end_time > day_start,
        ).first()
        if on_oncall:
            return False, "L'utilisateur est en astreinte ce jour-là."

        return True, ""

    @staticmethod
    def find_replacement_user(
        excluded_user_ids: list[int], check_date: date, shift_type: ShiftType
    ) -> User | None:
        """
        Trouve un utilisateur de remplacement disponible pour un shift, en excluant
        certains utilisateurs (par exemple ceux déjà assignés ou indisponibles).

        Args:
            excluded_user_ids: IDs d'utilisateurs à exclure
            check_date: Date du shift
            shift_type: Type de shift

        Returns:
            Un utilisateur disponible, ou None si aucun candidat.
        """
        for user in ShiftAutomation.get_eligible_users():
            if user.id in excluded_user_ids:
                continue
            can_assign, _ = ShiftAutomation.can_assign_shift(
                user.id, check_date, shift_type
            )
            if can_assign:
                return user
        return None

    @staticmethod
    def generate_shift_schedule(
        start_date: date,
        end_date: date,
        rules: dict | None = None,
        dry_run: bool = True,
    ) -> tuple[list[Shift], list[str]]:
        """
        Génère un planning de shifts pour une période donnée, selon des règles de
        couverture journalière (jours ouvrés uniquement).

        Args:
            start_date: Date de début (incluse)
            end_date: Date de fin (incluse)
            rules: Règles métier (voir BusinessRules.get_shift_rules). Utilise les
                   règles par défaut si non fournies.
            dry_run: Si True, ne sauvegarde rien en base

        Returns:
            Tuple: (liste des shifts générés (objets Shift), messages de log)
        """
        from app import db
        from app.utils.automation.business_rules import BusinessRules

        if rules is None:
            rules = BusinessRules.get_shift_rules()

        users = ShiftAutomation.get_eligible_users()
        if not users:
            return [], ["Aucun utilisateur éligible pour les shifts."]

        daily_requirements = rules.get("daily_requirements", {})
        shift_types_by_name = {st.name: st for st in ShiftAutomation.get_shift_types()}

        weekday_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

        shifts = []
        messages = []
        user_index = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:
                requirements = daily_requirements.get(
                    weekday_names[current_date.weekday()], {}
                )

                for shift_type_name, count in requirements.items():
                    shift_type = shift_types_by_name.get(shift_type_name)
                    if shift_type is None:
                        messages.append(
                            f"Type de shift '{shift_type_name}' non trouvé."
                        )
                        continue

                    for _ in range(count):
                        assigned_user = None
                        for _attempt in range(len(users)):
                            candidate = users[user_index % len(users)]
                            user_index += 1
                            can_assign, _ = ShiftAutomation.can_assign_shift(
                                candidate.id, current_date, shift_type
                            )
                            if can_assign:
                                assigned_user = candidate
                                break

                        if assigned_user is None:
                            messages.append(
                                f"Aucun utilisateur disponible pour {shift_type_name} le {current_date.strftime('%d/%m/%Y')}."
                            )
                            continue

                        shift = Shift(
                            user_id=assigned_user.id,
                            shift_type_id=shift_type.id,
                            start_time=datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.start_hour),
                            end_time=datetime.combine(
                                current_date, datetime.min.time()
                            ).replace(hour=shift_type.end_hour),
                            date=current_date,
                        )
                        shifts.append(shift)
                        if not dry_run:
                            db.session.add(shift)

            current_date += timedelta(days=1)

        if not dry_run and shifts:
            db.session.commit()

        messages.append(f"Généré {len(shifts)} shifts pour {len(users)} utilisateurs.")
        return shifts, messages
