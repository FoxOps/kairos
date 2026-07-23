"""
Admin routes for managing shift types. Registered on admin_bp (see
app/routes/admin.py).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app import db
from app.auth.decorators import admin_required, handle_form_errors
from app.repositories.shift_repository import ShiftTypeRepository
from app.routes.admin import admin_bp
from app.services import ShiftTypeService


@admin_bp.route("/admin/shift-types")
@admin_required
def list_shift_types():
    shift_types = ShiftTypeService.list_all()
    return render_template("admin/shift_types.html", shift_types=shift_types)


@admin_bp.route("/admin/shift-types/add", methods=["GET", "POST"])
@admin_required
@handle_form_errors
def add_shift_type():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        label = request.form.get("label", "").strip()
        start_hour = request.form.get("start_hour")
        end_hour = request.form.get("end_hour")

        if not all([name, label, start_hour, end_hour]):
            flash(_("Tous les champs sont obligatoires."), "danger")
            return redirect(url_for("admin.add_shift_type"))

        try:
            shift_type, error = ShiftTypeService.create(
                name, label, int(start_hour), int(end_hour)
            )
        except ValueError:
            db.session.rollback()
            flash(_("Les heures doivent être des nombres entiers."), "danger")
            return redirect(url_for("admin.add_shift_type"))

        if error:
            flash(error, "danger")
            return redirect(url_for("admin.add_shift_type"))

        flash(_("Type de shift ajouté avec succès !"), "success")
        return redirect(url_for("admin.list_shift_types"))

    return render_template("admin/add_shift_type.html")


@admin_bp.route("/admin/shift-types/edit/<int:shift_type_id>", methods=["GET", "POST"])
@admin_required
@handle_form_errors
def edit_shift_type(shift_type_id):
    shift_type = ShiftTypeRepository.get_by_id(shift_type_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        label = request.form.get("label", "").strip()
        start_hour = request.form.get("start_hour")
        end_hour = request.form.get("end_hour")

        if not all([name, label, start_hour, end_hour]):
            flash(_("Tous les champs sont obligatoires."), "danger")
            return redirect(
                url_for("admin.edit_shift_type", shift_type_id=shift_type_id)
            )

        try:
            updated, error = ShiftTypeService.update(
                shift_type_id, name, label, int(start_hour), int(end_hour)
            )
        except ValueError:
            db.session.rollback()
            flash(_("Les heures doivent être des nombres entiers."), "danger")
            return redirect(
                url_for("admin.edit_shift_type", shift_type_id=shift_type_id)
            )

        if error:
            flash(error, "danger")
            return redirect(
                url_for("admin.edit_shift_type", shift_type_id=shift_type_id)
            )

        flash(_("Type de shift modifié avec succès !"), "success")
        return redirect(url_for("admin.list_shift_types"))

    return render_template("admin/edit_shift_type.html", shift_type=shift_type)


@admin_bp.route("/admin/shift-types/delete/<int:shift_type_id>", methods=["POST"])
@admin_required
def delete_shift_type(shift_type_id):
    if not ShiftTypeRepository.get_by_id(shift_type_id):
        abort(404)

    try:
        deleted, error = ShiftTypeService.delete(shift_type_id)
        if error:
            flash(error, "danger")
        elif deleted:
            flash(_("Type de shift supprimé avec succès !"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    return redirect(url_for("admin.list_shift_types"))
