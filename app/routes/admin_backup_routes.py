"""
Admin routes for database backups. Registered on admin_bp (see
app/routes/admin.py). Business logic delegated to BackupService, which
wraps scripts/backup_database.py.
"""

import os

from flask import abort, flash, redirect, render_template, send_file, url_for
from flask_babel import gettext as _

from app.auth.decorators import admin_required
from app.routes.admin import admin_bp
from app.services import BackupService


@admin_bp.route("/admin/backups")
@admin_required
def backups_dashboard():
    """Backup dashboard: config, local and S3 listing."""
    config = BackupService.get_config()
    backups = BackupService.list_all_backups()

    return render_template(
        "admin/backups/dashboard.html",
        config=config,
        local_backups=backups["local"],
        s3_backups=backups["s3"],
    )


@admin_bp.route("/admin/backups/create", methods=["POST"])
@admin_required
def backups_create():
    """Trigger an immediate backup (local and/or S3 depending on config)."""
    results = BackupService.create_now()

    if results["success"]:
        flash(_("Sauvegarde créée avec succès."), "success")
    else:
        errors = "; ".join(results.get("errors", [])) or "erreur inconnue"
        flash(_("Échec de la sauvegarde : %(errors)s", errors=errors), "danger")

    return redirect(url_for("admin.backups_dashboard"))


@admin_bp.route("/admin/backups/cleanup", methods=["POST"])
@admin_required
def backups_cleanup():
    """Clean up expired backups (local and S3) per the configured retention."""
    results = BackupService.cleanup_now()
    local = results["local"]
    s3 = results["s3"]

    flash(
        _(
            "Nettoyage terminé : %(val0)s sauvegarde(s) locale(s), %(val1)s sauvegarde(s) S3 supprimée(s).",
            val0=local["count"],
            val1=s3["count"],
        ),
        "info",
    )

    return redirect(url_for("admin.backups_dashboard"))


@admin_bp.route("/admin/backups/download/local/<path:filename>")
@admin_required
def backups_download_local(filename):
    """Download a local backup."""
    filepath = BackupService.get_local_backup_path(filename)
    if filepath is None:
        abort(404)

    return send_file(filepath, as_attachment=True, download_name=filename)


@admin_bp.route("/admin/backups/download/s3/<path:key>")
@admin_required
def backups_download_s3(key):
    """Download an S3 backup (fetched server-side then streamed to the
    browser - no presigned URL exposed directly)."""
    tmp_path = BackupService.download_s3_backup_to_temp(key)
    if tmp_path is None:
        abort(404)

    response = send_file(
        tmp_path, as_attachment=True, download_name=os.path.basename(key)
    )
    response.call_on_close(lambda: os.path.exists(tmp_path) and os.remove(tmp_path))
    return response
