"""
Admin blueprint ("admin"). Routes are defined in separate files by
domain (admin_group_routes, admin_user_routes, admin_shift_type_routes,
admin_automation_routes, admin_backup_routes, admin_settings_routes)
which all register onto the admin_bp defined here - the blueprint name
stays "admin" everywhere (url_for("admin.xxx"), templates), only the
file split changes.
"""

from flask import Blueprint, render_template
from sqlalchemy import func

from app import db
from app.auth.decorators import admin_required
from app.models import Group, Leave, OnCall, Shift, SwapRequest, User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    users_count = db.session.query(func.count(User.id)).scalar()
    shifts_count = db.session.query(func.count(Shift.id)).scalar()
    on_calls_count = db.session.query(func.count(OnCall.id)).scalar()
    leaves_count = db.session.query(func.count(Leave.id)).scalar()
    groups_count = db.session.query(func.count(Group.id)).scalar()
    pending_swaps_count = (
        db.session.query(func.count(SwapRequest.id))
        .filter(SwapRequest.status == SwapRequest.AWAITING_ADMIN)
        .scalar()
    )

    return render_template(
        "admin/dashboard.html",
        users_count=users_count,
        shifts_count=shifts_count,
        on_calls_count=on_calls_count,
        leaves_count=leaves_count,
        groups_count=groups_count,
        pending_swaps_count=pending_swaps_count,
    )


# These imports trigger route registration onto admin_bp (each module
# does `from app.routes.admin import admin_bp` then decorates its
# functions with @admin_bp.route(...)). Must stay after admin_bp is
# created above.
from app.routes import (  # noqa: E402
    admin_audit_routes,  # noqa: F401
    admin_automation_routes,  # noqa: F401
    admin_backup_routes,  # noqa: F401
    admin_group_routes,  # noqa: F401
    admin_notification_target_routes,  # noqa: F401
    admin_settings_routes,  # noqa: F401
    admin_shift_type_routes,  # noqa: F401
    admin_swap_routes,  # noqa: F401
    admin_user_routes,  # noqa: F401
)
