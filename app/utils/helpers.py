# ========== FICHIER: app/utils/helpers.py (version finale) ==========
from app.models import Shift, OnCall, Leave, User
from datetime import datetime, timedelta


def is_user_on_shift(user_id, target_date):
    """Vérifie si un utilisateur a déjà un shift le jour donné."""
    return Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == target_date
    ).first() is not None


def is_user_on_13h21h_shift(user_id, target_date):
    """Vérifie si un utilisateur a un shift 13h-21h le jour donné."""
    return Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == target_date,
        Shift.shift_type == 'evening'  # 13h-21h
    ).first() is not None


def is_user_on_leave(user_id, target_date):
    """Vérifie si un utilisateur est en congé à une date donnée."""
    return Leave.query.filter(
        Leave.user_id == user_id,
        Leave.start_date <= target_date,
        Leave.end_date >= target_date
    ).first() is not None


def can_add_shift(user_id, shift_date, shift_type):
    """
    Vérifie si un shift peut être ajouté pour un utilisateur à une date donnée.
    Règles :
    - Une personne ne peut pas avoir 2 shifts le même jour.
    - Une personne en congé ne peut pas avoir de shift.
    - Les shifts ne peuvent être ajoutés que du lundi au vendredi.
    """
    if is_user_on_leave(user_id, shift_date):
        return False, "Impossible : l'utilisateur est en congé à cette date."
    if is_user_on_shift(user_id, shift_date):
        return False, "Impossible : l'utilisateur a déjà un shift ce jour-là."
    if shift_date.weekday() >= 5:  # 5 = samedi, 6 = dimanche
        return False, "Impossible : les shifts ne peuvent être ajoutés que du lundi au vendredi."
    return True, ""


def can_add_oncall(user_id, oncall_start_time):
    """
    Vérifie si une astreinte peut être ajoutée pour un utilisateur.
    Règles :
    - L'astreinte doit commencer un vendredi à 21h.
    - L'utilisateur ne doit pas être en congé pendant les 7 jours.
    
    Args:
        user_id (int): ID de l'utilisateur.
        oncall_start_time (datetime): Date/heure de début de l'astreinte (doit être un vendredi à 21h).
    
    Returns:
        tuple: (bool, str) -> (True, "") si OK, (False, "erreur") sinon.
    """
    start_date = oncall_start_time.date()
    start_time = oncall_start_time.time()
    
    # Vérifier que le premier jour est un vendredi et commence à 21h
    if start_date.weekday() != 4 or start_time.hour != 21:  # 4 = vendredi, 21h
        return False, "L'astreinte doit commencer un vendredi à 21h."
    
    # Vérifier que l'utilisateur n'est pas en congé pendant les 7 jours
    end_date = start_date + timedelta(days=7)
    current_date = start_date
    while current_date <= end_date:
        if is_user_on_leave(user_id, current_date):
            return False, f"Impossible : l'utilisateur est en congé le {current_date.strftime('%d/%m/%Y')}."
        current_date += timedelta(days=1)
    
    return True, ""


def can_add_leave(user_id, start_date, end_date):
    """Vérifie si un congé peut être ajouté pour un utilisateur."""
    if start_date > end_date:
        return False, "La date de début doit être antérieure à la date de fin."
    return True, ""