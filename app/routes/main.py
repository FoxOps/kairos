"""
Blueprint principal ("main"). Les routes sont définies dans des fichiers
séparés par domaine (dashboard_routes, shift_routes, oncall_routes,
leave_routes) qui s'enregistrent tous sur main_bp défini ici - le nom du
blueprint reste "main" partout (url_for("main.xxx"), templates), seul le
découpage en fichiers change.
"""

from flask import Blueprint

main_bp = Blueprint("main", __name__)

# Ces imports déclenchent l'enregistrement des routes sur main_bp
# (chaque module fait `from app.routes.main import main_bp` puis décore
# ses fonctions avec @main_bp.route(...)). Doivent rester après la
# création de main_bp ci-dessus.
from app.routes import (  # noqa: E402
    dashboard_routes,  # noqa: F401
    leave_routes,  # noqa: F401
    oncall_routes,  # noqa: F401
    shift_routes,  # noqa: F401
    swap_routes,  # noqa: F401
)
