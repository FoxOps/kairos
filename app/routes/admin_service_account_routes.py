"""
Admin routes for managing public API service accounts
(app/models/service_account.py, app/api/). Registered on admin_bp (see
app/routes/admin.py).
"""

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app.auth.decorators import admin_required
from app.repositories.service_account_repository import ServiceAccountRepository
from app.routes.admin import admin_bp
from app.services import ServiceAccountService


def _parse_expires_at(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


@admin_bp.route("/admin/service-accounts")
@admin_required
def list_service_accounts():
    accounts = ServiceAccountRepository.get_all()
    return render_template("admin/service_accounts.html", accounts=accounts)


@admin_bp.route("/admin/service-accounts/add", methods=["GET", "POST"])
@admin_required
def add_service_account():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash(_("Le nom est obligatoire."), "danger")
            return redirect(url_for("admin.add_service_account"))

        try:
            expires_at = _parse_expires_at(request.form.get("expires_at", ""))
        except ValueError:
            flash(_("Date d'expiration invalide."), "danger")
            return redirect(url_for("admin.add_service_account"))

        service_account, full_token = ServiceAccountService.create_account(
            name, description, expires_at
        )
        return render_template(
            "admin/service_account_created.html",
            service_account=service_account,
            full_token=full_token,
        )

    return render_template("admin/add_service_account.html")


@admin_bp.route(
    "/admin/service-accounts/edit/<int:service_account_id>", methods=["GET", "POST"]
)
@admin_required
def edit_service_account(service_account_id):
    service_account = ServiceAccountRepository.get_by_id(service_account_id) or abort(
        404
    )

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash(_("Le nom est obligatoire."), "danger")
            return redirect(
                url_for(
                    "admin.edit_service_account",
                    service_account_id=service_account_id,
                )
            )

        try:
            expires_at = _parse_expires_at(request.form.get("expires_at", ""))
        except ValueError:
            flash(_("Date d'expiration invalide."), "danger")
            return redirect(
                url_for(
                    "admin.edit_service_account",
                    service_account_id=service_account_id,
                )
            )

        ServiceAccountService.rename(service_account, name, description, expires_at)
        flash(_("Compte de service modifié avec succès !"), "success")
        return redirect(url_for("admin.list_service_accounts"))

    return render_template(
        "admin/edit_service_account.html", service_account=service_account
    )


@admin_bp.route(
    "/admin/service-accounts/<int:service_account_id>/regenerate", methods=["POST"]
)
@admin_required
def regenerate_service_account_secret(service_account_id):
    service_account = ServiceAccountRepository.get_by_id(service_account_id) or abort(
        404
    )

    full_token = ServiceAccountService.regenerate_secret(service_account)
    return render_template(
        "admin/service_account_created.html",
        service_account=service_account,
        full_token=full_token,
        regenerated=True,
    )


@admin_bp.route(
    "/admin/service-accounts/<int:service_account_id>/toggle-active", methods=["POST"]
)
@admin_required
def toggle_service_account_active(service_account_id):
    service_account = ServiceAccountRepository.get_by_id(service_account_id) or abort(
        404
    )

    if service_account.is_active:
        ServiceAccountService.revoke(service_account)
        flash(_("Compte de service révoqué."), "success")
    else:
        ServiceAccountService.reactivate(service_account)
        flash(_("Compte de service réactivé."), "success")
    return redirect(url_for("admin.list_service_accounts"))


@admin_bp.route(
    "/admin/service-accounts/delete/<int:service_account_id>", methods=["POST"]
)
@admin_required
def delete_service_account(service_account_id):
    service_account = ServiceAccountRepository.get_by_id(service_account_id) or abort(
        404
    )

    ServiceAccountService.delete(service_account)
    flash(_("Compte de service supprimé avec succès !"), "success")
    return redirect(url_for("admin.list_service_accounts"))
