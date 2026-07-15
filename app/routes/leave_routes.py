"""
Routes for leaves (schedule, CRUD, drag & drop API). Registered on
main_bp (see app/routes/main.py).
"""

from datetime import datetime

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.auth.decorators import user_owns_resource
from app.models import Leave, User
from app.repositories.leave_repository import LeaveRepository
from app.routes.main import main_bp
from app.services import LeaveService, UserService


@main_bp.route("/leave")
@login_required
def leave():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    per_page_options = [5, 10, 25, 50, 100]

    if per_page == 0 or per_page == -1:
        per_page = 999999

    if per_page not in per_page_options and per_page != 999999:
        per_page = 20

    leaves_paginated = LeaveService.list_paginated(page, per_page)

    return render_template(
        "leave.html",
        leaves=leaves_paginated,
        per_page=per_page,
        per_page_options=per_page_options,
    )


@main_bp.route("/leave/add", methods=["GET", "POST"])
@login_required
def add_leave():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        if not all([user_id, start_date_str, end_date_str]):
            flash(_("Tous les champs obligatoires doivent être remplis."), "danger")
            return redirect(url_for("main.add_leave"))

        try:
            user_id = int(user_id)

            # Permission check: a regular user may only add their own leave
            if not current_user.is_admin and current_user.id != user_id:
                flash(
                    _("Vous ne pouvez ajouter des congés que pour vous-même."), "danger"
                )
                return redirect(url_for("main.leave"))

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            target_user = db.session.get(User, user_id)
            if not target_user:
                flash(_("Utilisateur invalide."), "danger")
                return redirect(url_for("main.add_leave"))

            new_leave, regenerated_shifts = LeaveService.add_leave(
                target_user, start_date, end_date
            )
            if not new_leave:
                flash(
                    _(
                        "Impossible d'ajouter ce congé (dates invalides, congé existant sur cette période, ou effectif disponible tombant à 0 un jour de cette période)."
                    ),
                    "danger",
                )
                return redirect(url_for("main.add_leave"))

            if regenerated_shifts is None:
                flash(_("Rééquilibrage automatique des shifts échoué."), "warning")
            elif regenerated_shifts:
                flash(
                    _(
                        "Congé ajouté. %(val0)s shifts ont été recalculés.",
                        val0=len(regenerated_shifts),
                    ),
                    "success",
                )
            else:
                flash(_("Congé ajouté. Aucun shift à recalculer."), "success")

            flash(_("Conge ajoute avec succes !"), "success")
            return redirect(url_for("main.leave"))
        except ValueError:
            db.session.rollback()
            flash(
                _("Format de date invalide. Utilisez le format AAAA-MM-JJ."), "danger"
            )
            return redirect(url_for("main.add_leave"))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    # A regular user only sees themselves in the list
    users = UserService.visible_users_for_leave(current_user)
    return render_template("add_leave.html", users=users)


@main_bp.route("/leave/delete/<int:leave_id>", methods=["POST"])
@login_required
@user_owns_resource(Leave, "leave_id")
def delete_leave(leave_id):
    if not LeaveRepository.get_by_id(leave_id):
        abort(404)

    try:
        _leave, regenerated_shifts = LeaveService.delete_leave(leave_id)

        if regenerated_shifts is None:
            flash(_("Rééquilibrage automatique des shifts échoué."), "warning")
        elif regenerated_shifts:
            flash(
                _(
                    "Congé supprimé. %(val0)s shifts ont été recalculés.",
                    val0=len(regenerated_shifts),
                ),
                "success",
            )
        else:
            flash(_("Congé supprimé. Aucun shift à recalculer."), "success")

        flash(_("Conge supprime avec succes !"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Erreur : %(val0)s", val0=str(e)), "danger")
    return redirect(url_for("main.leave"))


@main_bp.route("/api/leave/<int:leave_id>", methods=["DELETE"])
@login_required
def api_delete_leave(leave_id):
    """API endpoint to delete a leave."""
    leave_obj = LeaveRepository.get_by_id(leave_id)
    if not leave_obj:
        return jsonify({"success": False, "error": "Congé non trouvé"}), 404

    # Permission check: a regular user may only delete their own leave
    if not current_user.is_admin and current_user.id != leave_obj.user_id:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Vous ne pouvez supprimer que vos propres congés",
                }
            ),
            403,
        )

    try:
        _deleted, rebalance_failed = LeaveService.api_delete(leave_id)
        response = {"success": True, "message": "Congé supprimé avec succès"}
        if rebalance_failed:
            response["rebalance_warning"] = True
            response["message"] += " (le rééquilibrage automatique des shifts a échoué)"
        return jsonify(response)
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500


@main_bp.route("/api/leave/<int:leave_id>", methods=["PATCH", "PUT"])
@login_required
def api_update_leave(leave_id):
    """API endpoint to update a leave via drag & drop."""
    leave_obj = LeaveRepository.get_by_id(leave_id)
    if not leave_obj:
        return jsonify({"success": False, "error": "Congé non trouvé"}), 404

    # Permission check: a regular user may only modify their own leave
    if not current_user.is_admin and current_user.id != leave_obj.user_id:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Vous ne pouvez modifier que vos propres congés",
                }
            ),
            403,
        )

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Aucune donnée reçue"}), 400

    try:
        new_start_str = data.get("start")
        new_end_str = data.get("end")

        if not new_start_str:
            return jsonify({"success": False, "error": "Date de début manquante"}), 400

        new_start = datetime.fromisoformat(new_start_str.replace("Z", "+00:00"))

        if new_end_str:
            new_end = datetime.fromisoformat(new_end_str.replace("Z", "+00:00"))
        else:
            duration = leave_obj.end_date - leave_obj.start_date
            new_end = new_start + duration

        new_start_date = new_start.date()
        new_end_date = new_end.date()

        updated_leave, error, rebalance_failed = LeaveService.api_update(
            leave_id, new_start_date, new_end_date
        )
        if error:
            return jsonify({"success": False, "error": error}), 400

        message = "Congé mis à jour avec succès"
        response = {
            "success": True,
            "message": message,
            "leave": {
                "id": updated_leave.id,
                "start": updated_leave.start_date.isoformat(),
                "end": updated_leave.end_date.isoformat(),
            },
        }
        if rebalance_failed:
            response["rebalance_warning"] = True
            response["message"] += " (le rééquilibrage automatique des shifts a échoué)"
        return jsonify(response)

    except ValueError as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "error": f"Format de date invalide: {str(e)}"}),
            400,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500
