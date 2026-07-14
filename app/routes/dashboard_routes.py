"""
Routes pour l'accueil (calendrier) et le tableau de bord utilisateur.
Enregistrées sur main_bp (cf. app/routes/main.py).
"""

from datetime import date, datetime

from flask import jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app.models import Leave, OnCall, Shift, ShiftType
from app.routes.main import main_bp
from app.services import ScheduleService
from app.utils.optimizations import eager_load


@main_bp.route("/")
@login_required
@eager_load(Shift, ["user", "shift_type"])
@eager_load(OnCall, ["user"])
@eager_load(Leave, ["user"])
def index():
    """Page d'accueil - accessible uniquement aux utilisateurs connectés."""
    events = ScheduleService.get_calendar_events()
    return render_template("index.html", events=events)


@main_bp.route("/api/shifts", methods=["GET"])
@login_required
def api_get_shifts():
    """API endpoint pour récupérer les shifts au format JSON pour FullCalendar."""
    events = ScheduleService.get_calendar_events()
    return jsonify(events)


@main_bp.route("/dashboard")
@login_required
def user_dashboard():
    """Tableau de bord utilisateur - Vue d'ensemble personnalisée."""
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

    shift_types_stats = []
    shift_types = ShiftType.query.all()
    for shift_type in shift_types:
        count = Shift.query.filter_by(
            user_id=user_id, shift_type_id=shift_type.id
        ).count()
        if count > 0:
            shift_types_stats.append(
                {
                    "id": shift_type.id,
                    "name": shift_type.name,
                    "label": shift_type.label,
                    "count": count,
                }
            )

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
        oncalls_this_month=oncalls_this_month,
        user=current_user,
    )
