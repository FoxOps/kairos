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

from flask import flash, redirect, request, url_for
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


def handle_form_errors(f):
    """
    Decorator for admin add_*/edit_* views: wraps the view call in the
    generic try/except each of them used to repeat inline - an
    unexpected exception rolls back the session, flashes it, and
    redirects back to the same view (GET) via request.endpoint, which
    re-renders the form with a fresh copy of whatever context (groups,
    the edited object...) the GET branch already computes. Only the
    generic case: a route-specific except clause (e.g. ValueError on a
    malformed field) stays inline in the view, ahead of this decorator
    catching whatever it doesn't handle itself. HTTPException (e.g. the
    `abort(404)` every edit_* view uses to fetch its object) is
    deliberately let through unhandled - it's Flask's own routing
    control flow, not a form-processing error, and must keep producing
    its real status code rather than a flashed-error redirect.

    Only fit for add_*/edit_* views (registered for both GET and POST) -
    a delete_* route is POST-only, so redirecting to its own endpoint
    would 405.

    Usage:
        @app.route('/admin/things/add', methods=['GET', 'POST'])
        @admin_required
        @handle_form_errors
        def add_thing():
            ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from werkzeug.exceptions import HTTPException

        from app import db

        try:
            return f(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")
            return redirect(url_for(request.endpoint, **kwargs))

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
