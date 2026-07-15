"""
Main blueprint ("main"). Routes are defined in separate files by domain
(dashboard_routes, shift_routes, oncall_routes, leave_routes) which all
register onto the main_bp defined here - the blueprint name stays
"main" everywhere (url_for("main.xxx"), templates), only the file split
changes.
"""

from flask import Blueprint

main_bp = Blueprint("main", __name__)

# These imports trigger route registration onto main_bp (each module
# does `from app.routes.main import main_bp` then decorates its
# functions with @main_bp.route(...)). Must stay after main_bp is
# created above.
from app.routes import (  # noqa: E402
    dashboard_routes,  # noqa: F401
    leave_routes,  # noqa: F401
    notification_routes,  # noqa: F401
    oncall_routes,  # noqa: F401
    shift_routes,  # noqa: F401
    swap_routes,  # noqa: F401
)
