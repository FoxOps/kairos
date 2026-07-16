"""
User routes for shift exchanges (request, list, cancel). Registered on
main_bp (see app/routes/main.py). Admin approval lives in
app/routes/admin_swap_routes.py.
"""

from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
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

        if not shift_id or not target_user_id:
            flash(_("Sélectionnez un shift à échanger et un destinataire."), "danger")
            return redirect(url_for("main.add_swap"))

        shift = ShiftRepository.get_by_id(shift_id)
        target_user = db.session.get(User, target_user_id)

        if not shift or not target_user:
            flash(_("Shift ou utilisateur invalide."), "danger")
            return redirect(url_for("main.add_swap"))

        swap_request, error = SwapService.request_swap(current_user, shift, target_user)
        if error:
            flash(
                _("Impossible de créer la demande : %(error)s", error=error), "danger"
            )
            return redirect(url_for("main.add_swap"))

        flash(
            _(
                "Demande d'échange envoyée, en attente de confirmation de %(name)s.",
                name=target_user.name,
            ),
            "success",
        )
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


@main_bp.route("/swaps/<int:swap_request_id>/confirm", methods=["GET", "POST"])
@login_required
def confirm_swap(swap_request_id):
    """Target's confirmation step: pick which of their own upcoming
    shifts to offer back (or none, for a one-way give-away), before the
    request reaches admin validation."""
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request or swap_request.target_user_id != current_user.id:
        abort(404)

    if request.method == "POST":
        target_shift_id = request.form.get("target_shift_id", type=int)
        target_shift = (
            ShiftRepository.get_by_id(target_shift_id) if target_shift_id else None
        )

        error = SwapService.confirm_swap(swap_request, current_user, target_shift)
        if error:
            flash(error, "danger")
            return redirect(
                url_for("main.confirm_swap", swap_request_id=swap_request_id)
            )

        flash(_("Échange confirmé, en attente de validation admin."), "success")
        return redirect(url_for("main.swaps"))

    my_shifts = [
        s
        for s in ShiftRepository.list_for_user(current_user.id)
        if s.date >= date.today()
    ]
    return render_template(
        "confirm_swap.html", swap_request=swap_request, my_shifts=my_shifts
    )


@main_bp.route("/swaps/<int:swap_request_id>/target-reject", methods=["POST"])
@login_required
def target_reject_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request or swap_request.target_user_id != current_user.id:
        abort(404)

    reason = request.form.get("reason", "").strip() or None
    error = SwapService.target_reject_swap(swap_request, current_user, reason)
    if error:
        flash(error, "danger")
    else:
        flash(_("Demande d'échange déclinée."), "success")
    return redirect(url_for("main.swaps"))


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
        flash(_("Demande d'échange annulée."), "success")
    return redirect(url_for("main.swaps"))


@main_bp.route("/swaps/purge", methods=["POST"])
@login_required
def purge_swaps():
    count = SwapService.purge_resolved_for_user(current_user)
    flash(
        _(
            "%(count)s demande(s) terminée(s) supprimée(s) de votre historique.",
            count=count,
        ),
        "success",
    )
    return redirect(url_for("main.swaps"))
