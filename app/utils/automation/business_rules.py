"""
Business rules for Leviia Schedule.

This module provides business rules for shift and on-call generation.
"""

from typing import Any


class BusinessRules:
    """
    Classe pour gérer les règles métiers spécifiques pour la génération des shifts.

    Ces règles peuvent être personnalisées selon les besoins de l'organisation.
    """

    @staticmethod
    def get_shift_rules() -> dict[str, Any]:
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
            "weekly_patterns": {},  # Vide par défaut, à remplir via configuration
            "daily_requirements": {
                "monday": {"morning": 1, "afternoon": 1, "evening": 0},
                "tuesday": {"morning": 1, "afternoon": 1, "evening": 0},
                "wednesday": {"morning": 1, "afternoon": 1, "evening": 0},
                "thursday": {"morning": 1, "afternoon": 1, "evening": 0},
                "friday": {"morning": 1, "afternoon": 1, "evening": 0},
                "saturday": {},
                "sunday": {},
            },
            "max_shifts_per_user_per_week": 5,
            "min_shifts_per_user_per_week": 2,
        }

    @staticmethod
    def get_oncall_rules() -> dict[str, Any]:
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
            "rotation_order": [],  # À remplir via configuration
            "start_day": "friday",
            "start_hour": 21,
            "duration_days": 7,
            "end_hour": 7,
        }
