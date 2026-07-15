"""
Admin route for the "Paramètres" (Settings) page. Registered on admin_bp
(see app/routes/admin.py). Each form section posts independently (a
`section` hidden field selects which SettingsService setter runs) so a
validation error in one group doesn't affect the others.
"""

from flask import flash, redirect, render_template, request, url_for

from app.auth.decorators import admin_required
from app.routes.admin import admin_bp
from app.services import SettingsService
from app.utils.helpers.common_helpers import get_timezone_choices
from scripts.backup_config import BackupConfig


@admin_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings_dashboard():
    if request.method == "POST":
        section = request.form.get("section")

        if section == "timezone":
            tz_name = request.form.get("default_timezone", "")
            error = SettingsService.set_default_timezone(tz_name)
            if error:
                flash(f"❌ Erreur : {error}", "danger")
            else:
                flash("✅ Fuseau horaire par défaut enregistré", "success")

        elif section == "general":
            public_base_url = request.form.get("public_base_url", "").strip() or None
            error = SettingsService.set_public_base_url(public_base_url)
            if error:
                flash(f"❌ Erreur : {error}", "danger")
            else:
                flash("✅ URL publique enregistrée", "success")

        elif section == "pagination":
            try:
                items_per_page = int(request.form.get("items_per_page", ""))
                max_per_page = int(request.form.get("max_per_page", ""))
            except ValueError:
                flash("❌ Erreur : valeurs de pagination invalides", "danger")
            else:
                error = SettingsService.set_pagination(items_per_page, max_per_page)
                if error:
                    flash(f"❌ Erreur : {error}", "danger")
                else:
                    flash("✅ Pagination enregistrée", "success")

        elif section == "notifications":
            enabled = request.form.get("notifications_enabled") == "on"
            error = SettingsService.set_notifications_enabled(enabled)
            if error:
                flash(f"❌ Erreur : {error}", "danger")
            else:
                flash("✅ Notifications enregistrées", "success")

        elif section == "backups":
            try:
                retention_days = int(request.form.get("backup_retention_days", ""))
                max_backups = int(request.form.get("backup_max_backups", ""))
            except ValueError:
                flash("❌ Erreur : valeurs de sauvegarde invalides", "danger")
            else:
                error = SettingsService.set_backup_retention(
                    retention_days, max_backups
                )
                if error:
                    flash(f"❌ Erreur : {error}", "danger")
                else:
                    flash("✅ Rétention des sauvegardes enregistrée", "success")

        elif section == "ics":
            try:
                expiry_days = int(request.form.get("ics_token_expiry_days", ""))
            except ValueError:
                flash("❌ Erreur : durée d'expiration invalide", "danger")
            else:
                error = SettingsService.set_ics_token_expiry_days(expiry_days)
                if error:
                    flash(f"❌ Erreur : {error}", "danger")
                else:
                    flash("✅ Durée d'expiration ICS enregistrée", "success")

        return redirect(url_for("admin.settings_dashboard"))

    env_backup_defaults = BackupConfig.from_env()

    return render_template(
        "admin/settings.html",
        default_timezone=SettingsService.get_default_timezone(),
        timezones=get_timezone_choices(),
        public_base_url=SettingsService.get_public_base_url(),
        items_per_page=SettingsService.get_items_per_page(),
        max_per_page=SettingsService.get_max_per_page(),
        notifications_enabled=SettingsService.get_notifications_enabled(),
        backup_retention_days=SettingsService.get_backup_retention_days()
        or env_backup_defaults.retention_days,
        backup_max_backups=SettingsService.get_backup_max_backups()
        or env_backup_defaults.max_backups,
        ics_token_expiry_days=SettingsService.get_ics_token_expiry_days(),
    )
