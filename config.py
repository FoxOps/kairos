import os

# Configuration de base pour Flask
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ta-cle-secrete-ici'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False