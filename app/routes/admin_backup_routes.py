"""
Routes admin pour les sauvegardes de la base de données. Enregistrées
sur admin_bp (cf. app/routes/admin.py). Logique métier déléguée à
BackupService, qui wrappe scripts/backup_database.py.
"""

import os

from flask import abort, flash, redirect, render_template, send_file, url_for

from app.auth.decorators import admin_required
from app.routes.admin import admin_bp
from app.services import BackupService


@admin_bp.route("/admin/backups")
@admin_required
def backups_dashboard():
    """Tableau de bord des sauvegardes : config, liste locale et S3."""
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
    """Déclenche une sauvegarde immédiate (local et/ou S3 selon la config)."""
    results = BackupService.create_now()

    if results["success"]:
        flash("✅ Sauvegarde créée avec succès.", "success")
    else:
        errors = "; ".join(results.get("errors", [])) or "erreur inconnue"
        flash(f"❌ Échec de la sauvegarde : {errors}", "danger")

    return redirect(url_for("admin.backups_dashboard"))


@admin_bp.route("/admin/backups/cleanup", methods=["POST"])
@admin_required
def backups_cleanup():
    """Nettoie les sauvegardes expirées (local et S3) selon la rétention configurée."""
    results = BackupService.cleanup_now()
    local = results["local"]
    s3 = results["s3"]

    flash(
        f"🧹 Nettoyage terminé : {local['count']} sauvegarde(s) locale(s), "
        f"{s3['count']} sauvegarde(s) S3 supprimée(s).",
        "info",
    )

    return redirect(url_for("admin.backups_dashboard"))


@admin_bp.route("/admin/backups/download/local/<path:filename>")
@admin_required
def backups_download_local(filename):
    """Télécharge une sauvegarde locale."""
    filepath = BackupService.get_local_backup_path(filename)
    if filepath is None:
        abort(404)

    return send_file(filepath, as_attachment=True, download_name=filename)


@admin_bp.route("/admin/backups/download/s3/<path:key>")
@admin_required
def backups_download_s3(key):
    """Télécharge une sauvegarde S3 (téléchargée côté serveur puis
    diffusée au navigateur - pas d'URL présignée exposée directement)."""
    tmp_path = BackupService.download_s3_backup_to_temp(key)
    if tmp_path is None:
        abort(404)

    response = send_file(
        tmp_path, as_attachment=True, download_name=os.path.basename(key)
    )
    response.call_on_close(lambda: os.path.exists(tmp_path) and os.remove(tmp_path))
    return response
