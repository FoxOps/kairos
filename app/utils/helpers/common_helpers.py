"""
Common helper functions for Kairos.

This module provides general utility functions used throughout the application.
"""

from datetime import date, datetime, timedelta
from zoneinfo import available_timezones

from flask_babel import gettext as _
from flask_login import current_user

from app import db
from app.models import Leave, OnCall, Shift


def get_timezone_choices() -> list[str]:
    """Sorted IANA timezone names, for the /profile/settings and
    /admin/settings timezone <select> dropdowns."""
    return sorted(available_timezones())


LANGUAGE_CHOICES: list[tuple[str, str]] = [("fr", "Français"), ("en", "English")]


def get_language_choices() -> list[tuple[str, str]]:
    """(code, display name) pairs for the /profile/settings and
    /admin/settings language <select> dropdowns. Tuples rather than bare
    codes (unlike get_timezone_choices()) - "fr"/"en" aren't
    self-explanatory the way IANA timezone names are."""
    return LANGUAGE_CHOICES


_FR_WEEKDAYS_ABBR = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
_EN_WEEKDAYS_ABBR = ["Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun."]


def format_date_fr(d: date | datetime | None, format_str: str = "%a %d/%m") -> str:
    """
    Format a date/datetime with a locale-aware weekday abbreviation for
    %a, independent of the server's OS locale (%a/%A depend on
    locale.setlocale, fragile/process-global in a WSGI app - defaults to
    English abbreviations here otherwise). Locale comes from
    flask_babel.get_locale() - the currently *resolved* locale (same
    resolution order as everywhere else: viewer's own preference, else
    the org default). Deliberately not app.get_locale() (the
    locale_selector callback itself): calling that directly bypasses an
    active force_locale() override (e.g. per-recipient email rendering),
    while flask_babel.get_locale() correctly honors it.

    Args:
        d: Date or datetime object to format
        format_str: Format string, may contain %a (default: "%a %d/%m")

    Returns:
        Formatted date string, or "" if d is None
    """
    if d is None:
        return ""

    from flask_babel import get_locale

    weekdays = _EN_WEEKDAYS_ABBR if str(get_locale()) == "en" else _FR_WEEKDAYS_ABBR
    resolved_format = format_str.replace("%a", weekdays[d.weekday()])
    return d.strftime(resolved_format)


DATE_FORMAT_CHOICES: list[tuple[str, str]] = [
    ("%d/%m/%Y", datetime(2026, 12, 31).strftime("%d/%m/%Y")),
    ("%m/%d/%Y", datetime(2026, 12, 31).strftime("%m/%d/%Y")),
    ("%Y-%m-%d", datetime(2026, 12, 31).strftime("%Y-%m-%d")),
]
TIME_FORMAT_CHOICES: list[tuple[str, str]] = [
    ("%H:%M", datetime(2026, 12, 31, 14, 30).strftime("%H:%M")),
    ("%I:%M %p", datetime(2026, 12, 31, 14, 30).strftime("%I:%M %p")),
]


def get_date_format_choices() -> list[tuple[str, str]]:
    """(strftime pattern, rendered sample) pairs for the /profile/settings
    and /admin/settings date format <select> dropdowns. The sample is
    computed rather than hardcoded so it can never drift from what the
    pattern actually produces."""
    return DATE_FORMAT_CHOICES


def get_time_format_choices() -> list[tuple[str, str]]:
    """(strftime pattern, rendered sample) pairs for the date time format
    <select> dropdowns."""
    return TIME_FORMAT_CHOICES


def format_date(d: date | datetime | None) -> str:
    """Format a date/datetime using the viewer's effective date format
    (own preference, else the org default) - see app.get_date_format().
    Jinja filter: {{ shift.date|format_date }}."""
    if d is None:
        return ""

    from app import get_date_format

    return d.strftime(get_date_format())


def format_time(t: date | datetime | None) -> str:
    """Format a datetime/time using the viewer's effective time format -
    see app.get_time_format(). Jinja filter: {{ shift.start_time|format_time }}."""
    if t is None:
        return ""

    from app import get_time_format

    return t.strftime(get_time_format())


def format_datetime(dt: datetime | None) -> str:
    """format_date() + format_time() combined, space-separated. Jinja
    filter: {{ oncall.start_time|format_datetime }}."""
    if dt is None:
        return ""
    return f"{format_date(dt)} {format_time(dt)}"


