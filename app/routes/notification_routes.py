"""
Routes pour les notifications internes à l'app (bell icon). Enregistrées
sur main_bp (cf. app/routes/main.py).
"""

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.repositories.app_notification_repository import AppNotificationRepository
from app.routes.main import main_bp
from app.services import AppNotificationService


@main_bp.route("/notifications")
@login_required
def notifications():
    items = AppNotificationService.list_for_user(current_user.id)
    return render_template("notifications.html", notifications=items)


@main_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    notification = AppNotificationRepository.get_by_id(notification_id)
    if not notification:
        abort(404)
    if notification.user_id != current_user.id:
        abort(403)

    AppNotificationService.mark_read(notification, current_user)
    if notification.link:
        return redirect(notification.link)
    return redirect(url_for("main.notifications"))


@main_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    AppNotificationService.mark_all_read(current_user)
    return redirect(url_for("main.notifications"))


@main_bp.route("/notifications/purge", methods=["POST"])
@login_required
def purge_notifications():
    count = AppNotificationService.purge_read(current_user)
    flash(f"{count} notification(s) lue(s) supprimée(s).", "success")
    return redirect(url_for("main.notifications"))
