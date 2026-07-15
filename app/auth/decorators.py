"""
Decorators for role and permission management.

This module provides decorators to control access to Flask routes
based on user roles and permissions.

Usage:
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
from flask_babel import gettext as _
from flask_login import current_user, login_required


def admin_required(f):
    """
    Decorator to check that the user is an administrator.
    Redirects to the home page with a message if not authorized.

    Usage:
        @app.route('/admin')
        @admin_required
        def admin_dashboard():
            ...
    """

    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash(_("Accès refusé : vous devez être administrateur."), "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


def user_owns_resource(model, resource_id_param, user_id_attr="user_id"):
    """
    Decorator to check that the user owns a resource.

    An administrator can access all resources.
    A regular user can only access their own resources.

    Args:
        model: The resource's SQLAlchemy model (e.g. Leave, Shift, OnCall)
        resource_id_param: The name of the parameter holding the resource ID (e.g. 'leave_id')
        user_id_attr: The name of the model attribute holding the user_id (default: 'user_id')

    Usage:
        @app.route('/leave/delete/<int:leave_id>')
        @user_owns_resource(Leave, 'leave_id')
        def delete_leave(leave_id):
            from flask import abort
            leave = db.session.get(Leave, leave_id) or abort(404)
            # Ownership was already checked by the decorator
            db.session.delete(leave)
            db.session.commit()
            ...
    """

    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the resource ID from kwargs
            resource_id = kwargs.get(resource_id_param)

            # If we don't have the ID, we can't check, so let it through
            # (the route will likely return 404 anyway)
            if resource_id is None:
                return f(*args, **kwargs)

            # Fetch the resource from the database
            from app import db

            resource = db.session.get(model, resource_id)

            # If the resource doesn't exist, let it through (the route handles the 404)
            if resource is None:
                return f(*args, **kwargs)

            # Check whether the user owns it or is an admin
            resource_user_id = getattr(resource, user_id_attr, None)

            if current_user.is_admin or current_user.id == resource_user_id:
                return f(*args, **kwargs)

            flash(
                _("Accès refusé : vous ne pouvez modifier que vos propres données."),
                "danger",
            )
            return redirect(url_for("main.index"))

        return decorated_function

    return decorator
