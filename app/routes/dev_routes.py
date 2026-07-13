"""
Route de style-guide interne (admin uniquement) - checkpoint temporaire
de la refonte visuelle Dracula/Alucard (Phase 0), pas destinée à rester
en place indéfiniment (retrait prévu en Phase 8 de la refonte, voir
app/templates/dev/styleguide.html). Enregistrée sur main_bp (cf.
app/routes/main.py).
"""

from flask import render_template

from app.auth.decorators import admin_required
from app.routes.main import main_bp


@main_bp.route("/dev/styleguide")
@admin_required
def styleguide():
    """Aperçu isolé de la palette et des composants daisyUI (admin only)."""
    return render_template("dev/styleguide.html")
