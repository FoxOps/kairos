"""
Routes admin pour la validation des demandes d'échange de shifts.
Enregistrées sur admin_bp (cf. app/routes/admin.py). La création des
demandes côté utilisateur vit dans app/routes/swap_routes.py.
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.auth.decorators import admin_required
from app.repositories.swap_request_repository import SwapRequestRepository
from app.routes.admin import admin_bp
from app.services import SwapService


@admin_bp.route("/admin/swaps")
@admin_required
def list_swaps():
    pending = SwapService.list_pending()
    return render_template("admin/swaps.html", pending=pending)


@admin_bp.route("/admin/swaps/<int:swap_request_id>/approve", methods=["POST"])
@admin_required
def approve_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request:
        abort(404)

    error = SwapService.approve_swap(swap_request, current_user)
    if error:
        flash(f"❌ {error}", "danger")
    else:
        flash("✅ Échange approuvé, shifts réassignés.", "success")
    return redirect(url_for("admin.list_swaps"))


@admin_bp.route("/admin/swaps/<int:swap_request_id>/reject", methods=["POST"])
@admin_required
def reject_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request:
        abort(404)

    reason = request.form.get("reason", "").strip() or None
    error = SwapService.reject_swap(swap_request, current_user, reason)
    if error:
        flash(f"❌ {error}", "danger")
    else:
        flash("Échange rejeté.", "success")
    return redirect(url_for("admin.list_swaps"))
