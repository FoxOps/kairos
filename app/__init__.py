from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()

def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialiser les extensions
    db.init_app(app)

    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models

    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)

    return app

# Créer une instance par défaut pour le développement
app = create_app()
