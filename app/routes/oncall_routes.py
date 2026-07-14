"""
Routes pour les astreintes (planning, CRUD, API drag & drop). Enregistrées
sur main_bp (cf. app/routes/main.py).
"""

from datetime import datetime

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app import db
from app.auth.decorators import admin_required
from app.models import User
from app.repositories.oncall_repository import OnCallRepository
from app.routes.main import main_bp
from app.services import OnCallService, UserService


@main_bp.route("/oncall")
@login_required
def oncall():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    per_page_options = [5, 10, 25, 50, 100]

    if per_page == 0 or per_page == -1:
        per_page = 999999

    if per_page not in per_page_options and per_page != 999999:
        per_page = 20

    on_calls_paginated = OnCallService.list_paginated(page, per_page)

    return render_template(
        "oncall.html",
        on_calls=on_calls_paginated,
        per_page=per_page,
        per_page_options=per_page_options,
    )


@main_bp.route("/oncall/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_oncall():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_str = request.form.get("start_date")

        if not all([user_id, start_date_str]):
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("main.add_oncall"))

        try:
            user_id = int(user_id)
            target_user = db.session.get(User, user_id)
            if not target_user:
                flash("Utilisateur invalide.", "danger")
                return redirect(url_for("main.add_oncall"))

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

            oncall_obj, error = OnCallService.add_oncall(target_user, start_date)
            if error:
                flash(error, "danger")
                return redirect(url_for("main.add_oncall"))

            flash(
                "Astreinte ajoutee avec succes ! (Du vendredi 21h au vendredi suivant 07h)",
                "success",
            )
            return redirect(url_for("main.oncall"))
        except ValueError:
            db.session.rollback()
            flash("Format de date invalide. Utilisez le format AAAA-MM-JJ.", "danger")
            return redirect(url_for("main.add_oncall"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")

    # Seuls les administrateurs peuvent voir cette page
    users = UserService.list_for_oncall()
    return render_template("add_oncall.html", users=users)


@main_bp.route("/oncall/delete/<int:oncall_id>", methods=["POST"])
@login_required
@admin_required
def delete_oncall(oncall_id):
    if not OnCallRepository.get_by_id(oncall_id):
        abort(404)

    try:
        OnCallService.delete_oncall(oncall_id)
        flash("Astreinte supprimee avec succes !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("main.oncall"))


@main_bp.route("/oncall/delete-all", methods=["POST"])
@login_required
@admin_required
def delete_all_oncalls():
    """Supprime toutes les astreintes."""
    try:
        count = OnCallService.delete_all()
        if count > 0:
            flash(
                f"✅ Toutes les {count} astreintes ont été supprimées avec succès !",
                "success",
            )
        else:
            flash("⚠️ Aucune astreinte à supprimer.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.oncall"))


@main_bp.route("/oncall/delete-all-for-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_all_oncalls_for_user(user_id):
    """Supprime toutes les astreintes d'un utilisateur spécifique."""
    user = db.session.get(User, user_id) or abort(404)

    try:
        count = OnCallService.delete_all_for_user(user_id)
        if count == 0:
            flash(f"⚠️ Aucun astreinte trouvée pour {user.name}.", "warning")
        else:
            flash(
                f"✅ Toutes les {count} astreintes de {user.name} ont été supprimées avec succès !",
                "success",
            )
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.oncall"))


@main_bp.route("/api/oncall/<int:oncall_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_oncall(oncall_id):
    """API endpoint pour supprimer une astreinte."""
    if not OnCallRepository.get_by_id(oncall_id):
        return jsonify({"success": False, "error": "Astreinte non trouvée"}), 404

    try:
        OnCallService.api_delete(oncall_id)
        return jsonify({"success": True, "message": "Astreinte supprimée avec succès"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500


@main_bp.route("/api/oncall/<int:oncall_id>", methods=["PATCH", "PUT"])
@login_required
@admin_required
def api_update_oncall(oncall_id):
    """API endpoint pour mettre à jour une astreinte via drag & drop."""
    oncall_obj = OnCallRepository.get_by_id(oncall_id)
    if not oncall_obj:
        return jsonify({"success": False, "error": "Astreinte non trouvée"}), 404

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
            duration = oncall_obj.end_time - oncall_obj.start_time
            new_end = new_start + duration

        updated_oncall, error = OnCallService.api_update(oncall_id, new_start, new_end)
        if error:
            return jsonify({"success": False, "error": error}), 400

        return jsonify(
            {
                "success": True,
                "message": "Astreinte mise à jour avec succès",
                "oncall": {
                    "id": updated_oncall.id,
                    "start": updated_oncall.start_time.isoformat(),
                    "end": updated_oncall.end_time.isoformat(),
                },
            }
        )

    except ValueError as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "error": f"Format de date invalide: {str(e)}"}),
            400,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500
