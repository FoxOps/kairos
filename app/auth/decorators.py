"""
Décorateurs pour la gestion des rôles et permissions.

Ce module fournit des décorateurs pour contrôler l'accès aux routes Flask
en fonction des rôles des utilisateurs et des permissions.

Utilisation:
    from app.auth.decorators import admin_required, user_owns_resource

    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        ...

    @app.route('/leave/delete/<int:leave_id>')
    @user_owns_resource(Leave, 'leave_id')
    def delete_leave(leave_id):
        ...
"""

from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def admin_required(f):
    """
    Décorateur pour vérifier que l'utilisateur est administrateur.
    Redirige vers la page d'accueil avec un message si non autorisé.

    Utilisation:
        @app.route('/admin')
        @admin_required
        def admin_dashboard():
            ...
    """

    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("❌ Accès refusé : vous devez être administrateur.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


def user_owns_resource(model, resource_id_param, user_id_attr="user_id"):
    """
    Décorateur pour vérifier que l'utilisateur est propriétaire d'une ressource.

    L'administrateur peut accéder à toutes les ressources.
    Un utilisateur normal ne peut accéder qu'à ses propres ressources.

    Args:
        model: Le modèle SQLAlchemy de la ressource (ex: Leave, Shift, OnCall)
        resource_id_param: Le nom du paramètre contenant l'ID de la ressource (ex: 'leave_id')
        user_id_attr: Le nom de l'attribut du modèle qui contient l'user_id (par défaut: 'user_id')

    Utilisation:
        @app.route('/leave/delete/<int:leave_id>')
        @user_owns_resource(Leave, 'leave_id')
        def delete_leave(leave_id):
            from flask import abort
            leave = db.session.get(Leave, leave_id) or abort(404)
            # La vérification de propriété est déjà faite par le décorateur
            db.session.delete(leave)
            db.session.commit()
            ...
    """

    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Récupérer l'ID de la ressource depuis kwargs
            resource_id = kwargs.get(resource_id_param)

            # Si on n'a pas l'ID, on ne peut pas vérifier, donc on laisse passer
            # (la route va probablement retourner 404 de toute façon)
            if resource_id is None:
                return f(*args, **kwargs)

            # Récupérer la ressource depuis la base de données
            from app import db

            resource = db.session.get(model, resource_id)

            # Si la ressource n'existe pas, on laisse passer (la route va gérer le 404)
            if resource is None:
                return f(*args, **kwargs)

            # Vérifier si l'utilisateur est propriétaire ou admin
            resource_user_id = getattr(resource, user_id_attr, None)

            if current_user.is_admin or current_user.id == resource_user_id:
                return f(*args, **kwargs)

            flash(
                "❌ Accès refusé : vous ne pouvez modifier que vos propres données.",
                "danger",
            )
            return redirect(url_for("main.index"))

        return decorated_function

    return decorator
