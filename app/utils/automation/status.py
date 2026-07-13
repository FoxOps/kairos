"""
Automation status utilities for Leviia Schedule.

This module provides functions to check the current status of automation.
"""

from datetime import date, datetime, timedelta
from typing import Any

from app.models import OnCall, Shift
from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation
from app.utils.automation.oncall_automation import OnCallAutomation


def get_automation_status() -> dict[str, Any]:
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
    shift_eligible = len(AdvancedShiftAutomation.get_users_in_schedule_groups())

    # Trouver la prochaine date disponible (le premier vendredi dans le futur sans astreinte)
    today = date.today()
    current_date = today
    while current_date.weekday() != 4:  # 4 = vendredi
        current_date += timedelta(days=1)

    # Vérifier si une astreinte existe déjà pour ce vendredi
    next_oncall_date = None
    while next_oncall_date is None:
        start_time = datetime.combine(current_date, datetime.min.time()).replace(
            hour=21
        )

        has_oncall = OnCall.query.filter(OnCall.start_time == start_time).first()

        if not has_oncall:
            next_oncall_date = current_date
        else:
            current_date += timedelta(days=7)

    return {
        "oncall_count": oncall_count,
        "shift_count": shift_count,
        "oncall_eligible_users": oncall_eligible,
        "shift_eligible_users": shift_eligible,
        "next_available_oncall_date": (
            next_oncall_date.strftime("%Y-%m-%d") if next_oncall_date else None
        ),
    }
