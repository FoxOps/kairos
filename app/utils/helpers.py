from datetime import datetime, timedelta
from app import db
from app.models import Shift, OnCall, Leave


def is_user_on_shift(user_id, target_date):
    """Vérifie si un utilisateur a déjà un shift le jour donné."""
    return db.session.query(
        db.exists().where(Shift.user_id == user_id, Shift.date == target_date)
    ).scalar()


def is_user_on_leave(user_id, target_date):
    """Vérifie si un utilisateur est en congé à une date donnée."""
    return db.session.query(
        db.exists().where(
            Leave.user_id == user_id,
            Leave.start_date <= target_date,
            Leave.end_date >= target_date,
        )
    ).scalar()


def _has_overlapping_oncall(user_id, start_time, end_time):
    """Vérifie si l'utilisateur a déjà une astreinte qui chevauche la période."""
    return db.session.query(
        db.exists().where(
            OnCall.user_id == user_id,
            OnCall.start_time < end_time,
            OnCall.end_time > start_time,
        )
    ).scalar()


def _get_overlapping_leave(user_id, start_date, end_date):
    """Récupère le premier congé chevauchant la période."""
    return (
        db.session.query(Leave)
        .filter(
            Leave.user_id == user_id,
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        )
        .first()
    )


def _get_overlapping_shift(user_id, start_date, end_date):
    """Récupère le premier shift chevauchant la période."""
    return (
        db.session.query(Shift)
        .filter(
            Shift.user_id == user_id, Shift.date >= start_date, Shift.date <= end_date
        )
        .first()
    )


def _get_overlapping_oncall(user_id, start_date, end_date):
    """Récupère la première astreinte chevauchant la période."""
    return (
        db.session.query(OnCall)
        .filter(
            OnCall.user_id == user_id,
            OnCall.start_time
            < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
            OnCall.end_time > datetime.combine(start_date, datetime.min.time()),
        )
        .first()
    )


# ============================================================================
# FONCTIONS OPTIMISÉES POUR LES VÉRIFICATIONS BATCH
# ============================================================================

def check_users_on_shift(user_ids, target_date):
    """
    Vérifie quels utilisateurs ont déjà un shift à une date donnée.
    Optimisation : une seule requête pour tous les utilisateurs.
    
    Args:
        user_ids: Liste des IDs d'utilisateurs à vérifier
        target_date: Date à vérifier
    
    Returns:
        Set des IDs d'utilisateurs qui ont déjà un shift
    """
    if not user_ids:
        return set()
    
    results = db.session.query(Shift.user_id).filter(
        Shift.user_id.in_(user_ids),
        Shift.date == target_date
    ).all()
    return {r.user_id for r in results}


def check_users_on_leave(user_ids, target_date):
    """
    Vérifie quels utilisateurs sont en congé à une date donnée.
    Optimisation : une seule requête pour tous les utilisateurs.
    
    Args:
        user_ids: Liste des IDs d'utilisateurs à vérifier
        target_date: Date à vérifier
    
    Returns:
        Set des IDs d'utilisateurs qui sont en congé
    """
    if not user_ids:
        return set()
    
    results = db.session.query(Leave.user_id).filter(
        Leave.user_id.in_(user_ids),
        Leave.start_date <= target_date,
        Leave.end_date >= target_date,
    ).all()
    return {r.user_id for r in results}


def check_users_overlapping_oncall(user_ids, start_time, end_time):
    """
    Vérifie quels utilisateurs ont une astreinte qui chevauche la période.
    Optimisation : une seule requête pour tous les utilisateurs.
    
    Args:
        user_ids: Liste des IDs d'utilisateurs à vérifier
        start_time: Date/heure de début de la période
        end_time: Date/heure de fin de la période
    
    Returns:
        Set des IDs d'utilisateurs qui ont une astreinte chevauchante
    """
    if not user_ids:
        return set()
    
    results = db.session.query(OnCall.user_id).filter(
        OnCall.user_id.in_(user_ids),
        OnCall.start_time < end_time,
        OnCall.end_time > start_time,
    ).all()
    return {r.user_id for r in results}


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
        return (
            False,
            "Impossible : les shifts ne peuvent être ajoutés que du lundi au vendredi.",
        )
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
        return (
            False,
            "Impossible : l'utilisateur a déjà une astreinte sur cette période.",
        )

    # Vérification optimisée : une seule requête pour vérifier et récupérer le congé
    overlapping_leave = _get_overlapping_leave(
        user_id, start_date, start_date + timedelta(days=7)
    )
    if overlapping_leave:
        return (
            False,
            f"Impossible : l'utilisateur est en congé le {overlapping_leave.start_date.strftime('%d/%m/%Y')}.",
        )

    return True, ""


def can_add_leave(user_id, start_date, end_date):
    """Vérifie si un congé peut être ajouté pour un utilisateur."""
    if start_date > end_date:
        return False, "La date de début doit être antérieure à la date de fin."

    # Vérification optimisée : une seule requête pour les congés chevauchants
    overlapping_leave = _get_overlapping_leave(user_id, start_date, end_date)
    if overlapping_leave:
        return False, "Impossible : un congé existe déjà sur cette période."

    # Note: Les shifts et astreintes ne bloquent pas les congés - les congés sont prioritaires
    # Les shifts et astreintes existants seront gérés séparément (suppression automatique et recalcul)

    return True, ""
