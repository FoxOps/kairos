import os


# Configuration de base pour Flask
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuration SQLite pour éviter les problèmes de "database is locked"
    # Ces paramètres permettent une meilleure gestion des accès concurrents
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "timeout": 30,  # Timeout de connexion en secondes
            "isolation_level": None,  # Désactive l'isolation pour SQLite (utilise AUTCOMMIT)
        },
        "pool_pre_ping": True,  # Vérifie la connexion avant de l'utiliser
        "pool_recycle": 3600,  # Recycle les connexions après 1 heure
        "pool_size": 5,  # Nombre de connexions dans le pool
        "max_overflow": 10,  # Nombre maximal de connexions supplémentaires
    }

    # Configuration Flask-Login
    LOGIN_DISABLED = False  # Désactive l'authentification si True (pour dev/test)
    REMEMBER_COOKIE_DURATION = 86400  # 1 jour en secondes
    SESSION_PROTECTION = "strong"
