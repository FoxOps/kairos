"""
Admin routes for managing external notification targets (Apprise -
Slack/Discord/Telegram/webhooks). Registered on admin_bp (see
app/routes/admin.py).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app import db
from app.auth.decorators import admin_required
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)
from app.routes.admin import admin_bp
from app.services import AppriseNotificationService, AuditService, SettingsService

CATEGORY_CHOICES = ["swap", "backup", "system"]


@admin_bp.route("/admin/notification-targets")
@admin_required
def list_notification_targets():
    targets = NotificationTargetRepository.get_all()
    return render_template(
        "admin/notification_targets.html",
        targets=targets,
        category_choices=CATEGORY_CHOICES,
        apprise_notifications_enabled=SettingsService.get_apprise_notifications_enabled(),
    )


@admin_bp.route("/admin/notification-targets/toggle", methods=["POST"])
@admin_required
def toggle_apprise_notifications():
    enabled = request.form.get("enabled") == "on"
    error = SettingsService.set_apprise_notifications_enabled(enabled)
    if error:
        flash(_("Erreur : %(error)s", error=error), "danger")
    else:
        flash(
            (
                _("Notifications externes activées.")
                if enabled
                else _("Notifications externes désactivées.")
            ),
            "success",
        )
    return redirect(url_for("admin.list_notification_targets"))


@admin_bp.route("/admin/notification-targets/add", methods=["GET", "POST"])
@admin_required
def add_notification_target():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        apprise_url = request.form.get("apprise_url", "").strip()
        enabled = request.form.get("enabled") == "on"
        categories = [
            c for c in request.form.getlist("categories") if c in CATEGORY_CHOICES
        ]

        if not name or not apprise_url:
            flash(_("Le nom et l'URL Apprise sont obligatoires."), "danger")
            return redirect(url_for("admin.add_notification_target"))

        try:
            target = NotificationTargetRepository.create(
                name, apprise_url, enabled, categories
            )
            db.session.commit()
            AuditService.log(
                "notification_target.create",
                resource_type="NotificationTarget",
                resource_id=target.id,
                details=name,
            )
            flash(_("Cible de notification ajoutée avec succès !"), "success")
            return redirect(url_for("admin.list_notification_targets"))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    return render_template(
        "admin/add_notification_target.html", category_choices=CATEGORY_CHOICES
    )


@admin_bp.route(
    "/admin/notification-targets/edit/<int:target_id>", methods=["GET", "POST"]
)
@admin_required
def edit_notification_target(target_id):
    target = NotificationTargetRepository.get_by_id(target_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        apprise_url = request.form.get("apprise_url", "").strip()
        enabled = request.form.get("enabled") == "on"
        categories = [
            c for c in request.form.getlist("categories") if c in CATEGORY_CHOICES
        ]

        if not name or not apprise_url:
            flash(_("Le nom et l'URL Apprise sont obligatoires."), "danger")
            return redirect(
                url_for("admin.edit_notification_target", target_id=target_id)
            )

        try:
            target.name = name
            target.apprise_url = apprise_url
            target.enabled = enabled
            target.set_categories(categories)
            db.session.commit()
            AuditService.log(
                "notification_target.update",
                resource_type="NotificationTarget",
                resource_id=target.id,
                details=name,
            )
            flash(_("Cible de notification modifiée avec succès !"), "success")
            return redirect(url_for("admin.list_notification_targets"))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    return render_template(
        "admin/edit_notification_target.html",
        target=target,
        category_choices=CATEGORY_CHOICES,
        selected_categories=target.get_categories(),
    )


@admin_bp.route("/admin/notification-targets/delete/<int:target_id>", methods=["POST"])
@admin_required
def delete_notification_target(target_id):
    target = NotificationTargetRepository.get_by_id(target_id) or abort(404)

    deleted_name = target.name
    NotificationTargetRepository.delete(target)
    db.session.commit()
    AuditService.log(
        "notification_target.delete",
        resource_type="NotificationTarget",
        resource_id=target_id,
        details=deleted_name,
    )
    flash(_("Cible de notification supprimée avec succès !"), "success")
    return redirect(url_for("admin.list_notification_targets"))


@admin_bp.route(
    "/admin/notification-targets/<int:target_id>/toggle-enabled", methods=["POST"]
)
@admin_required
def toggle_notification_target_enabled(target_id):
    target = NotificationTargetRepository.get_by_id(target_id) or abort(404)

    target.enabled = not target.enabled
    db.session.commit()
    AuditService.log(
        "notification_target.toggle",
        resource_type="NotificationTarget",
        resource_id=target.id,
        details=target.name,
    )
    return redirect(url_for("admin.list_notification_targets"))


@admin_bp.route("/admin/notification-targets/<int:target_id>/test", methods=["POST"])
@admin_required
def test_notification_target(target_id):
    target = NotificationTargetRepository.get_by_id(target_id) or abort(404)

    ok, error = AppriseNotificationService.send_test(target)
    if ok:
        flash(_("Notification de test envoyée avec succès !"), "success")
    else:
        flash(_("Échec du test : %(error)s", error=error), "danger")
    return redirect(url_for("admin.list_notification_targets"))
