"""
Admin routes for managing groups. Registered on admin_bp (see
app/routes/admin.py).
"""

from flask import abort, flash, redirect, render_template, request, url_for

from app import db
from app.auth.decorators import admin_required
from app.repositories.user_repository import GroupRepository
from app.routes.admin import admin_bp
from app.services import GroupService


@admin_bp.route("/admin/groups")
@admin_required
def list_groups():
    groups = GroupService.list_all()
    return render_template("admin/groups.html", groups=groups)


@admin_bp.route("/admin/groups/add", methods=["GET", "POST"])
@admin_required
def add_group():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        is_part_of_schedule = "is_part_of_schedule" in request.form
        is_part_of_oncall = "is_part_of_oncall" in request.form

        if not name:
            flash("❌ Le nom du groupe est obligatoire.", "danger")
            return redirect(url_for("admin.add_group"))

        try:
            group, error = GroupService.create(
                name, is_part_of_schedule, is_part_of_oncall
            )
            if error:
                flash(f"❌ {error}", "danger")
                return redirect(url_for("admin.add_group"))

            flash("✅ Groupe ajouté avec succès !", "success")
            return redirect(url_for("admin.list_groups"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/add_group.html")


@admin_bp.route("/admin/groups/edit/<int:group_id>", methods=["GET", "POST"])
@admin_required
def edit_group(group_id):
    group = GroupRepository.get_by_id(group_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        is_part_of_schedule = "is_part_of_schedule" in request.form
        is_part_of_oncall = "is_part_of_oncall" in request.form

        if not name:
            flash("❌ Le nom du groupe est obligatoire.", "danger")
            return redirect(url_for("admin.edit_group", group_id=group_id))

        try:
            updated_group, error = GroupService.update(
                group_id, name, is_part_of_schedule, is_part_of_oncall
            )
            if error:
                flash(f"❌ {error}", "danger")
                return redirect(url_for("admin.edit_group", group_id=group_id))

            flash("✅ Groupe modifié avec succès !", "success")
            return redirect(url_for("admin.list_groups"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/edit_group.html", group=group)


@admin_bp.route("/admin/groups/delete/<int:group_id>", methods=["POST"])
@admin_required
def delete_group(group_id):
    if not GroupRepository.get_by_id(group_id):
        abort(404)

    try:
        deleted, error = GroupService.delete(group_id)
        if error:
            flash(f"❌ {error}", "danger")
        elif deleted:
            flash("✅ Groupe supprimé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")

    return redirect(url_for("admin.list_groups"))
