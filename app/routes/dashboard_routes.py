"""
Routes for the home page (calendar) and the user dashboard. Registered
on main_bp (see app/routes/main.py).
"""

from datetime import datetime

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.routes.main import main_bp
from app.services import DashboardService, ScheduleService

# Hard ceiling on a single api_get_shifts() request's span, independent
# of the ±180-day *default* (ScheduleService.CALENDAR_WINDOW_DAYS) - the
# default no longer caps anything once start/end are supplied (see that
# function's docstring), so without this a client could request e.g.
# start=0001-01-01&end=9999-12-31 and force a full-table scan of every
# shift/on-call/leave ever created on every request. 730 days (2 years)
# comfortably covers any legitimate admin workflow (generating a
# schedule a year or more ahead, per the real report that motivated
# dropping the old fixed window) while keeping a single request's query
# cost bounded.
MAX_CALENDAR_RANGE_DAYS = 730


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
    doesn't pass them keeps working unchanged. A range wider than
    MAX_CALENDAR_RANGE_DAYS, or with end before start, is rejected the
    same way as an unparseable one (falls back to the default window)
    rather than trusting an arbitrarily large client-supplied span for
    the underlying query - see that constant's own docstring."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    window_start = _parse_calendar_bound(start_str) if start_str else None
    window_end = _parse_calendar_bound(end_str) if end_str else None

    if (
        window_start is None
        or window_end is None
        or window_end <= window_start
        or (window_end - window_start).days > MAX_CALENDAR_RANGE_DAYS
    ):
        window_start, window_end = ScheduleService.calendar_window()

    events = ScheduleService.get_calendar_events_for_range(
        current_user, window_start, window_end
    )
    return jsonify(events)


@main_bp.route("/dashboard")
@login_required
def user_dashboard():
    """User dashboard - personalized overview."""
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    return render_template("dashboard.html", user=current_user, **dashboard_data)
