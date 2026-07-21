"""
Admin routes for managing users. Registered on admin_bp (see
app/routes/admin.py).
"""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from sqlalchemy.orm import selectinload

from app import db
from app.auth.decorators import admin_required
from app.models import User
from app.repositories.user_repository import GroupRepository, UserRepository
from app.routes.admin import admin_bp
from app.services import UserService


@admin_bp.route("/admin/users")
@admin_required
def list_users():
    # admin/users.html only displays user.group.name - shifts/on_calls/leaves
    # are never rendered there, preloading them was just wasting queries
    # (and growing unbounded with each user's history).
    users = User.query.options(selectinload(User.group)).order_by(User.name).all()
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
            flash(_("Tous les champs sont obligatoires."), "danger")
            return render_template("admin/add_user.html", groups=groups)

        try:
            user, error, generated_password = UserService.create(
                name, email, int(group_id), password
            )
            if error:
                flash(error, "danger")
                return render_template("admin/add_user.html", groups=groups)

            flash(_("Utilisateur ajouté avec succès !"), "success")
            if generated_password:
                # One-time reveal, same pattern as ServiceAccount tokens
                # (see admin_service_account_routes.py) - this value is
                # never stored anywhere else, so this flash is the only
                # chance to hand it to the admin.
                flash(
                    _(
                        "Mot de passe généré automatiquement : %(password)s "
                        "(à communiquer à l'utilisateur - il devra le "
                        "changer à sa première connexion, ce mot de passe "
                        "ne sera plus jamais affiché).",
                        password=generated_password,
                    ),
                    "warning",
                )
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

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
            flash(_("Tous les champs sont obligatoires."), "danger")
            return render_template("admin/edit_user.html", user=user, groups=groups)

        try:
            updated_user, error = UserService.update(
                user_id, name, email, int(group_id), is_admin, password
            )
            if error:
                flash(error, "danger")
                return render_template("admin/edit_user.html", user=user, groups=groups)

            flash(_("Utilisateur modifié avec succès !"), "success")
            return redirect(url_for("admin.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    return render_template("admin/edit_user.html", user=user, groups=groups)


@admin_bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if not UserRepository.get_by_id(user_id):
        abort(404)

    try:
        deleted, error = UserService.delete(user_id)
        if error:
            flash(error, "danger")
        elif deleted:
            flash(_("Utilisateur supprimé avec succès !"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    return redirect(url_for("admin.list_users"))
