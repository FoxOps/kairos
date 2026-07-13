from flask import Blueprint, make_response, redirect, request, url_for

from app.services import ExportService

# Create blueprint
export_bp = Blueprint("export", __name__)


def _get_export_scope():
    """Récupère le scope de l'export depuis les paramètres de requête."""
    return ExportService.normalize_scope(request.args.get("scope"))


def _get_user_for_export():
    """
    Récupère l'utilisateur pour l'export.
    Si l'utilisateur est authentifié, utilise current_user.
    Sinon, vérifie si un token valide est fourni.
    """
    return ExportService.resolve_user(request.args.get("token"))


def _ics_response(ics_content: str, filename: str):
    response = make_response(ics_content)
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def _unauthorized_response():
    if (
        request.accept_mimetypes.accept_json
        or "text/calendar" in request.accept_mimetypes
    ):
        return "Unauthorized", 401
    return redirect(url_for("auth.login"))


@export_bp.route("/export/shifts")
def export_shifts():
    """Export des shifts au format ICS."""
    user = _get_user_for_export()
    if not user:
        return _unauthorized_response()

    scope = _get_export_scope()
    ics_content = ExportService.export_shifts(scope, user)
    return _ics_response(ics_content, f"shifts_{'all' if scope == 'all' else 'my'}.ics")


@export_bp.route("/export/oncall")
def export_oncall():
    """Export des astreintes au format ICS."""
    user = _get_user_for_export()
    if not user:
        return _unauthorized_response()

    scope = _get_export_scope()
    ics_content = ExportService.export_oncall(scope, user)
    return _ics_response(ics_content, f"oncall_{'all' if scope == 'all' else 'my'}.ics")


@export_bp.route("/export/leaves")
def export_leaves():
    """Export des congés au format ICS."""
    user = _get_user_for_export()
    if not user:
        return _unauthorized_response()

    scope = _get_export_scope()
    ics_content = ExportService.export_leaves(scope, user)
    return _ics_response(ics_content, f"leaves_{'all' if scope == 'all' else 'my'}.ics")
