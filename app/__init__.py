from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import time
import sqlite3

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


# Gestion des erreurs de base de données verrouillée pour SQLite
# SQLAlchemy 2.0 utilise un système d'événements différent
# On va utiliser une approche plus simple avec des retries au niveau de l'application

def execute_with_retry(func, max_retries=5, delay=0.1):
    """Exécute une fonction avec des retries en cas d'erreur de base de données verrouillée."""
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise
    raise sqlite3.OperationalError("Database locked after maximum retries")


@login_manager.user_loader
def load_user(user_id):
    """Charger l'utilisateur depuis la base de données."""
    from app.models import User

    # Utiliser le retry mechanism pour éviter les erreurs "database is locked"
    def _load():
        return db.session.get(User, int(user_id))
    
    return execute_with_retry(_load)


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
