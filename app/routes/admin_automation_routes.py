"""
Routes admin pour l'automatisation (astreintes/shifts). Enregistrées sur
admin_bp (cf. app/routes/admin.py).
"""

from datetime import date, datetime, timedelta

from flask import flash, redirect, render_template, request, url_for

from app import db
from app.auth.decorators import admin_required
from app.repositories.shift_repository import ShiftRepository
from app.routes.admin import admin_bp
from app.services import AutomationAdminService
from app.utils.automation import (
    AdvancedShiftAutomation,
    OnCallAutomation,
    get_automation_status,
)


def _flash_automation_messages(messages, default_category="info"):
    for msg in messages:
        if "✅" in msg or "🎉" in msg:
            category = "success"
        elif "⚠️" in msg:
            category = "warning"
        elif default_category == "info":
            category = "info"
        else:
            category = "danger"
        flash(msg, category)


@admin_bp.route("/admin/automation")
@admin_required
def automation_dashboard():
    """Tableau de bord de l'automatisation."""
    status = get_automation_status()

    return render_template(
        "admin/automation/dashboard.html",
        status=status,
    )


@admin_bp.route("/admin/automation/full", methods=["GET", "POST"])
@admin_required
def automation_full():
    """Génération complète (astreintes + shifts)."""
    if request.method == "POST":
        action = request.form.get("action")

        if action in ["generate", "dry_run", "save_order"]:
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")

            rotation_order_ids = AutomationAdminService.parse_rotation_order_from_form(
                request.form
            )

            if action == "save_order":
                error = AutomationAdminService.save_rotation_order(rotation_order_ids)
                if error:
                    flash(
                        f"❌ Erreur lors de la sauvegarde de l'ordre : {error}",
                        "danger",
                    )
                else:
                    flash(
                        "✅ Ordre de rotation enregistré ! Utilisez le bouton 'Générer' pour appliquer.",
                        "success",
                    )
                return redirect(url_for("admin.automation_full"))

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                dry_run = action == "dry_run"

                if not dry_run:
                    oncalls_deleted, shifts_deleted = (
                        AutomationAdminService.clear_period(start_date, end_date)
                    )
                    if oncalls_deleted:
                        flash(
                            f"🗑️ {oncalls_deleted} astreintes existantes supprimées pour la période",
                            "info",
                        )
                    if shifts_deleted:
                        flash(
                            f"🗑️ {shifts_deleted} shifts existants supprimés pour la période",
                            "info",
                        )

                oncalls, oncall_messages = OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, rotation_order_ids, dry_run=dry_run
                )

                if dry_run:
                    return render_template(
                        "admin/automation/oncall_dry_run.html",
                        oncalls=oncalls,
                        messages=oncall_messages,
                        start_date=start_date,
                        end_date=end_date,
                    )
                else:
                    shifts, shift_messages = (
                        AdvancedShiftAutomation.generate_full_schedule(
                            start_date, end_date, dry_run=False
                        )
                    )

                    _flash_automation_messages(
                        oncall_messages, default_category="danger"
                    )
                    _flash_automation_messages(shift_messages, default_category="info")

                    flash(
                        f"🔄 Régénération complète terminée pour la période du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}",
                        "success",
                    )
                    return redirect(url_for("admin.automation_full"))

            except ValueError as e:
                flash(f"❌ Format de date invalide : {str(e)}", "danger")
            except Exception as e:
                flash(f"❌ Erreur : {str(e)}", "danger")

    oncall_users = OnCallAutomation.get_eligible_users()
    current_rotation_order = AutomationAdminService.get_rotation_order()

    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today
    while start_date_default.weekday() != 4:
        start_date_default += timedelta(days=1)

    return render_template(
        "admin/automation/full.html",
        oncall_users=oncall_users,
        start_date_default=start_date_default,
        end_date_default=end_date_default,
        current_rotation_order=current_rotation_order,
    )


@admin_bp.route("/admin/automation/status")
@admin_required
def automation_status():
    """Affiche l'état actuel de l'automatisation."""
    status = get_automation_status()
    return render_template("admin/automation/status.html", status=status)


@admin_bp.route("/admin/automation/refresh-shifts", methods=["GET", "POST"])
@admin_required
def refresh_shifts():
    """
    Rafraîchit les shifts en vérifiant les astreintes actuelles.

    Cette route permet de recalculer tous les shifts pour une période donnée
    en tenant compte des astreintes actuelles (même modifiées manuellement).
    """
    if request.method == "POST":
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            # Ne supprime que les shifts (pas les astreintes, contrairement à
            # automation_full) : on ne fait que régénérer les shifts en
            # tenant compte des astreintes existantes.
            deleted = ShiftRepository.delete_in_date_range(start_date, end_date)
            if deleted:
                db.session.commit()
                flash(
                    f"🗑️ {deleted} shifts existants supprimés pour la période", "info"
                )

            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=False
            )

            _flash_automation_messages(messages, default_category="info")

            flash(f"🔄 {len(shifts)} shifts régénérés avec succès !", "success")
            return redirect(url_for("admin.refresh_shifts"))

        except ValueError as e:
            flash(f"❌ Format de date invalide : {str(e)}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today

    return render_template(
        "admin/automation/refresh_shifts.html",
        start_date_default=start_date_default,
        end_date_default=end_date_default,
    )
