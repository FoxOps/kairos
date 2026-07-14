"""
Common helper functions for Leviia Schedule.

This module provides general utility functions used throughout the application.
"""

import os
from datetime import date, datetime, time, timedelta

from flask_login import current_user

from app import db
from app.models import Leave, OnCall, Shift


def get_bool(env_var: str, default: bool = False) -> bool:
    """Get a boolean value from environment variable."""
    value = os.environ.get(env_var)
    if value is None:
        return default
    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "y", "on"):
        return True
    elif value_lower in ("false", "0", "no", "n", "off"):
        return False
    return default


def get_int(env_var: str, default: int = 0) -> int:
    """Get an integer value from environment variable."""
    value = os.environ.get(env_var)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def format_date(d: date, format_str: str = "%Y-%m-%d") -> str:
    """
    Format a date object as a string.

    Args:
        d: Date object to format
        format_str: Format string (default: YYYY-MM-DD)

    Returns:
        Formatted date string
    """
    if d is None:
        return ""
    return d.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.

    Args:
        dt: Datetime object to format
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    return dt.strftime(format_str)


def format_time(t: time, format_str: str = "%H:%M") -> str:
    """
    Format a time object as a string.

    Args:
        t: Time object to format
        format_str: Format string (default: HH:MM)

    Returns:
        Formatted time string
    """
    if t is None:
        return ""
    return t.strftime(format_str)


_FR_WEEKDAYS_ABBR = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def format_date_fr(d: date | datetime | None, format_str: str = "%a %d/%m") -> str:
    """
    Format a date/datetime with a French weekday abbreviation for %a,
    independent of the server's OS locale (%a/%A depend on locale.setlocale,
    fragile/process-global in a WSGI app - defaults to English abbreviations
    here otherwise).

    Args:
        d: Date or datetime object to format
        format_str: Format string, may contain %a (default: "%a %d/%m")

    Returns:
        Formatted date string, or "" if d is None
    """
    if d is None:
        return ""
    resolved_format = format_str.replace("%a", _FR_WEEKDAYS_ABBR[d.weekday()])
    return d.strftime(resolved_format)


# Palette de couleurs sémantiques daisyUI (voir app/static/css/theme-colors.css)
# utilisée pour distinguer visuellement les types de shifts sur le dashboard
# (graphique + badges) - "error" volontairement exclu (connotation négative
# trompeuse pour un simple type de shift).
SHIFT_TYPE_COLOR_PALETTE = [
    "primary",
    "secondary",
    "accent",
    "info",
    "success",
    "warning",
]


def shift_type_color(shift_type_id: int | None) -> str:
    """
    Nom de couleur sémantique daisyUI déterministe pour un type de shift,
    pour qu'un même type ait toujours la même couleur partout sur le
    dashboard (pas de colonne "couleur" sur ShiftType, calculé à la volée).

    Args:
        shift_type_id: ID du ShiftType (peut être None)

    Returns:
        Nom de couleur daisyUI (ex: "primary", "accent")
    """
    if shift_type_id is None:
        return "neutral"
    return SHIFT_TYPE_COLOR_PALETTE[shift_type_id % len(SHIFT_TYPE_COLOR_PALETTE)]


def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> date | None:
    """
    Parse a string into a date object.

    Args:
        date_str: String to parse
        format_str: Format string (default: YYYY-MM-DD)

    Returns:
        Date object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, format_str).date()
    except (ValueError, TypeError):
        return None


def parse_datetime(
    dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> datetime | None:
    """
    Parse a string into a datetime object.

    Args:
        dt_str: String to parse
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)

    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(dt_str, format_str)
    except (ValueError, TypeError):
        return None


def get_current_year() -> int:
    """Get the current year."""
    return datetime.now().year


def get_current_month() -> int:
    """Get the current month (1-12)."""
    return datetime.now().month


def get_days_in_month(year: int, month: int) -> int:
    """
    Get the number of days in a month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Number of days in the month
    """
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, 12, 1)).days
    else:
        return (date(year, month + 1, 1) - date(year, month, 1)).days


# ---------------------------------------------------------------------------
# Permission helper functions (for compatibility with existing code)
# ---------------------------------------------------------------------------


def can_add_shift(user=None, date=None, shift_type_id=None):
    """
    Check if a user can add a shift on a specific date.

    Args:
        user: User to check (default: current_user)
        date: Date to check (default: today)
        shift_type_id: Shift type ID to check

    Returns:
        True if user can add a shift, False otherwise
    """
    if user is None:
        user = current_user

    if date is None:
        date = datetime.now().date()

    if not user or not user.is_authenticated:
        return False

    # Les shifts ne peuvent être ajoutés que du lundi au vendredi
    if date.weekday() >= 5:
        return False

    # L'utilisateur ne peut pas avoir de shift s'il est en congé
    if is_user_on_leave(user.id, date):
        return False

    # Check if user already has a shift on this date
    return not is_user_on_shift(user.id, date)


