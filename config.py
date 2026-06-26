import os
import json
import logging

# Charger les variables d'environnement depuis un fichier .env si présent
# Cela permet une configuration facile sans modifier le code
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv n'est pas installé, on utilise uniquement les variables d'environnement système
    pass


# Fonction utilitaire pour convertir les valeurs booléennes depuis les variables d'environnement
def get_bool_from_env(env_var, default=False):
    """Convertit une variable d'environnement en booléen.
    
    Accepte: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    value_lower = value.lower().strip()
    if value_lower in ('true', '1', 'yes', 'y', 'on'):
        return True
    elif value_lower in ('false', '0', 'no', 'n', 'off'):
        return False
    else:
        # Pour la compatibilité ascendante, retourner la valeur par défaut
        # mais logger un avertissement si la valeur n'est pas reconnue
        if value_lower:
            logging.warning(f"Valeur non reconnue pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


# Fonction utilitaire pour obtenir une valeur entière depuis les variables d'environnement
def get_int_from_env(env_var, default=0):
    """Convertit une variable d'environnement en entier."""
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    try:
        return int(value.strip())
    except ValueError:
        logging.warning(f"Valeur non entière pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


# Fonction utilitaire pour obtenir une valeur JSON depuis les variables d'environnement
def get_json_from_env(env_var, default=None):
    """Convertit une variable d'environnement en objet Python via JSON."""
    value = os.environ.get(env_var)
    if value is None or value.strip() == '':
        return default
    
    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        logging.warning(f"Valeur JSON invalide pour {env_var}: '{value}'. Utilisation de la valeur par défaut")
        return default


# Fonction utilitaire pour détecter le type de base de données
# Doit être définie avant la classe Config pour éviter les problèmes de référence circulaire
def get_database_type(database_uri=None):
    """Détecte le type de base de données à partir de l'URI."""
    if database_uri is None:
        database_uri = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    
    if database_uri.startswith("postgresql://") or database_uri.startswith("postgres://"):
        return "postgresql"
    elif database_uri.startswith("mysql://") or database_uri.startswith("mariadb://"):
        return "mysql"
    elif database_uri.startswith("sqlite://"):
        return "sqlite"
    else:
        # Par défaut, on suppose SQLite
        return "sqlite"


# Configuration de base pour Flask
class Config:
    # Clé secrète pour Flask (OBLIGATOIRE en production)
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"
    
    # URI de la base de données - peut être configurée via DATABASE_URL
    # SQLite reste la base de données par défaut
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = get_bool_from_env("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    
    # Détecter le type de base de données à partir de l'URI
    @staticmethod
    def get_database_type(database_uri=None):
        """Détecte le type de base de données à partir de l'URI."""
        return get_database_type(database_uri or Config.SQLALCHEMY_DATABASE_URI)
    
    # Configuration des options du moteur SQLAlchemy selon le type de base de données
    custom_engine_options = get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS")
    if custom_engine_options:
        SQLALCHEMY_ENGINE_OPTIONS = custom_engine_options
    else:
        # Utiliser la variable d'environnement directement pour éviter les problèmes de référence circulaire
        db_type = get_database_type(os.environ.get("DATABASE_URL") or "sqlite:///app.db")
        
        if db_type == "sqlite":
            # Configuration SQLite pour éviter les problèmes de "database is locked"
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {
                    "timeout": get_int_from_env("DATABASE_CONNECT_TIMEOUT", 30),  # Timeout de connexion en secondes
                    "isolation_level": None,  # Désactive l'isolation pour SQLite (utilise AUTCOMMIT)
                },
                "pool_pre_ping": True,  # Vérifie la connexion avant de l'utiliser
                "pool_recycle": get_int_from_env("DATABASE_POOL_RECYCLE", 3600),  # Recycle les connexions après 1 heure
                "pool_size": get_int_from_env("DATABASE_POOL_SIZE", 5),  # Nombre de connexions dans le pool
                "max_overflow": get_int_from_env("DATABASE_MAX_OVERFLOW", 10),  # Nombre maximal de connexions supplémentaires
            }
        elif db_type == "postgresql":
            # Configuration PostgreSQL optimisée
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {
                    "connect_timeout": get_int_from_env("DATABASE_CONNECT_TIMEOUT", 10),  # Timeout de connexion en secondes
                },
                "pool_pre_ping": True,  # Vérifie la connexion avant de l'utiliser
                "pool_recycle": get_int_from_env("DATABASE_POOL_RECYCLE", 3600),  # Recycle les connexions après 1 heure
                "pool_size": get_int_from_env("DATABASE_POOL_SIZE", 10),  # Nombre de connexions dans le pool
                "max_overflow": get_int_from_env("DATABASE_MAX_OVERFLOW", 20),  # Nombre maximal de connexions supplémentaires
            }
        elif db_type == "mysql":
            # Configuration MariaDB/MySQL optimisée
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {
                    "connect_timeout": get_int_from_env("DATABASE_CONNECT_TIMEOUT", 10),  # Timeout de connexion en secondes
                    "charset": "utf8mb4",  # Support complet des caractères Unicode
                    "collation": "utf8mb4_unicode_ci",  # Collation Unicode
                },
                "pool_pre_ping": True,  # Vérifie la connexion avant de l'utiliser
                "pool_recycle": get_int_from_env("DATABASE_POOL_RECYCLE", 3600),  # Recycle les connexions après 1 heure
                "pool_size": get_int_from_env("DATABASE_POOL_SIZE", 10),  # Nombre de connexions dans le pool
                "max_overflow": get_int_from_env("DATABASE_MAX_OVERFLOW", 20),  # Nombre maximal de connexions supplémentaires
            }
        else:
            # Configuration par défaut (SQLite)
            SQLALCHEMY_ENGINE_OPTIONS = {
                "connect_args": {
                    "timeout": get_int_from_env("DATABASE_CONNECT_TIMEOUT", 30),
                    "isolation_level": None,
                },
                "pool_pre_ping": True,
                "pool_recycle": get_int_from_env("DATABASE_POOL_RECYCLE", 3600),
                "pool_size": get_int_from_env("DATABASE_POOL_SIZE", 5),
                "max_overflow": get_int_from_env("DATABASE_MAX_OVERFLOW", 10),
            }

    # Configuration Flask-Login
    LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)  # Désactive l'authentification si True (pour dev/test)
    REMEMBER_COOKIE_DURATION = get_int_from_env("REMEMBER_COOKIE_DURATION", 86400)  # 1 jour en secondes
    SESSION_PROTECTION = os.environ.get("SESSION_PROTECTION") or "strong"
    
    # Configuration SQLAlchemy
    SQLALCHEMY_ECHO = get_bool_from_env("SQLALCHEMY_ECHO", False)

    # ============================================================================
    # CONFIGURATION DE LA GESTION DES ERREURS
    # ============================================================================

    # Afficher les détails des erreurs en mode développement
    # WARNING: NE JAMAIS activer en production !
    DEBUG_ERRORS = get_bool_from_env("DEBUG_ERRORS", False)

    # Afficher les pages d'erreur personnalisées
    SHOW_CUSTOM_ERROR_PAGES = get_bool_from_env("SHOW_CUSTOM_ERROR_PAGES", True)
    
    # Messages d'erreur personnalisés
    ERROR_500_MESSAGE = os.environ.get("ERROR_500_MESSAGE") or "Une erreur interne du serveur s'est produite. Veuillez reessayer plus tard."
    ERROR_503_MESSAGE = os.environ.get("ERROR_503_MESSAGE") or "Service temporairement indisponible. Veuillez reessayer dans quelques instants."
    ERROR_503_RETRY_AFTER = get_int_from_env("ERROR_503_RETRY_AFTER", 300)  # 5 minutes

    # ============================================================================
    # CONFIGURATION DU LOGGING
    # ============================================================================

    # Configuration du logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE_SIZE = get_int_from_env("LOG_FILE_SIZE", 5 * 1024 * 1024)  # 5 Mo par fichier de log
    LOG_BACKUP_COUNT = get_int_from_env("LOG_BACKUP_COUNT", 10)  # Nombre de fichiers de backup
    LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), 'logs')
    
    # Configuration des fichiers de log
    LOG_FILE_APP = os.environ.get("LOG_FILE_APP") or "leviia-app.log"
    LOG_FILE_ERRORS = os.environ.get("LOG_FILE_ERRORS") or "leviia-errors.log"
    LOG_FILE_HTTP = os.environ.get("LOG_FILE_HTTP") or "leviia-http-errors.log"
    LOG_FILE_DEBUG = os.environ.get("LOG_FILE_DEBUG") or "leviia-debug.log"
    LOG_FILE_AUDIT = os.environ.get("LOG_FILE_AUDIT") or "leviia-audit.log"
    
    # Niveaux de log par module
    LOG_LEVEL_APP = os.environ.get("LOG_LEVEL_APP") or LOG_LEVEL
    LOG_LEVEL_ERRORS = os.environ.get("LOG_LEVEL_ERRORS") or "ERROR"
    LOG_LEVEL_HTTP = os.environ.get("LOG_LEVEL_HTTP") or "WARNING"
    LOG_LEVEL_DEBUG = os.environ.get("LOG_LEVEL_DEBUG") or "DEBUG"
    LOG_LEVEL_AUDIT = os.environ.get("LOG_LEVEL_AUDIT") or "INFO"
    
    # Configuration syslog pour la production
    SYSLOG_ENABLED = get_bool_from_env("SYSLOG_ENABLED", False)
    SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS") or "/dev/log"
    SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY") or "local0"
    
    # Filtres de log
    LOG_FILTER_SENSITIVE = get_bool_from_env("LOG_FILTER_SENSITIVE", True)
    
    # Patterns de filtrage par défaut
    default_filter_patterns = [
        r'password["\']?\s*[:=]\s*[^\s]+',
        r'secret["\']?\s*[:=]\s*[^\s]+',
        r'token["\']?\s*[:=]\s*[^\s]+',
        r'api[_-]?key["\']?\s*[:=]\s*[^\s]+',
        r'auth["\']?\s*[:=]\s*[^\s]+',
    ]
    
    # Ajouter des patterns personnalisés depuis la variable d'environnement
    custom_patterns = os.environ.get("LOG_FILTER_PATTERNS")
    if custom_patterns:
        # Séparer par virgule et ajouter aux patterns par défaut
        additional_patterns = [p.strip() for p in custom_patterns.split(",") if p.strip()]
        LOG_FILTER_PATTERNS = default_filter_patterns + additional_patterns
    else:
        LOG_FILTER_PATTERNS = default_filter_patterns
    
    # Format des logs
    LOG_FORMAT = os.environ.get("LOG_FORMAT") or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = os.environ.get("LOG_DATE_FORMAT") or "%Y-%m-%d %H:%M:%S"

    # ============================================================================
    # CONFIGURATION DE SECURITE
    # ============================================================================

    # Désactiver le cache pour les pages d'erreur
    SEND_FILE_MAX_AGE_DEFAULT = get_int_from_env("SEND_FILE_MAX_AGE_DEFAULT", 0)

    # Configuration CORS (si nécessaire)
    CORS_ENABLED = get_bool_from_env("CORS_ENABLED", False)

    # ============================================================================
    # CONFIGURATION POUR LES TESTS
    # ============================================================================

    # Configuration spécifique pour les tests
    TESTING = get_bool_from_env("FLASK_TESTING", False)
    # ============================================================================
    # CONFIGURATION DE LA SÉCURITÉ
    # ============================================================================
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = get_bool_from_env("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "200 per day, 50 per hour")
    
    # Compression Gzip
    COMPRESS_ENABLED = get_bool_from_env("COMPRESS_ENABLED", True)
    COMPRESS_MIMETYPES = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript'
    ]
    
    # CSRF Protection
    WTF_CSRF_ENABLED = get_bool_from_env("WTF_CSRF_ENABLED", True)
    WTF_CSRF_TIME_LIMIT = get_int_from_env("WTF_CSRF_TIME_LIMIT", 3600)
    
    # Headers de sécurité
    SESSION_COOKIE_SECURE = get_bool_from_env("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY = get_bool_from_env("SESSION_COOKIE_HTTPONLY", True)
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = get_bool_from_env("REMEMBER_COOKIE_SECURE", False)
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")



# ============================================================================
# CONFIGURATION DES DONNEES PAR DEFAUT
# =============================================================================

class DefaultDataConfig:
    """Configuration des données par défaut pour l'initialisation."""
    # Email de l'utilisateur admin par défaut
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL") or "admin@leviia.local"
    
    # Mot de passe de l'utilisateur admin par défaut
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD") or "admin123"
    
    # Nom du groupe par défaut
    DEFAULT_GROUP_NAME = os.environ.get("DEFAULT_GROUP_NAME") or "Defaut"
    
    # Le groupe par défaut fait partie du planning
    DEFAULT_GROUP_IN_SCHEDULE = get_bool_from_env("DEFAULT_GROUP_IN_SCHEDULE", True)
    
    # Le groupe par défaut fait partie des astreintes
    DEFAULT_GROUP_IN_ONCALL = get_bool_from_env("DEFAULT_GROUP_IN_ONCALL", True)
    
    # Types de shifts par défaut (peut être personnalisé via JSON)
    custom_shift_types = get_json_from_env("DEFAULT_SHIFT_TYPES")
    if custom_shift_types:
        DEFAULT_SHIFT_TYPES = custom_shift_types
    else:
        DEFAULT_SHIFT_TYPES = [
            {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
            {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
            {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21},
        ]
    
    # Durée de validité du token ICS en jours
    ICS_TOKEN_EXPIRY_DAYS = get_int_from_env("ICS_TOKEN_EXPIRY_DAYS", 365)


# ============================================================================
# CONFIGURATION DES NOTIFICATIONS (pour extensions futures)
# =============================================================================

class NotificationConfig:
    """Configuration des notifications (a implementer)."""
    # Activer les notifications par email
    NOTIFICATIONS_ENABLED = get_bool_from_env("NOTIFICATIONS_ENABLED", False)
    
    # Adresse email de l'expéditeur
    NOTIFICATION_FROM_EMAIL = os.environ.get("NOTIFICATION_FROM_EMAIL") or ""
    
    # Serveur SMTP
    SMTP_HOST = os.environ.get("SMTP_HOST") or ""
    SMTP_PORT = get_int_from_env("SMTP_PORT", 587)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME") or ""
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or ""
    SMTP_USE_TLS = get_bool_from_env("SMTP_USE_TLS", True)


class DevelopmentConfig(Config):
    """Configuration pour le développement."""
    DEBUG = True
    DEBUG_ERRORS = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_ECHO = True  # Afficher les requêtes SQL


class ProductionConfig(Config):
    """Configuration pour la production.
    
    En production, il est fortement recommandé d'utiliser PostgreSQL ou MariaDB
    plutôt que SQLite. La configuration se fait uniquement via la variable
    d'environnement DATABASE_URL.
    
    Exemples:
    - PostgreSQL: postgresql://user:password@localhost:5432/leviia
    - MariaDB: mariadb://user:password@localhost:3306/leviia
    - MySQL: mysql://user:password@localhost:3306/leviia
    
    SQLite reste disponible mais n'est pas recommandé pour la production
    avec plusieurs processus workers.
    """
    DEBUG = False
    DEBUG_ERRORS = False
    LOG_LEVEL = "WARNING"
    SQLALCHEMY_ECHO = False
    
    # En production, la base de données doit être configurée via DATABASE_URL
    # SQLite reste la valeur par défaut mais n'est pas recommandé pour la production
    # SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///app.db"


class TestingConfig(Config):
    """Configuration pour les tests."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LOG_LEVEL = "DEBUG"
    DEBUG_ERRORS = True
    RATE_LIMIT_ENABLED = False
    COMPRESS_ENABLED = False




# ============================================================================
# CONFIGURATION POUR LE NETTOYAGE AUTOMATIQUE
# ============================================================================

class DataCleanupConfig:
    """
    Configuration du nettoyage automatique des données.
    
    Variables d'environnement disponibles:
    - DATA_CLEANUP_ENABLED: true/false (défaut: false - désactivé par défaut)
    - DATA_CLEANUP_RETENTION: durée de rétention (ex: '1y', '6m', '30d', '365' en jours)
    - DATA_CLEANUP_BATCH_SIZE: taille des lots pour la suppression (défaut: 1000)
    - DATA_CLEANUP_SCHEDULE: planification cron (ex: '0 0 * * *' pour minuit)
    """
    
    # Désactivé par défaut pour la sécurité
    ENABLED = get_bool_from_env("DATA_CLEANUP_ENABLED", False)
    
    # Durée de rétention par défaut: 1 an
    RETENTION_DAYS = get_int_from_env("DATA_CLEANUP_RETENTION_DAYS", 365)
    
    # Taille des lots pour la suppression
    BATCH_SIZE = get_int_from_env("DATA_CLEANUP_BATCH_SIZE", 1000)
    
    # Planification par défaut: tous les jours à minuit
    SCHEDULE = os.environ.get("DATA_CLEANUP_SCHEDULE", "0 0 * * *")
    
    @classmethod
    def parse_retention(cls, retention_str):
        """Parse une chaîne de rétention (ex: '1y', '6m', '30d') en jours."""
        if not retention_str:
            return cls.RETENTION_DAYS
        retention_str = retention_str.lower().strip()
        if retention_str.endswith('y'):
            return int(retention_str[:-1]) * 365
        elif retention_str.endswith('m'):
            return int(retention_str[:-1]) * 30
        elif retention_str.endswith('d'):
            return int(retention_str[:-1])
        else:
            try:
                return int(retention_str)
            except ValueError:
                return cls.RETENTION_DAYS
    
    @classmethod
    def from_env(cls):
        """Recharge la configuration depuis les variables d'environnement."""
        cls.ENABLED = get_bool_from_env("DATA_CLEANUP_ENABLED", False)
        retention_str = os.environ.get("DATA_CLEANUP_RETENTION", f"{cls.RETENTION_DAYS}d")
        cls.RETENTION_DAYS = cls.parse_retention(retention_str)
        cls.BATCH_SIZE = get_int_from_env("DATA_CLEANUP_BATCH_SIZE", 1000)
        cls.SCHEDULE = os.environ.get("DATA_CLEANUP_SCHEDULE", "0 0 * * *")


# Charger la configuration du nettoyage
DataCleanupConfig.from_env()


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
