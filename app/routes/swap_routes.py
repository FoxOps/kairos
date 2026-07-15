"""
User routes for shift exchanges (request, list, cancel). Registered on
main_bp (see app/routes/main.py). Admin approval lives in
app/routes/admin_swap_routes.py.
"""

from datetime import date

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User
from app.repositories.shift_repository import ShiftRepository
from app.repositories.swap_request_repository import SwapRequestRepository
from app.routes.main import main_bp
from app.services import SwapService, UserService


@main_bp.route("/swaps")
@login_required
def swaps():
    requests = SwapRequestRepository.list_for_user(current_user.id)
    sent = [r for r in requests if r.requester_id == current_user.id]
    received = [r for r in requests if r.target_user_id == current_user.id]
    return render_template("swaps.html", sent=sent, received=received)


@main_bp.route("/swaps/add", methods=["GET", "POST"])
@login_required
def add_swap():
    if request.method == "POST":
        shift_id = request.form.get("shift_id", type=int)
        target_user_id = request.form.get("target_user_id", type=int)
        target_shift_id = request.form.get("target_shift_id", type=int)

        if not shift_id or not target_user_id:
            flash("Sélectionnez un shift à échanger et un destinataire.", "danger")
            return redirect(url_for("main.add_swap"))

        shift = ShiftRepository.get_by_id(shift_id)
        target_user = db.session.get(User, target_user_id)
        target_shift = (
            ShiftRepository.get_by_id(target_shift_id) if target_shift_id else None
        )

        if not shift or not target_user:
            flash("Shift ou utilisateur invalide.", "danger")
            return redirect(url_for("main.add_swap"))

        swap_request, error = SwapService.request_swap(
            current_user, shift, target_user, target_shift
        )
        if error:
            flash(f"Impossible de créer la demande : {error}", "danger")
            return redirect(url_for("main.add_swap"))

        flash("Demande d'échange envoyée, en attente de validation admin.", "success")
        return redirect(url_for("main.swaps"))

    my_shifts = [
        s
        for s in ShiftRepository.list_for_user(current_user.id)
        if s.date >= date.today()
    ]
    other_users = [u for u in UserService.list_all() if u.id != current_user.id]
    return render_template(
        "add_swap.html", my_shifts=my_shifts, other_users=other_users
    )


@main_bp.route("/swaps/<int:swap_request_id>/cancel", methods=["POST"])
@login_required
def cancel_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request:
        abort(404)

    error = SwapService.cancel_swap(swap_request, current_user)
    if error:
        flash(error, "danger")
    else:
        flash("Demande d'échange annulée.", "success")
    return redirect(url_for("main.swaps"))


@main_bp.route("/swaps/purge", methods=["POST"])
@login_required
def purge_swaps():
    count = SwapService.purge_resolved_for_user(current_user)
    flash(
        f"{count} demande(s) terminée(s) supprimée(s) de votre historique.", "success"
    )
    return redirect(url_for("main.swaps"))


@main_bp.route("/api/swaps/target-shifts")
@login_required
def api_target_shifts():
    """JSON list of a target user's upcoming shifts, for the exchange
    request form (optional choice of the shift requested back)."""
    target_user_id = request.args.get("user_id", type=int)
    if not target_user_id:
        return jsonify({"success": False, "error": "user_id manquant"}), 400

    shifts = [
        {"id": s.id, "date": s.date.isoformat(), "shift_type": s.shift_type.label}
        for s in ShiftRepository.list_for_user(target_user_id)
        if s.date >= date.today()
    ]
    return jsonify({"success": True, "shifts": shifts})
