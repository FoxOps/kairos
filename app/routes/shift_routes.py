"""
Routes pour les shifts (planning, CRUD, API drag & drop). Enregistrées
sur main_bp (cf. app/routes/main.py).
"""

from datetime import datetime, timedelta

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.auth.decorators import admin_required
from app.models import User
from app.repositories.shift_repository import ShiftRepository, ShiftTypeRepository
from app.routes.main import main_bp
from app.services import ShiftService, UserService


@main_bp.route("/schedule")
@login_required
def schedule():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    per_page_options = [5, 10, 25, 50, 100]

    if per_page == 0 or per_page == -1:
        per_page = 999999

    if per_page not in per_page_options and per_page != 999999:
        per_page = 20

    shifts_paginated = ShiftService.list_paginated(page, per_page)

    return render_template(
        "schedule.html",
        shifts=shifts_paginated,
        per_page=per_page,
        per_page_options=per_page_options,
    )


@main_bp.route("/schedule/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_shift():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        shift_type_id = request.form.get("shift_type_id")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        if not all([user_id, shift_type_id, start_date_str, end_date_str]):
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("main.add_shift"))

        try:
            shift_type = ShiftTypeRepository.get_by_id(int(shift_type_id))
            if not shift_type:
                flash("Type de shift invalide.", "danger")
                return redirect(url_for("main.add_shift"))

            user_id = int(user_id)
            target_user = db.session.get(User, user_id)
            if not target_user:
                flash("Utilisateur invalide.", "danger")
                return redirect(url_for("main.add_shift"))

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            if start_date > end_date:
                flash(
                    "La date de debut doit etre anterieure a la date de fin.", "danger"
                )
                return redirect(url_for("main.add_shift"))

            shifts_added, failed_date = ShiftService.add_shifts_for_range(
                target_user, shift_type, start_date, end_date
            )

            if failed_date is not None:
                flash(
                    f"Impossible d'ajouter ce shift (le {failed_date.strftime('%d/%m/%Y')}).",
                    "danger",
                )
                return redirect(url_for("main.add_shift"))

            if shifts_added:
                flash(
                    f"Shifts ajoutes avec succes pour les dates : {', '.join(shifts_added)} !",
                    "success",
                )
            else:
                flash(
                    "Aucun shift ajoute (periode invalide ou jours non ouvres).",
                    "danger",
                )
            return redirect(url_for("main.schedule"))
        except ValueError as e:
            db.session.rollback()
            flash(
                f"Format de date invalide : {str(e)}. Utilisez le format AAAA-MM-JJ.",
                "danger",
            )
            return redirect(url_for("main.add_shift"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")
            return redirect(url_for("main.add_shift"))

    # Seuls les administrateurs peuvent voir cette page
    users = UserService.list_for_schedule()
    shift_types = ShiftTypeRepository.get_all()
    return render_template("add_shift.html", users=users, shift_types=shift_types)


@main_bp.route("/schedule/delete/<int:shift_id>")
@login_required
@admin_required
def delete_shift(shift_id):
    if not ShiftRepository.get_by_id(shift_id):
        abort(404)

    try:
        ShiftService.delete_shift(shift_id)
        flash("Shift supprime avec succes !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("main.schedule"))


@main_bp.route("/shift/delete-all", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts():
    """Supprime tous les shifts."""
    try:
        count = ShiftService.delete_all()
        if count > 0:
            flash(
                f"✅ Tous les {count} shifts ont été supprimés avec succès !", "success"
            )
        else:
            flash("⚠️ Aucun shift à supprimer.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.schedule"))


@main_bp.route("/shift/delete-all-for-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_user(user_id):
    """Supprime tous les shifts d'un utilisateur spécifique."""
    user = db.session.get(User, user_id) or abort(404)

    try:
        count = ShiftService.delete_all_for_user(user_id)
        if count == 0:
            flash(f"⚠️ Aucun shift trouvé pour {user.name}.", "warning")
        else:
            flash(
                f"✅ Tous les {count} shifts de {user.name} ont été supprimés avec succès !",
                "success",
            )
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.schedule"))


@main_bp.route("/shift/delete-day/<date_str>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_day(date_str):
    """Supprime tous les shifts pour une journée spécifique."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        count = ShiftService.delete_for_day(date_obj)

        if count == 0:
            flash(
                f"⚠️ Aucun shift trouvé pour le {date_obj.strftime('%d/%m/%Y')}.",
                "warning",
            )
        else:
            flash(
                f"✅ Tous les {count} shifts du {date_obj.strftime('%d/%m/%Y')} ont été supprimés avec succès !",
                "success",
            )
    except ValueError:
        flash("❌ Format de date invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.schedule"))


@main_bp.route("/shift/delete-week/<date_str>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_week(date_str):
    """Supprime tous les shifts pour une semaine complète (lundi-vendredi)."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        monday = date_obj - timedelta(days=date_obj.weekday())

        count = ShiftService.delete_for_week(monday)

        if count == 0:
            flash(
                f"⚠️ Aucun shift trouvé pour la semaine du {monday.strftime('%d/%m/%Y')}.",
                "warning",
            )
        else:
            flash(
                f"✅ Tous les {count} shifts de la semaine du {monday.strftime('%d/%m/%Y')} ont été supprimés avec succès !",
                "success",
            )
    except ValueError:
        flash("❌ Format de date invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("main.schedule"))


# ========== API ENDPOINTS POUR DRAG & DROP ====================


@main_bp.route("/api/shifts", methods=["POST"])
@login_required
@admin_required
def api_create_shift():
    """API endpoint pour créer un nouveau shift via drag & drop."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Aucune donnée reçue"}), 400

    try:
        user_id = data.get("userId")
        shift_type_id = data.get("shiftTypeId")
        start_str = data.get("start")
        end_str = data.get("end")

        if not all([user_id, shift_type_id, start_str]):
            return jsonify({"success": False, "error": "Données manquantes"}), 400

        user_id = int(user_id)
        shift_type_id = int(shift_type_id)

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"success": False, "error": "Utilisateur non trouvé"}), 404

        shift_type = ShiftTypeRepository.get_by_id(shift_type_id)
        if not shift_type:
            return jsonify({"success": False, "error": "Type de shift non trouvé"}), 404

        start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_time = (
            datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            if end_str
            else start_time
        )

        shift, error = ShiftService.api_create(user, shift_type, start_time, end_time)
        if error:
            return jsonify({"success": False, "error": error}), 400

        return jsonify(
            {
                "success": True,
                "message": "Shift créé avec succès",
                "shift": {
                    "id": shift.id,
                    "title": f"{user.name} - {shift_type.label}",
                    "start": shift.start_time.isoformat(),
                    "end": shift.end_time.isoformat(),
                    "className": "fc-event-shift",
                    "userId": user_id,
                    "shiftTypeId": shift_type_id,
                },
            }
        )

    except ValueError as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Format invalide: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500


@main_bp.route("/api/shifts/<int:shift_id>", methods=["PATCH", "PUT"])
@login_required
@admin_required
def api_update_shift(shift_id):
    """API endpoint pour mettre à jour un shift via drag & drop."""
    shift = ShiftRepository.get_by_id(shift_id)
    if not shift:
        return jsonify({"success": False, "error": "Shift non trouvé"}), 404

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
            duration = shift.end_time - shift.start_time
            new_end = new_start + duration

        updated_shift, error = ShiftService.api_update(shift_id, new_start, new_end)
        if error:
            return jsonify({"success": False, "error": error}), 400

        return jsonify(
            {
                "success": True,
                "message": "Shift mis à jour avec succès",
                "shift": {
                    "id": updated_shift.id,
                    "start": updated_shift.start_time.isoformat(),
                    "end": updated_shift.end_time.isoformat(),
                    "date": updated_shift.date.isoformat(),
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


@main_bp.route("/api/shifts/<int:shift_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_shift(shift_id):
    """API endpoint pour supprimer un shift via drag & drop."""
    if not ShiftRepository.get_by_id(shift_id):
        return jsonify({"success": False, "error": "Shift non trouvé"}), 404

    try:
        ShiftService.api_delete(shift_id)
        return jsonify({"success": True, "message": "Shift supprimé avec succès"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Erreur: {str(e)}"}), 500


@main_bp.route("/api/users", methods=["GET"])
@login_required
def api_get_users():
    """API endpoint pour récupérer la liste des utilisateurs pour le drag & drop."""
    users = UserService.visible_users_for_schedule(current_user)

    users_list = [
        {"id": user.id, "name": user.name, "email": user.email} for user in users
    ]

    return jsonify(users_list)


@main_bp.route("/api/shift-types", methods=["GET"])
@login_required
def api_get_shift_types():
    """API endpoint pour récupérer la liste des types de shifts."""
    shift_types = ShiftTypeRepository.get_all()

    shift_types_list = [
        {
            "id": st.id,
            "name": st.name,
            "label": st.label,
            "start_hour": st.start_hour,
            "end_hour": st.end_hour,
        }
        for st in shift_types
    ]

    return jsonify(shift_types_list)
