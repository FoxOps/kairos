from app.models import Shift, OnCall, Leave
from datetime import datetime, timedelta


def is_user_on_shift(user_id, target_date):
    """Vérifie si un utilisateur a déjà un shift le jour donné."""
    return Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == target_date
    ).first() is not None


def is_user_on_leave(user_id, target_date):
    """Vérifie si un utilisateur est en congé à une date donnée."""
    return Leave.query.filter(
        Leave.user_id == user_id,
        Leave.start_date <= target_date,
        Leave.end_date >= target_date
    ).first() is not None


def _has_overlapping_oncall(user_id, start_time, end_time):
    """Vérifie si l'utilisateur a déjà une astreinte qui chevauche la période."""
    return OnCall.query.filter(
        OnCall.user_id == user_id,
        OnCall.start_time < end_time,
        OnCall.end_time > start_time
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
    if shift_date.weekday() >= 5:
        return False, "Impossible : les shifts ne peuvent être ajoutés que du lundi au vendredi."
    return True, ""


def can_add_oncall(user_id, oncall_start_time, oncall_end_time):
    """
    Vérifie si une astreinte peut être ajoutée pour un utilisateur.
    Règles :
    - L'astreinte doit commencer un vendredi à 21h.
    - L'utilisateur ne doit pas être en congé pendant la période.
    - L'utilisateur ne doit pas avoir d'astreinte qui chevauche.
    """
    start_date = oncall_start_time.date()
    start_time = oncall_start_time.time()

    if start_date.weekday() != 4 or start_time.hour != 21:
        return False, "L'astreinte doit commencer un vendredi à 21h."

    if _has_overlapping_oncall(user_id, oncall_start_time, oncall_end_time):
        return False, "Impossible : l'utilisateur a déjà une astreinte sur cette période."

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

    overlapping_leave = Leave.query.filter(
        Leave.user_id == user_id,
        Leave.start_date <= end_date,
        Leave.end_date >= start_date
    ).first()
    if overlapping_leave:
        return False, "Impossible : un congé existe déjà sur cette période."

    current_date = start_date
    while current_date <= end_date:
        if is_user_on_shift(user_id, current_date):
            return False, f"Impossible : l'utilisateur a un shift le {current_date.strftime('%d/%m/%Y')}."
        current_date += timedelta(days=1)

    overlapping_oncall = OnCall.query.filter(
        OnCall.user_id == user_id,
        OnCall.start_time < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
        OnCall.end_time > datetime.combine(start_date, datetime.min.time()),
    ).first()
    if overlapping_oncall:
        return False, "Impossible : l'utilisateur a une astreinte sur cette période."

    return True, ""
