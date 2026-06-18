from app.models import Shift, OnCall, Leave
from datetime import datetime, timedelta
from app import db


def is_user_on_shift(user_id, target_date):
    """Vérifie si un utilisateur a déjà un shift le jour donné."""
    return db.session.query(
        db.exists().where(
            Shift.user_id == user_id,
            Shift.date == target_date
        )
    ).scalar()


def is_user_on_leave(user_id, target_date):
    """Vérifie si un utilisateur est en congé à une date donnée."""
    return db.session.query(
        db.exists().where(
            Leave.user_id == user_id,
            Leave.start_date <= target_date,
            Leave.end_date >= target_date
        )
    ).scalar()


def _has_overlapping_oncall(user_id, start_time, end_time):
    """Vérifie si l'utilisateur a déjà une astreinte qui chevauche la période."""
    return db.session.query(
        db.exists().where(
            OnCall.user_id == user_id,
            OnCall.start_time < end_time,
            OnCall.end_time > start_time
        )
    ).scalar()


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

    # Vérification optimisée : une seule requête pour vérifier les congés sur la période
    end_date = start_date + timedelta(days=7)
    overlapping_leave = db.session.query(
        db.exists().where(
            Leave.user_id == user_id,
            Leave.start_date <= end_date,
            Leave.end_date >= start_date
        )
    ).scalar()
    
    if overlapping_leave:
        # Trouver la date exacte du congé pour le message
        leave = Leave.query.filter(
            Leave.user_id == user_id,
            Leave.start_date <= end_date,
            Leave.end_date >= start_date
        ).first()
        if leave:
            return False, f"Impossible : l'utilisateur est en congé le {leave.start_date.strftime('%d/%m/%Y')}."

    return True, ""


def can_add_leave(user_id, start_date, end_date):
    """Vérifie si un congé peut être ajouté pour un utilisateur."""
    if start_date > end_date:
        return False, "La date de début doit être antérieure à la date de fin."

    # Vérification optimisée : une seule requête pour les congés chevauchants
    overlapping_leave = db.session.query(
        db.exists().where(
            Leave.user_id == user_id,
            Leave.start_date <= end_date,
            Leave.end_date >= start_date
        )
    ).scalar()
    if overlapping_leave:
        return False, "Impossible : un congé existe déjà sur cette période."

    # Vérification optimisée : une seule requête pour les shifts sur la période
    overlapping_shift = db.session.query(
        db.exists().where(
            Shift.user_id == user_id,
            Shift.date >= start_date,
            Shift.date <= end_date
        )
    ).scalar()
    if overlapping_shift:
        # Trouver le shift exact pour le message
        shift = Shift.query.filter(
            Shift.user_id == user_id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).first()
        if shift:
            return False, f"Impossible : l'utilisateur a un shift le {shift.date.strftime('%d/%m/%Y')}."

    # Vérification optimisée : une seule requête pour les astreintes chevauchantes
    overlapping_oncall = db.session.query(
        db.exists().where(
            OnCall.user_id == user_id,
            OnCall.start_time < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(start_date, datetime.min.time()),
        )
    ).scalar()
    if overlapping_oncall:
        return False, "Impossible : l'utilisateur a une astreinte sur cette période."

    return True, ""
