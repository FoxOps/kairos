from flask import Blueprint, make_response, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.models import Shift, OnCall, Leave, User
from app.utils.export import export_to_ics

# Create blueprint
export_bp = Blueprint("export", __name__)


def _get_export_scope():
    """Récupère le scope de l'export depuis les paramètres de requête."""
    scope = request.args.get("scope", "all")
    if scope not in ["all", "my"]:
        scope = "all"
    return scope


def _filter_by_scope(query, model, scope, user):
    """Filtre une requête selon le scope (all ou my)."""
    if scope == "my":
        return query.filter(model.user_id == user.id)
    return query


def _get_user_from_token():
    """Récupère l'utilisateur à partir du token ICS."""
    token = request.args.get("token")
    if token:
        return User.query.filter_by(ics_token=token).first()
    return None


def _get_user_for_export():
    """
    Récupère l'utilisateur pour l'export.
    Si l'utilisateur est authentifié, utilise current_user.
    Sinon, vérifie si un token valide est fourni.
    """
    if current_user.is_authenticated:
        return current_user
    
    # Vérifier si un token est fourni
    token_user = _get_user_from_token()
    if token_user:
        return token_user
    
    return None


@export_bp.route("/export/shifts")
def export_shifts():
    """Export des shifts au format ICS."""
    # Vérifier l'authentification (session ou token)
    user = _get_user_for_export()
    
    if not user:
        # Si pas d'authentification, rediriger vers le login
        # Mais pour les requêtes externes (Thunderbird, etc.), on retourne une erreur 401
        if request.accept_mimetypes.accept_json or 'text/calendar' in request.accept_mimetypes:
            return "Unauthorized", 401
        return redirect(url_for("auth.login"))
    
    scope = _get_export_scope()

    query = Shift.query.options(joinedload(Shift.user)).order_by(Shift.start_time)

    filtered_query = _filter_by_scope(query, Shift, scope, user)
    shifts = filtered_query.all()

    ics_content = export_to_ics(shifts, f"Leviia Schedule - Shifts ({'All' if scope == 'all' else 'My'})")
    response = make_response(ics_content)
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    filename = f"shifts_{'all' if scope == 'all' else 'my'}.ics"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@export_bp.route("/export/oncall")
def export_oncall():
    """Export des astreintes au format ICS."""
    # Vérifier l'authentification (session ou token)
    user = _get_user_for_export()
    
    if not user:
        if request.accept_mimetypes.accept_json or 'text/calendar' in request.accept_mimetypes:
            return "Unauthorized", 401
        return redirect(url_for("auth.login"))
    
    scope = _get_export_scope()

    query = OnCall.query.options(joinedload(OnCall.user)).order_by(OnCall.start_time)

    filtered_query = _filter_by_scope(query, OnCall, scope, user)
    on_calls = filtered_query.all()

    ics_content = export_to_ics(on_calls, f"Leviia Schedule - OnCall ({'All' if scope == 'all' else 'My'})")
    response = make_response(ics_content)
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    filename = f"oncall_{'all' if scope == 'all' else 'my'}.ics"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@export_bp.route("/export/leaves")
def export_leaves():
    """Export des congés au format ICS."""
    # Vérifier l'authentification (session ou token)
    user = _get_user_for_export()
    
    if not user:
        if request.accept_mimetypes.accept_json or 'text/calendar' in request.accept_mimetypes:
            return "Unauthorized", 401
        return redirect(url_for("auth.login"))
    
    scope = _get_export_scope()

    query = Leave.query.options(joinedload(Leave.user)).order_by(Leave.start_date)

    filtered_query = _filter_by_scope(query, Leave, scope, user)
    leaves = filtered_query.all()

    ics_content = export_to_ics(leaves, f"Leviia Schedule - Leaves ({'All' if scope == 'all' else 'My'})")
    response = make_response(ics_content)
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    filename = f"leaves_{'all' if scope == 'all' else 'my'}.ics"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
