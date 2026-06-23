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
    
    # Configuration SQLAlchemy
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "false").lower() == "true"

    # ============================================================================
    # CONFIGURATION DE LA GESTION DES ERREURS
    # ============================================================================

    # Afficher les détails des erreurs en mode développement
    # ⚠️ NE JAMAIS activer en production !
    DEBUG_ERRORS = os.environ.get("DEBUG_ERRORS", "false").lower() == "true"

    # Configuration du logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE_SIZE = int(os.environ.get("LOG_FILE_SIZE", 5 * 1024 * 1024))  # 5 Mo par fichier de log
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))  # Nombre de fichiers de backup
    LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    # Configuration des fichiers de log
    LOG_FILE_APP = os.environ.get("LOG_FILE_APP", "leviia-app.log")
    LOG_FILE_ERRORS = os.environ.get("LOG_FILE_ERRORS", "leviia-errors.log")
    LOG_FILE_HTTP = os.environ.get("LOG_FILE_HTTP", "leviia-http-errors.log")
    LOG_FILE_DEBUG = os.environ.get("LOG_FILE_DEBUG", "leviia-debug.log")
    LOG_FILE_AUDIT = os.environ.get("LOG_FILE_AUDIT", "leviia-audit.log")
    
    # Niveaux de log par module
    LOG_LEVEL_APP = os.environ.get("LOG_LEVEL_APP", LOG_LEVEL)
    LOG_LEVEL_ERRORS = os.environ.get("LOG_LEVEL_ERRORS", "ERROR")
    LOG_LEVEL_HTTP = os.environ.get("LOG_LEVEL_HTTP", "WARNING")
    LOG_LEVEL_DEBUG = os.environ.get("LOG_LEVEL_DEBUG", "DEBUG")
    LOG_LEVEL_AUDIT = os.environ.get("LOG_LEVEL_AUDIT", "INFO")
    
    # Configuration syslog pour la production
    SYSLOG_ENABLED = os.environ.get("SYSLOG_ENABLED", "false").lower() == "true"
    SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS", "/dev/log")
    SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY", "local0")
    
    # Filtres de log
    LOG_FILTER_SENSITIVE = os.environ.get("LOG_FILTER_SENSITIVE", "true").lower() == "true"
    LOG_FILTER_PATTERNS = [
        r'password["\']?\s*[:=]\s*[^\s]+',
        r'secret["\']?\s*[:=]\s*[^\s]+',
        r'token["\']?\s*[:=]\s*[^\s]+',
        r'api[_-]?key["\']?\s*[:=]\s*[^\s]+',
        r'auth["\']?\s*[:=]\s*[^\s]+',
    ]
    
    # Format des logs
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_DATE_FORMAT = os.environ.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")

    # Configuration des erreurs HTTP
    # Afficher les pages d'erreur personnalisées
    SHOW_CUSTOM_ERROR_PAGES = True

    # Message par défaut pour les erreurs 500
    ERROR_500_MESSAGE = "Une erreur interne du serveur s'est produite. Veuillez réessayer plus tard."

    # Message par défaut pour les erreurs 503
    ERROR_503_MESSAGE = "Service temporairement indisponible. Veuillez réessayer dans quelques instants."

    # Délai de réessai pour les erreurs 503 (en secondes)
    ERROR_503_RETRY_AFTER = 300  # 5 minutes

    # ============================================================================
    # CONFIGURATION DE SÉCURITÉ
    # ============================================================================

    # Désactiver le cache pour les pages d'erreur
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # Configuration CORS (si nécessaire)
    CORS_ENABLED = os.environ.get("CORS_ENABLED", "false").lower() == "true"

    # ============================================================================
    # CONFIGURATION POUR LES TESTS
    # ============================================================================

    # Configuration spécifique pour les tests
    TESTING = os.environ.get("FLASK_TESTING", "false").lower() == "true"


class DevelopmentConfig(Config):
    """Configuration pour le développement."""
    DEBUG = True
    DEBUG_ERRORS = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_ECHO = True  # Afficher les requêtes SQL


class ProductionConfig(Config):
    """Configuration pour la production."""
    DEBUG = False
    DEBUG_ERRORS = False
    LOG_LEVEL = "WARNING"
    SQLALCHEMY_ECHO = False
    
    # Utiliser une base de données plus robuste en production
    # Exemple : PostgreSQL
    # SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "postgresql://user:password@localhost/leviia"


class TestingConfig(Config):
    """Configuration pour les tests."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LOG_LEVEL = "DEBUG"
    DEBUG_ERRORS = True


# Sélection de la configuration en fonction de l'environnement
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

# Récupérer la configuration depuis la variable d'environnement
FLASK_ENV = os.environ.get("FLASK_ENV") or "default"
CurrentConfig = config_map.get(FLASK_ENV, DevelopmentConfig)
