"""
Routes for the home page (calendar) and the user dashboard. Registered
on main_bp (see app/routes/main.py).
"""

from datetime import date, datetime

from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models import Leave, OnCall, Shift, ShiftType
from app.routes.main import main_bp
from app.services import ScheduleService
from app.utils.helpers import build_shift_type_color_map


@main_bp.route("/")
@login_required
def index():
    """Home page - only accessible to logged-in users. The calendar
    itself is populated client-side by FullCalendar fetching /api/shifts
    for whatever range it's currently viewing (see
    fullcalendar-config.js) - no events are embedded server-side here
    anymore, so navigating far into the past/future is never capped by
    a fixed window (see api_get_shifts()'s own docstring)."""
    return render_template("index.html")


def _parse_calendar_bound(value: str) -> datetime | None:
    """FullCalendar sends fetchInfo.startStr/endStr as ISO 8601 - a
    trailing 'Z' (UTC designator) isn't accepted by datetime.fromisoformat()
    on Python < 3.11, so it's normalized to '+00:00' first; the
    resulting tzinfo is then dropped since every stored shift/on-call
    datetime is naive org-local time (see "Multi-timezone support"),
    comparing an aware value against them would raise. Returns None on
    anything unparseable, letting the caller fall back to the default
    window instead of erroring the whole request over a malformed
    query param."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


@main_bp.route("/api/shifts", methods=["GET"])
@login_required
def api_get_shifts():
    """JSON events for FullCalendar (session-cookie auth, internal to
    this app's own frontend - not the public /api/v1/* REST API).
    Used as FullCalendar's dynamic events source: called with start/end
    query params for whatever range the calendar is currently viewing,
    so navigating far into the past/future always fetches real data
    instead of being capped by a fixed embedded window (the previous
    design: a static JSON blob embedded once at page load, ±180 days -
    a schedule generated further out than that, a real workflow tested
    directly against this app, would silently never appear in the
    calendar with no indication why). start/end omitted or unparseable
    falls back to that same ±180-day default, so any caller that
    doesn't pass them keeps working unchanged."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    window_start = _parse_calendar_bound(start_str) if start_str else None
    window_end = _parse_calendar_bound(end_str) if end_str else None

    if window_start is None or window_end is None:
        window_start, window_end = ScheduleService.calendar_window()

    events = ScheduleService.get_calendar_events_for_range(
        current_user, window_start, window_end
    )
    return jsonify(events)


@main_bp.route("/dashboard")
@login_required
def user_dashboard():
    """User dashboard - personalized overview."""
    user_id = current_user.id

    total_shifts = Shift.query.filter_by(user_id=user_id).count()
    total_oncalls = OnCall.query.filter_by(user_id=user_id).count()
    total_leaves = Leave.query.filter_by(user_id=user_id).count()

    now = datetime.now()
    upcoming_shifts = (
        Shift.query.options(joinedload(Shift.shift_type))
        .filter(Shift.user_id == user_id, Shift.start_time >= now)
        .order_by(Shift.start_time)
        .limit(5)
        .all()
    )

    upcoming_oncalls = (
        OnCall.query.filter(OnCall.user_id == user_id, OnCall.start_time >= now)
        .order_by(OnCall.start_time)
        .limit(5)
        .all()
    )

    today = date.today()
    upcoming_leaves = (
        Leave.query.filter(Leave.user_id == user_id, Leave.start_date >= today)
        .order_by(Leave.start_date)
        .limit(5)
        .all()
    )

    recent_shifts = (
        Shift.query.options(joinedload(Shift.shift_type))
        .filter(Shift.user_id == user_id, Shift.end_time <= now)
        .order_by(Shift.end_time.desc())
        .limit(5)
        .all()
    )

    shift_types = ShiftType.query.all()
    # A .count() per shift type (loop) used to run as many queries as
    # there were types - replaced with a single GROUP BY.
    counts_by_type_id = dict(
        db.session.query(Shift.shift_type_id, func.count(Shift.id))
        .filter(Shift.user_id == user_id)
        .group_by(Shift.shift_type_id)
        .all()
    )
    shift_types_stats = [
        {
            "id": shift_type.id,
            "name": shift_type.name,
            "label": shift_type.label,
            "count": counts_by_type_id[shift_type.id],
        }
        for shift_type in shift_types
        if counts_by_type_id.get(shift_type.id, 0) > 0
    ]

    # By rank among the existing types (not by id % palette size),
    # otherwise two types whose IDs differ by a multiple of the palette
    # size end up with the same color.
    shift_type_colors = build_shift_type_color_map(st.id for st in shift_types)

    first_day_of_month = date(today.year, today.month, 1)
    oncalls_this_month = OnCall.query.filter(
        OnCall.user_id == user_id,
        OnCall.start_time >= datetime.combine(first_day_of_month, datetime.min.time()),
        OnCall.end_time <= datetime.combine(today, datetime.max.time()),
    ).count()

    return render_template(
        "dashboard.html",
        total_shifts=total_shifts,
        total_oncalls=total_oncalls,
        total_leaves=total_leaves,
        upcoming_shifts=upcoming_shifts,
        upcoming_oncalls=upcoming_oncalls,
        upcoming_leaves=upcoming_leaves,
        recent_shifts=recent_shifts,
        shift_types_stats=shift_types_stats,
        shift_type_colors=shift_type_colors,
        oncalls_this_month=oncalls_this_month,
        user=current_user,
    )
