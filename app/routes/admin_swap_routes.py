"""
Admin routes for approving shift exchange requests. Registered on
admin_bp (see app/routes/admin.py). Request creation on the user side
lives in app/routes/swap_routes.py.
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user

from app.auth.decorators import admin_required
from app.repositories.swap_request_repository import SwapRequestRepository
from app.routes.admin import admin_bp
from app.services import SwapService


@admin_bp.route("/admin/swaps")
@admin_required
def list_swaps():
    awaiting_target = SwapService.list_pending()
    awaiting_admin = SwapService.list_awaiting_admin()
    approved = SwapService.list_approved()
    return render_template(
        "admin/swaps.html",
        awaiting_target=awaiting_target,
        awaiting_admin=awaiting_admin,
        approved=approved,
    )


@admin_bp.route("/admin/swaps/<int:swap_request_id>/approve", methods=["POST"])
@admin_required
def approve_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request:
        abort(404)

    error = SwapService.approve_swap(swap_request, current_user)
    if error:
        flash(error, "danger")
    else:
        flash(_("Échange approuvé, shifts réassignés."), "success")
    return redirect(url_for("admin.list_swaps"))


@admin_bp.route("/admin/swaps/<int:swap_request_id>/revert", methods=["POST"])
@admin_required
def revert_swap(swap_request_id):
    swap_request = SwapRequestRepository.get_by_id(swap_request_id)
    if not swap_request:
        abort(404)

    error = SwapService.revert_swap(swap_request, current_user)
    if error:
        flash(error, "danger")
    else:
        flash(
            _("Échange annulé, shifts réassignés à leurs propriétaires d'origine."),
            "success",
        )
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
        flash(error, "danger")
    else:
        flash(_("Échange rejeté."), "warning")
    return redirect(url_for("admin.list_swaps"))


@admin_bp.route("/admin/swaps/purge", methods=["POST"])
@admin_required
def purge_swaps():
    count = SwapService.purge_all_resolved()
    flash(
        _(
            "%(count)s demande(s) terminée(s) supprimée(s) (tous utilisateurs).",
            count=count,
        ),
        "success",
    )
    return redirect(url_for("admin.list_swaps"))
