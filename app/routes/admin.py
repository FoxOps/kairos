"""
Blueprint admin ("admin"). Les routes sont définies dans des fichiers
séparés par domaine (admin_group_routes, admin_user_routes,
admin_shift_type_routes, admin_automation_routes) qui s'enregistrent
tous sur admin_bp défini ici - le nom du blueprint reste "admin" partout
(url_for("admin.xxx"), templates), seul le découpage en fichiers change.
"""

from flask import Blueprint, render_template
from sqlalchemy import func

from app import db
from app.auth.decorators import admin_required
from app.models import Group, Leave, OnCall, Shift, User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    users_count = db.session.query(func.count(User.id)).scalar()
    shifts_count = db.session.query(func.count(Shift.id)).scalar()
    on_calls_count = db.session.query(func.count(OnCall.id)).scalar()
    leaves_count = db.session.query(func.count(Leave.id)).scalar()
    groups_count = db.session.query(func.count(Group.id)).scalar()

    return render_template(
        "admin/dashboard.html",
        users_count=users_count,
        shifts_count=shifts_count,
        on_calls_count=on_calls_count,
        leaves_count=leaves_count,
        groups_count=groups_count,
    )


# Ces imports déclenchent l'enregistrement des routes sur admin_bp
# (chaque module fait `from app.routes.admin import admin_bp` puis décore
# ses fonctions avec @admin_bp.route(...)). Doivent rester après la
# création de admin_bp ci-dessus.
from app.routes import (  # noqa: E402
    admin_automation_routes,  # noqa: F401
    admin_group_routes,  # noqa: F401
    admin_shift_type_routes,  # noqa: F401
    admin_user_routes,  # noqa: F401
)