def can_add_leave(user=None, start_date=None, end_date=None, exclude_leave_id=None):
    """
    Check if a user can add a leave for a specific period.

    Args:
        user: User to check (default: current_user)
        start_date: Start date of leave
        end_date: End date of leave
        exclude_leave_id: Leave id to ignore when checking the minimum
            headcount (used when modifying an existing leave's dates,
            so it doesn't count itself as "someone else on leave")

    Returns:
        True if user can add leave, False otherwise
    """
    if user is None:
        user = current_user

    if start_date is None or end_date is None:
        return False

    if not user or not user.is_authenticated:
        return False

    # La date de début doit être antérieure (ou égale) à la date de fin
    if start_date > end_date:
        return False

    # Check if user already has a leave overlapping with this period
    overlapping_leave = Leave.query.filter(
        Leave.user_id == user.id,
        Leave.start_date <= end_date,
        Leave.end_date >= start_date,
    ).first()

    if overlapping_leave is not None:
        return False

    # Règle 6 : effectif minimum 1 personne, jamais 0. Un congé ne peut pas
    # faire tomber l'effectif disponible d'un jour couvert (parmi les
    # utilisateurs éligibles pour les shifts) à 0.
    return leave_keeps_minimum_headcount(user, start_date, end_date, exclude_leave_id)


def leave_keeps_minimum_headcount(
    user, start_date: date, end_date: date, exclude_leave_id=None
) -> bool:
    """Vérifie que le congé [start_date, end_date] ne fait tomber
    l'effectif disponible (utilisateurs de groupes schedule, hors congés)
    à 0 pour aucun jour ouvré couvert. Ne s'applique qu'aux utilisateurs
    éligibles pour les shifts - le congé de quelqu'un hors de ces groupes
    n'affecte pas cet effectif."""
    from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation

    schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
    schedule_user_ids = {u.id for u in schedule_users}

    if user.id not in schedule_user_ids:
        return True

    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Shifts générés du lundi au vendredi
            leave_query = Leave.query.filter(
                Leave.user_id.in_(schedule_user_ids),
                Leave.user_id != user.id,
                Leave.start_date <= current_date,
                Leave.end_date >= current_date,
            )
            if exclude_leave_id is not None:
                leave_query = leave_query.filter(Leave.id != exclude_leave_id)
            other_users_on_leave = {leave.user_id for leave in leave_query.all()}

            # -1 pour l'utilisateur qui demande ce congé : il quitte
            # l'effectif disponible ce jour-là.
            available_after = len(schedule_user_ids) - len(other_users_on_leave) - 1
            if available_after < 1:
                return False
        current_date += timedelta(days=1)

    return True


def can_add_oncall(user=None, start_time=None, end_time=None):
    """
    Check if a user can add an on-call duty for a specific period.

    Args:
        user: User to check (default: current_user)
        start_time: Start datetime of on-call
        end_time: End datetime of on-call

    Returns:
        True if user can add on-call, False otherwise
    """
    if user is None:
        user = current_user

    if start_time is None or end_time is None:
        return False

    if not user or not user.is_authenticated:
        return False

    # L'astreinte doit commencer un vendredi à 21h
    if start_time.weekday() != 4 or start_time.hour != 21:
        return False

    # L'utilisateur ne peut pas avoir d'astreinte s'il est en congé sur la période
    if _get_overlapping_leave(user.id, start_time.date(), end_time.date()):
        return False

    # Check if user already has an on-call overlapping with this period
    overlapping_oncall = OnCall.query.filter(
        OnCall.user_id == user.id,
        OnCall.start_time <= end_time,
        OnCall.end_time >= start_time,
    ).first()

    return overlapping_oncall is None


# ---------------------------------------------------------------------------
# Overlap checking functions (for compatibility with existing code)
# ---------------------------------------------------------------------------


def is_user_on_shift(user_id, target_date):
    """Check if a user already has a shift on the given date."""
    return db.session.query(
        db.exists().where(Shift.user_id == user_id, Shift.date == target_date)
    ).scalar()


def is_user_on_leave(user_id, target_date):
    """Check if a user is on leave on the given date."""
    return db.session.query(
        db.exists().where(
            Leave.user_id == user_id,
            Leave.start_date <= target_date,
            Leave.end_date >= target_date,
        )
    ).scalar()


def _has_overlapping_oncall(user_id, start_time, end_time):
    """Check if user already has an on-call that overlaps with the period."""
    return db.session.query(
        db.exists().where(
            OnCall.user_id == user_id,
            OnCall.start_time < end_time,
            OnCall.end_time > start_time,
        )
    ).scalar()


def _get_overlapping_leave(user_id, start_date, end_date):
    """Get the first leave overlapping with the period."""
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
    """Get the first shift overlapping with the period."""
    return (
        db.session.query(Shift)
        .filter(
            Shift.user_id == user_id, Shift.date >= start_date, Shift.date <= end_date
        )
        .first()
    )


def _get_overlapping_oncall(user_id, start_date, end_date):
    """Get the first on-call overlapping with the period."""
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
