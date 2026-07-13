"""
Routes admin pour la gestion des utilisateurs. Enregistrées sur admin_bp
(cf. app/routes/admin.py).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import selectinload

from app import db
from app.auth.decorators import admin_required
from app.models import User
from app.repositories.user_repository import GroupRepository, UserRepository
from app.routes.admin import admin_bp
from app.services import UserService
from app.utils.optimizations import eager_load


@admin_bp.route("/admin/users")
@admin_required
@eager_load(User, ["group", "shifts", "on_calls", "leaves"])
def list_users():
    users = (
        User.query.options(
            selectinload(User.group),
            selectinload(User.shifts),
            selectinload(User.on_calls),
            selectinload(User.leaves),
        )
        .order_by(User.name)
        .all()
    )
    groups = GroupRepository.get_all()
    return render_template("admin/users.html", users=users, groups=groups)


@admin_bp.route("/admin/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    groups = GroupRepository.get_all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        group_id = request.form.get("group_id")
        password = request.form.get("password", "")

        if not all([name, email, group_id]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return render_template("admin/add_user.html", groups=groups)

        try:
            user, error = UserService.create(name, email, int(group_id), password)
            if error:
                flash(f"❌ {error}", "danger")
                return render_template("admin/add_user.html", groups=groups)

            flash("✅ Utilisateur ajouté avec succès !", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/add_user.html", groups=groups)


@admin_bp.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = UserRepository.get_by_id(user_id) or abort(404)
    groups = GroupRepository.get_all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        group_id = request.form.get("group_id")
        is_admin = "is_admin" in request.form
        password = request.form.get("password", "")

        if not all([name, email, group_id]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return render_template("admin/edit_user.html", user=user, groups=groups)

        try:
            updated_user, error = UserService.update(
                user_id, name, email, int(group_id), is_admin, password
            )
            if error:
                flash(f"❌ {error}", "danger")
                return render_template("admin/edit_user.html", user=user, groups=groups)

            flash("✅ Utilisateur modifié avec succès !", "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/edit_user.html", user=user, groups=groups)


@admin_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if not UserRepository.get_by_id(user_id):
        abort(404)

    try:
        deleted, error = UserService.delete(user_id)
        if error:
            flash(f"❌ {error}", "danger")
        elif deleted:
            flash("✅ Utilisateur supprimé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")

    return redirect(url_for("admin.list_users"))
