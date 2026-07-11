"""
Automation admin service for Leviia Schedule.

Business logic supporting the admin automation screens: parsing the
daily-requirements form into BusinessRules-shaped data, clearing an
existing period before regeneration, and persisting the rotation order.
The actual schedule generation itself lives in app.utils.automation
(OnCallAutomation/ShiftAutomation/AdvancedShiftAutomation), which is
already a business-logic layer - this service wraps the admin-specific
glue around it rather than duplicating it.
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

from app import db
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.utils.automation import BusinessRules

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
SHIFT_KINDS = ['morning', 'afternoon', 'evening']


class AutomationAdminService:
    """Logique métier support pour les écrans d'automatisation admin."""

    @staticmethod
    def parse_shift_rules_from_form(form) -> Dict:
        """Construit les daily_requirements à partir des champs
        `{day}_{shift_kind}` du formulaire (ex: monday_morning)."""
        rules = BusinessRules.get_shift_rules()

        for day in WEEKDAYS:
            for shift_kind in SHIFT_KINDS:
                count_key = f"{day}_{shift_kind}"
                if count_key in form:
                    try:
                        count = int(form[count_key])
                        rules['daily_requirements'].setdefault(day, {})
                        rules['daily_requirements'][day][shift_kind] = count
                    except ValueError:
                        pass

        return rules

    @staticmethod
    def parse_rotation_order_from_form(form) -> List[int]:
        """Extrait l'ordre de rotation depuis les champs
        `rotation_order_{user_id}` (position) / `include_{user_id}`."""
        user_data = []
        for key, value in form.items():
            if key.startswith("rotation_order_"):
                user_id = int(key.replace("rotation_order_", ""))
                position = int(value)
                include = form.get(f"include_{user_id}", "0") == "1"
                user_data.append({'user_id': user_id, 'position': position, 'include': include})

        user_data_sorted = sorted(user_data, key=lambda u: u['position'])
        return [u['user_id'] for u in user_data_sorted if u['include']]

    @staticmethod
    def save_rotation_order(rotation_order_ids: List[int]) -> Optional[str]:
        """Returns error_message, ou None si succès."""
        try:
            from app.models import AutomationConfig
            AutomationConfig.set_rotation_order(rotation_order_ids)
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    @staticmethod
    def get_rotation_order() -> Optional[List[int]]:
        try:
            from app.models import AutomationConfig
            return AutomationConfig.get_rotation_order()
        except Exception:
            return None

    @staticmethod
    def clear_period(start_date: date, end_date: date) -> Tuple[int, int]:
        """Supprime les astreintes et shifts existants chevauchant la
        période. Returns (nb_astreintes_supprimees, nb_shifts_supprimes)."""
        oncalls_deleted = OnCallRepository.delete_overlapping_range(start_date, end_date)
        if oncalls_deleted:
            db.session.commit()

        shifts_deleted = ShiftRepository.delete_in_date_range(start_date, end_date)
        if shifts_deleted:
            db.session.commit()

        return oncalls_deleted, shifts_deleted