# daisyUI semantic color palette (see app/static/css/theme-colors.css)
# used to visually distinguish shift types on the dashboard (chart +
# badges) - "error" deliberately excluded (misleadingly negative
# connotation for a plain shift type).
SHIFT_TYPE_COLOR_PALETTE = [
    "primary",
    "secondary",
    "accent",
    "info",
    "success",
    "warning",
]


def build_shift_type_color_map(shift_type_ids) -> dict:
    """
    Map each ShiftType.id to a daisyUI semantic color, guaranteed
    distinct for all passed IDs as long as there are at most
    len(SHIFT_TYPE_COLOR_PALETTE) of them (beyond that, the palette
    wraps around).

    Assigns by RANK (sorted order of the IDs), not by `id % len(palette)`:
    a modulo on the raw ID makes two types collide as soon as their IDs
    differ by a multiple of the palette size (e.g. IDs 2 and 8 with a
    palette of 6 both land on index 2) - a real bug observed in practice
    after deleting/recreating shift types, which pushes auto-incremented
    IDs up without them staying contiguous from 1.

    Args:
        shift_type_ids: ShiftType IDs to map (duplicates/None tolerated)

    Returns:
        Dict {shift_type_id: daisyui_color_name}
    """
    unique_sorted_ids = sorted({sid for sid in shift_type_ids if sid is not None})
    palette_size = len(SHIFT_TYPE_COLOR_PALETTE)
    return {
        shift_type_id: SHIFT_TYPE_COLOR_PALETTE[index % palette_size]
        for index, shift_type_id in enumerate(unique_sorted_ids)
    }


# ---------------------------------------------------------------------------
# Permission helper functions (for compatibility with existing code)
# ---------------------------------------------------------------------------


def _resolve_authenticated_user(user):
    """Resolve `user` to current_user if absent, or None if not
    authenticated - identical preamble repeated by can_add_shift/
    can_add_leave/can_add_oncall before each of their specific checks."""
    if user is None:
        user = current_user
    if not user or not user.is_authenticated:
        return None
    return user


def can_add_shift(user=None, date=None, shift_type=None):
    """
    Check if a user can add a shift on a specific date.

    Args:
        user: User to check (default: current_user)
        date: Date to check (default: today)
        shift_type: ShiftType the shift would use - optional (the
            configured-rule checks in check_shift_rule_violations()
            are skipped when not given, same "not enough information,
            don't block" stance as the rest of this function)

    Returns:
        True if user can add a shift, False otherwise
    """
    user = _resolve_authenticated_user(user)
    if user is None:
        return False

    if date is None:
        date = datetime.now().date()

    # Shifts can only be added Monday through Friday
    if date.weekday() >= 5:
        return False

    # The user can't have a shift while on leave
    if is_user_on_leave(user.id, date):
        return False

    # Check if user already has a shift on this date
    if is_user_on_shift(user.id, date):
        return False

    return check_shift_rule_violations(user, date, shift_type) is None


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
    user = _resolve_authenticated_user(user)
    if user is None:
        return False

    if start_date is None or end_date is None:
        return False

    # The start date must be before (or equal to) the end date
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

    # Rule 6: minimum headcount of 1 person, never 0. A leave can't make
    # the available headcount for a covered day (among users eligible
    # for shifts) drop to 0.
    return leave_keeps_minimum_headcount(user, start_date, end_date, exclude_leave_id)


def leave_keeps_minimum_headcount(
    user, start_date: date, end_date: date, exclude_leave_id=None
) -> bool:
    """Check that the leave [start_date, end_date] doesn't drop the
    available headcount (users in schedule groups, excluding leave) to
    0 for any covered business day. Only applies to users eligible for
    shifts - a leave for someone outside these groups doesn't affect
    this headcount."""
    from app.utils.automation.advanced_shift_automation import AdvancedShiftAutomation

    schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
    schedule_user_ids = {u.id for u in schedule_users}

    if user.id not in schedule_user_ids:
        return True

    # One query per business day replaced with a single query covering
    # the whole [start_date, end_date] period - the per-day overlap is
    # then checked in memory against this small list of leaves (count of
    # ongoing leaves, not count of days in the period).
    leave_query = Leave.query.filter(
        Leave.user_id.in_(schedule_user_ids),
        Leave.user_id != user.id,
        Leave.start_date <= end_date,
        Leave.end_date >= start_date,
    )
    if exclude_leave_id is not None:
        leave_query = leave_query.filter(Leave.id != exclude_leave_id)
    other_leaves = leave_query.all()

    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Shifts are generated Monday-Friday
            other_users_on_leave = {
                leave.user_id
                for leave in other_leaves
                if leave.start_date <= current_date <= leave.end_date
            }

            # -1 for the user requesting this leave: they leave the
            # available headcount that day.
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
    user = _resolve_authenticated_user(user)
    if user is None:
        return False

    if start_time is None or end_time is None:
        return False

    # On-call must start on a Friday at 9pm
    if start_time.weekday() != 4 or start_time.hour != 21:
        return False

    # The user can't have an on-call while on leave over the period
    if _get_overlapping_leave(user.id, start_time.date(), end_time.date()):
        return False

    # Check if user already has an on-call overlapping with this period
    overlapping_oncall = OnCall.query.filter(
        OnCall.user_id == user.id,
        OnCall.start_time <= end_time,
        OnCall.end_time >= start_time,
    ).first()
    if overlapping_oncall is not None:
        return False

    return check_oncall_rule_violations(user, start_time, end_time) is None


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


