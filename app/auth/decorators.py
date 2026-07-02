"""
Décorateurs pour la gestion des rôles et permissions.

Ce module fournit des décorateurs pour contrôler l'accès aux routes Flask
en fonction des rôles des utilisateurs et des permissions.

Rôles disponibles:
- admin: Accès complet à toutes les fonctionnalités
- user: Accès limité à ses propres données

Utilisation:
    from app.utils.decorators import admin_required, role_required, user_owns_resource

    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        ...

    @app.route('/profile')
    @role_required('user')
    def profile():
        ...

    @app.route('/leave/delete/<int:leave_id>')
    @user_owns_resource(Leave, 'leave_id')
    def delete_leave(leave_id):
        ...
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
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
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    """
    Décorateur générique pour vérifier que l'utilisateur a un rôle spécifique.

    Args:
        *roles: Liste des rôles autorisés (ex: 'admin', 'user')

    Utilisation:
        @app.route('/dashboard')
        @role_required('admin', 'user')
        def dashboard():
            ...
    """

    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Vérifier si l'utilisateur a au moins un des rôles requis
            has_required_role = False

            # L'admin a tous les droits
            if "admin" in roles and current_user.is_admin:
                has_required_role = True

            # Un utilisateur authentifié a le rôle 'user'
            if "user" in roles and current_user.is_authenticated:
                has_required_role = True

            if not has_required_role:
                flash("❌ Accès refusé : permissions insuffisantes.", "danger")
                return redirect(url_for("index"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


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
            return redirect(url_for("index"))

        return decorated_function

    return decorator


def user_can_edit_resource(model, resource_id_param, user_id_attr="user_id"):
    """
    Décorateur pour vérifier que l'utilisateur peut éditer une ressource.

    C'est un alias de user_owns_resource pour plus de clarté.

    Args:
        model: Le modèle SQLAlchemy de la ressource
        resource_id_param: Le nom du paramètre contenant l'ID de la ressource
        user_id_attr: Le nom de l'attribut du modèle qui contient l'user_id

    Utilisation:
        @app.route('/leave/edit/<int:leave_id>')
        @user_can_edit_resource(Leave, 'leave_id')
        def edit_leave(leave_id):
            ...
    """
    return user_owns_resource(model, resource_id_param, user_id_attr)


def user_can_delete_resource(model, resource_id_param, user_id_attr="user_id"):
    """
    Décorateur pour vérifier que l'utilisateur peut supprimer une ressource.

    C'est un alias de user_owns_resource pour plus de clarté.

    Args:
        model: Le modèle SQLAlchemy de la ressource
        resource_id_param: Le nom du paramètre contenant l'ID de la ressource
        user_id_attr: Le nom de l'attribut du modèle qui contient l'user_id

    Utilisation:
        @app.route('/leave/delete/<int:leave_id>')
        @user_can_delete_resource(Leave, 'leave_id')
        def delete_leave(leave_id):
            ...
    """
    return user_owns_resource(model, resource_id_param, user_id_attr)


# Décorateurs obsolètes - conservés pour compatibilité
# Ces décorateurs sont conservés pour la rétrocompatibilité mais ne sont pas recommandés
# pour les nouvelles implémentations. Utilisez plutôt user_owns_resource.


def user_can_edit(user_id):
    """
    Décorateur pour vérifier que l'utilisateur peut éditer une ressource.
    L'admin peut tout éditer, un utilisateur normal ne peut éditer que ses propres ressources.

    Args:
        user_id: L'ID de l'utilisateur propriétaire de la ressource

    Utilisation:
        @user_can_edit('user_id')
        def edit_shift(user_id):
            ...

    Note: Ce décorateur est obsolète. Utilisez user_owns_resource à la place.
    """

    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Récupérer l'user_id depuis les args ou kwargs
            func_user_id = None

            # Chercher dans kwargs d'abord
            if user_id in kwargs:
                func_user_id = kwargs[user_id]
            # Sinon chercher dans args (positionnel)
            elif len(args) > 0:
                # Si user_id est un index
                if isinstance(user_id, int):
                    if user_id < len(args):
                        func_user_id = args[user_id]
                # Si user_id est un nom de paramètre
                else:
                    # On ne peut pas savoir la position, donc on utilise kwargs
                    pass

            # Si on n'a pas trouvé l'user_id, on autorise (cas des routes sans user_id)
            if func_user_id is None:
                return f(*args, **kwargs)

            # Vérifier les permissions
            if current_user.is_admin or current_user.id == func_user_id:
                return f(*args, **kwargs)

            flash(
                "❌ Accès refusé : vous ne pouvez modifier que vos propres données.",
                "danger",
            )
            return redirect(url_for("index"))

        return decorated_function

    return decorator


def user_can_delete(resource_type, user_id_param="user_id"):
    """
    Décorateur pour vérifier que l'utilisateur peut supprimer une ressource.

    Args:
        resource_type: Type de ressource ('shift', 'oncall', 'leave')
        user_id_param: Nom du paramètre contenant l'user_id

    Utilisation:
        @user_can_delete('shift', 'user_id')
        def delete_shift(shift_id):
            ...

    Note: Ce décorateur est obsolète. Utilisez user_owns_resource à la place.
    """

    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Pour les routes de suppression, on vérifie l'user_id de la ressource
            # On suppose que la fonction va récupérer la ressource et vérifier son user_id
            # On ne peut pas faire la vérification ici sans accéder à la DB
            # Donc on laisse la vérification dans la route elle-même
            return f(*args, **kwargs)

        return decorated_function

    return decorator
