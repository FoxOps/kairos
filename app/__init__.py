from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialisation de la base de données
db = SQLAlchemy()

# Initialisation de Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login"  # Route pour la page de login
login_manager.login_message_category = "danger"  # Catégorie pour les messages flash

# Créer l'instance Flask
app = Flask(__name__)
app.config.from_object("config.Config")

# Initialiser les extensions
db.init_app(app)
login_manager.init_app(app)

# Importer les modèles
from app import models

# NE PAS importer les routes ici pour éviter la circularité
# Les routes seront importées dans run.py ou par l'utilisateur


@login_manager.user_loader
def load_user(user_id):
    """Charger l'utilisateur depuis la base de données."""
    from app.models import User

    return User.query.get(int(user_id))


# Gestion des erreurs personnalisées
@app.errorhandler(403)
def forbidden_error(error):
    """Page d'erreur 403 personnalisée."""
    from flask import render_template

    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found_error(error):
    """Page d'erreur 404 personnalisée."""
    from flask import render_template

    return render_template("404.html"), 404


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    return app
