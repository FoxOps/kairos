import os


# Configuration de base pour Flask
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuration Flask-Login
    LOGIN_DISABLED = False  # Désactive l'authentification si True (pour dev/test)
    REMEMBER_COOKIE_DURATION = 86400  # 1 jour en secondes
    SESSION_PROTECTION = "strong"
