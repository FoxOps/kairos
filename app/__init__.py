# ========== FICHIER: app/__init__.py (corrigé) ==========
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de l'application Flask
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialisation de la base de données
# CORRECTION : Suppression du point avant 'db'
db = SQLAlchemy(app)

# Import des modèles pour les enregistrer avec SQLAlchemy
from app import models

# Import des routes
from app.routes import main, admin, export