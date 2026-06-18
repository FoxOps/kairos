from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de la base de données
db = SQLAlchemy()

# Créer l'instance Flask
app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

# Importer les modèles
from app import models

# NE PAS importer les routes ici pour éviter la circularité
# Les routes seront importées dans run.py ou par l'utilisateur


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    return app