# ---------------------------------------------------------------------------
# Configurable automation rule checks (see app/utils/automation/rules/) -
# none of these 3 rule types existed in any form before this feature;
# each check is a no-op until an admin actually configures the rule
# (oncall_shift_overlap is the one exception, on by default - see its
# rule class docstring for why).
# ---------------------------------------------------------------------------


def check_shift_rule_violations(user, date, shift_type=None, exclude_shift_id=None):
    """Returns a translated error message if creating/moving a shift
    for `user` on `date` into `shift_type` would violate a configured
    automation rule (staffing_limits max, rest_after_oncall,
    oncall_shift_overlap), else None. `shift_type` is optional - the
    checks that need it (all 3, currently) are skipped when it's None.
    `exclude_shift_id`: the shift's own id, when checking a move
    (ShiftService.api_update) rather than a fresh creation - excludes
    it from the staffing_limits headcount so moving a shift to the
    same date/type it's already on doesn't count itself twice."""
    if shift_type is None:
        return None

    from app.utils.automation.rules import (
        OnCallShiftOverlapRule,
        RestAfterOnCallRule,
        StaffingLimitsRule,
    )

    limits = StaffingLimitsRule.get_limits(shift_type.id)
    if limits["max"] is not None:
        count_query = Shift.query.filter(
            Shift.shift_type_id == shift_type.id, Shift.date == date
        )
        if exclude_shift_id is not None:
            count_query = count_query.filter(Shift.id != exclude_shift_id)
        if count_query.count() >= limits["max"]:
            return _(
                "Impossible d'ajouter ce shift : effectif maximum (%(max)s) "
                "déjà atteint pour ce créneau.",
                max=limits["max"],
            )

    start_time = datetime.combine(date, datetime.min.time()).replace(
        hour=shift_type.start_hour
    )
    end_time = datetime.combine(date, datetime.min.time()).replace(
        hour=shift_type.end_hour
    )

    if OnCallShiftOverlapRule.resolve()["block"] and _has_overlapping_oncall(
        user.id, start_time, end_time
    ):
        return _(
            "Impossible d'ajouter ce shift : chevauche une astreinte de %(name)s.",
            name=user.name,
        )

    min_rest_hours = RestAfterOnCallRule.resolve()["min_rest_hours"]
    if min_rest_hours > 0:
        last_oncall = (
            OnCall.query.filter(
                OnCall.user_id == user.id, OnCall.end_time <= start_time
            )
            .order_by(OnCall.end_time.desc())
            .first()
        )
        if last_oncall and (start_time - last_oncall.end_time) < timedelta(
            hours=min_rest_hours
        ):
            return _(
                "Impossible d'ajouter ce shift : %(name)s doit se reposer "
                "%(hours)sh après son astreinte.",
                name=user.name,
                hours=min_rest_hours,
            )

    return None


def check_oncall_rule_violations(user, start_time, end_time, exclude_oncall_id=None):
    """Returns a translated error message if creating/moving an on-call
    for `user` over [start_time, end_time] would violate
    oncall_shift_overlap, else None. `exclude_oncall_id` is accepted
    for symmetry with check_shift_rule_violations() but unused here -
    the check queries Shift, not OnCall, so the on-call being moved
    never counts against itself."""
    from app.utils.automation.rules import OnCallShiftOverlapRule

    if OnCallShiftOverlapRule.resolve()["block"]:
        overlapping_shift = _get_overlapping_shift(
            user.id, start_time.date(), end_time.date()
        )
        if overlapping_shift is not None:
            return _(
                "Impossible d'ajouter cette astreinte : chevauche un shift de "
                "%(name)s.",
                name=user.name,
            )

    return None
