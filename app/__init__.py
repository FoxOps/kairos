from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import time
import sqlite3
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import os
import traceback
import re
from datetime import datetime

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


# ============================================================================
# CONFIGURATION DU LOGGING
# ============================================================================

class SensitiveDataFilter(logging.Filter):
    """Filtre pour masquer les données sensibles dans les logs."""
    
    def __init__(self, patterns=None):
        super().__init__()
        self.patterns = patterns or [
            r'password["\']?\s*[:=]\s*[^\s]+',
            r'secret["\']?\s*[:=]\s*[^\s]+',
            r'token["\']?\s*[:=]\s*[^\s]+',
            r'api[_-]?key["\']?\s*[:=]\s*[^\s]+',
            r'auth["\']?\s*[:=]\s*[^\s]+',
        ]
    
    def filter(self, record):
        """Masque les données sensibles dans le message de log."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            message = record.msg
            for pattern in self.patterns:
                message = re.sub(pattern, lambda m: m.group(0).split('=')[0] + '=***', message, flags=re.IGNORECASE)
            record.msg = message
        
        if hasattr(record, 'args') and record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    filtered_arg = arg
                    for pattern in self.patterns:
                        filtered_arg = re.sub(pattern, lambda m: m.group(0).split('=')[0] + '=***', filtered_arg, flags=re.IGNORECASE)
                    new_args.append(filtered_arg)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        
        return True


def get_log_level(level_name):
    """Convertit un nom de niveau de log en constante logging."""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level_name.upper(), logging.INFO)


def create_rotating_file_handler(filepath, max_bytes, backup_count, level, formatter, encoding='utf-8'):
    """Crée un handler de fichier avec rotation."""
    handler = RotatingFileHandler(
        filepath,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging():
    """Configure le logging pour l'application avec rotation des fichiers et gestion avancée."""
    from config import Config
    
    # Créer le dossier de logs s'il n'existe pas
    log_dir = Config.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    
    # Récupérer les niveaux de log depuis la configuration
    log_level = get_log_level(Config.LOG_LEVEL)
    app_log_level = get_log_level(Config.LOG_LEVEL_APP)
    error_log_level = get_log_level(Config.LOG_LEVEL_ERRORS)
    http_log_level = get_log_level(Config.LOG_LEVEL_HTTP)
    debug_log_level = get_log_level(Config.LOG_LEVEL_DEBUG)
    audit_log_level = get_log_level(Config.LOG_LEVEL_AUDIT)
    
    # Format des logs
    log_format = Config.LOG_FORMAT
    date_format = Config.LOG_DATE_FORMAT
    
    # Formatter principal
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Formatter détaillé pour les erreurs (inclut la trace)
    error_formatter = logging.Formatter(
        f'{log_format}\n\n%(exc_text)s',
        datefmt=date_format
    )
    
    # Formatter pour les erreurs HTTP (avec contexte)
    http_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - IP: %(ip)s - Path: %(path)s - User: %(user)s - Error: %(message)s',
        datefmt=date_format
    )
    
    # Formatter simple pour la console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt=date_format
    )
    
    # Filtre pour les données sensibles
    sensitive_filter = SensitiveDataFilter(Config.LOG_FILTER_PATTERNS) if Config.LOG_FILTER_SENSITIVE else None
    
    # ========================================================================
    # Configuration du logger principal de l'application
    # ========================================================================
    app.logger.setLevel(app_log_level)
    
    # Handler pour les fichiers d'application (INFO et plus)
    app_file_handler = create_rotating_file_handler(
        os.path.join(log_dir, Config.LOG_FILE_APP),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.INFO,
        formatter
    )
    if sensitive_filter:
        app_file_handler.addFilter(sensitive_filter)
    app.logger.addHandler(app_file_handler)
    
    # Handler pour les erreurs (ERROR et plus)
    error_file_handler = create_rotating_file_handler(
        os.path.join(log_dir, Config.LOG_FILE_ERRORS),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.ERROR,
        error_formatter
    )
    if sensitive_filter:
        error_file_handler.addFilter(sensitive_filter)
    app.logger.addHandler(error_file_handler)
    
    # Handler pour le debug (DEBUG seulement)
    debug_file_handler = create_rotating_file_handler(
        os.path.join(log_dir, Config.LOG_FILE_DEBUG),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.DEBUG,
        formatter
    )
    if sensitive_filter:
        debug_file_handler.addFilter(sensitive_filter)
    app.logger.addHandler(debug_file_handler)
    
    # Handler pour l'audit (INFO et plus - actions utilisateur)
    audit_file_handler = create_rotating_file_handler(
        os.path.join(log_dir, Config.LOG_FILE_AUDIT),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.INFO,
        formatter
    )
    if sensitive_filter:
        audit_file_handler.addFilter(sensitive_filter)
    app.logger.addHandler(audit_file_handler)
    
    # ========================================================================
    # Handler console (pour le développement)
    # ========================================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    if sensitive_filter:
        console_handler.addFilter(sensitive_filter)
    app.logger.addHandler(console_handler)
    
    # ========================================================================
    # Logger dédié aux erreurs HTTP
    # ========================================================================
    http_error_logger = logging.getLogger('http_errors')
    http_error_logger.setLevel(http_log_level)
    http_error_logger.propagate = False  # Éviter la duplication des logs
    
    http_error_handler = create_rotating_file_handler(
        os.path.join(log_dir, Config.LOG_FILE_HTTP),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        http_log_level,
        http_formatter
    )
    if sensitive_filter:
        http_error_handler.addFilter(sensitive_filter)
    http_error_logger.addHandler(http_error_handler)
    
    # ========================================================================
    # Syslog pour la production (si activé)
    # ========================================================================
    if Config.SYSLOG_ENABLED:
        try:
            syslog_handler = SysLogHandler(address=Config.SYSLOG_ADDRESS)
            syslog_handler.setLevel(log_level)
            syslog_formatter = logging.Formatter(
                f'LeviiaSchedule - %(levelname)s - %(message)s',
                datefmt=date_format
            )
            syslog_handler.setFormatter(syslog_formatter)
            if sensitive_filter:
                syslog_handler.addFilter(sensitive_filter)
            app.logger.addHandler(syslog_handler)
            http_error_logger.addHandler(syslog_handler)
            app.logger.info("Syslog handler activé")
        except Exception as e:
            app.logger.warning(f"Impossible d'activer syslog: {str(e)}")
    
    # ========================================================================
    # Loggers spécifiques pour différents modules
    # ========================================================================
    
    # Logger pour les requêtes SQL (si SQLALCHEMY_ECHO est activé)
    if Config.SQLALCHEMY_ECHO:
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.DEBUG)
        sql_handler = create_rotating_file_handler(
            os.path.join(log_dir, 'leviia-sql.log'),
            Config.LOG_FILE_SIZE,
            Config.LOG_BACKUP_COUNT,
            logging.DEBUG,
            formatter
        )
        if sensitive_filter:
            sql_handler.addFilter(sensitive_filter)
        sql_logger.addHandler(sql_handler)
        sql_logger.propagate = False
    
    # Logger pour Flask-Login
    login_logger = logging.getLogger('flask_login')
    login_logger.setLevel(logging.INFO)
    login_handler = create_rotating_file_handler(
        os.path.join(log_dir, 'leviia-auth.log'),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.INFO,
        formatter
    )
    if sensitive_filter:
        login_handler.addFilter(sensitive_filter)
    login_logger.addHandler(login_handler)
    login_logger.propagate = False
    
    # Logger pour les tâches planifiées
    automation_logger = logging.getLogger('automation')
    automation_logger.setLevel(logging.INFO)
    automation_handler = create_rotating_file_handler(
        os.path.join(log_dir, 'leviia-automation.log'),
        Config.LOG_FILE_SIZE,
        Config.LOG_BACKUP_COUNT,
        logging.INFO,
        formatter
    )
    if sensitive_filter:
        automation_handler.addFilter(sensitive_filter)
    automation_logger.addHandler(automation_handler)
    automation_logger.propagate = False
    
    # Message de démarrage
    app.logger.info(f"Configuration du logging terminée - Niveau: {Config.LOG_LEVEL}")
    app.logger.info(f"Dossier des logs: {log_dir}")
    app.logger.info(f"Filtrage des données sensibles: {'activé' if Config.LOG_FILTER_SENSITIVE else 'désactivé'}")
    
    return http_error_logger


# Initialiser le logging
http_error_logger = setup_logging()


# ============================================================================
# GESTION DES ERREURS DE BASE DE DONNÉES VERROUILLÉE POUR SQLITE
# ============================================================================

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


# ============================================================================
# FONCTIONS UTILITAIRES POUR LE LOGGING DES ERREURS
# ============================================================================

def log_http_error(error_code, error_message=None, exc_info=None):
    """Log une erreur HTTP avec des informations contextuelles."""
    ip = request.remote_addr if request else 'unknown'
    path = request.path if request else 'unknown'
    user = current_user.name if hasattr(current_user, 'name') and current_user.is_authenticated else 'anonymous'
    
    error_msg = f"HTTP {error_code} - {error_message or error_code}"
    
    # Ajouter la trace complète si disponible
    if exc_info:
        error_msg += f"\n{traceback.format_exception(*exc_info)}"
    
    # Logger dans le logger dédié aux erreurs HTTP
    http_error_logger.error(
        error_msg,
        extra={'ip': ip, 'path': path, 'user': user}
    )
    
    # Logger aussi dans le logger principal selon le niveau
    if error_code >= 500:
        app.logger.error(f"Erreur serveur {error_code}: {error_message or error_code} - Path: {path}")
    elif error_code >= 400:
        app.logger.warning(f"Erreur client {error_code}: {error_message or error_code} - Path: {path}")


def log_audit_action(action, user=None, path=None, status="success", details=None):
    """Log une action utilisateur pour l'audit."""
    audit_logger = logging.getLogger('audit')
    user_name = user.name if user and hasattr(user, 'name') else 'anonymous'
    
    message = f"AUDIT: {action} - User: {user_name} - Status: {status}"
    if path:
        message += f" - Path: {path}"
    if details:
        message += f" - Details: {details}"
    
    if status == "success":
        audit_logger.info(message)
    elif status == "failure":
        audit_logger.warning(message)
    else:
        audit_logger.info(message)


def get_logger(name):
    """Obtient un logger spécifique avec la configuration par défaut."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Ajouter un handler par défaut si aucun n'existe
        from config import Config
        log_dir = Config.LOG_DIR
        handler = create_rotating_file_handler(
            os.path.join(log_dir, f'leviia-{name}.log'),
            Config.LOG_FILE_SIZE,
            Config.LOG_BACKUP_COUNT,
            logging.INFO,
            logging.Formatter(Config.LOG_FORMAT, datefmt=Config.LOG_DATE_FORMAT)
        )
        if Config.LOG_FILTER_SENSITIVE:
            handler.addFilter(SensitiveDataFilter(Config.LOG_FILTER_PATTERNS))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============================================================================
# GESTIONNAIRES D'ERREURS PERSONNALISÉS
# ============================================================================

@app.errorhandler(400)
def bad_request_error(error):
    """Page d'erreur 400 personnalisée - Requête incorrecte."""
    log_http_error(400, str(error))
    return render_template("400.html", **get_error_template_data(400, str(error))), 400


@app.errorhandler(401)
def unauthorized_error(error):
    """Page d'erreur 401 personnalisée - Non autorisé."""
    log_http_error(401, str(error))
    return render_template("401.html", **get_error_template_data(401, "Accès non autorisé")), 401


@app.errorhandler(403)
def forbidden_error(error):
    """Page d'erreur 403 personnalisée - Accès interdit."""
    log_http_error(403, str(error))
    return render_template("403.html", **get_error_template_data(403, str(error))), 403


@app.errorhandler(404)
def not_found_error(error):
    """Page d'erreur 404 personnalisée - Page non trouvée."""
    log_http_error(404, str(error))
    return render_template("404.html", **get_error_template_data(404, str(error))), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    """Page d'erreur 405 personnalisée - Méthode non autorisée."""
    log_http_error(405, str(error))
    return render_template("405.html", **get_error_template_data(405, str(error))), 405


@app.errorhandler(500)
def internal_server_error(error):
    """Page d'erreur 500 personnalisée - Erreur interne du serveur."""
    # Obtenir la trace complète de l'erreur
    exc_type, exc_value, exc_traceback = None, None, None
    if hasattr(error, 'exc_info') and error.exc_info:
        exc_type, exc_value, exc_traceback = error.exc_info
    elif hasattr(error, 'original_exception'):
        exc_type = type(error.original_exception)
        exc_value = error.original_exception
        exc_traceback = error.original_exception.__traceback__
    
    # Log l'erreur complète
    error_message = str(error) if str(error) else "Erreur interne du serveur"
    log_http_error(500, error_message, (exc_type, exc_value, exc_traceback) if exc_type else None)
    
    # Vérifier si la requête est AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur interne du serveur s\'est produite. Veuillez réessayer plus tard.',
            'code': 500
        }), 500
    
    return render_template(
        "500.html", 
        **get_error_template_data(500, "Une erreur interne du serveur s'est produite")
    ), 500


@app.errorhandler(502)
def bad_gateway_error(error):
    """Page d'erreur 502 personnalisée - Mauvaise passerelle."""
    log_http_error(502, str(error))
    return render_template(
        "502.html", 
        **get_error_template_data(502, "Le serveur a reçu une réponse invalide")
    ), 502


@app.errorhandler(503)
def service_unavailable_error(error):
    """Page d'erreur 503 personnalisée - Service indisponible."""
    retry_after = None
    if hasattr(error, 'retry_after'):
        retry_after = error.retry_after
    
    log_http_error(503, str(error))
    return render_template(
        "503.html", 
        retry_after=retry_after,
        **get_error_template_data(503, "Service temporairement indisponible")
    ), 503


@app.errorhandler(504)
def gateway_timeout_error(error):
    """Page d'erreur 504 personnalisée - Délai d'attente de la passerelle."""
    log_http_error(504, str(error))
    return render_template(
        "504.html", 
        **get_error_template_data(504, "Le serveur n'a pas répondu à temps")
    ), 504


# ============================================================================
# GESTIONNAIRES D'EXCEPTIONS COURANTES
# ============================================================================

@app.errorhandler(Exception)
def handle_exception(error):
    """Gestionnaire d'exceptions générique pour capturer toutes les erreurs non gérées."""
    # Ne pas interférer avec les erreurs HTTP déjà gérées
    if hasattr(error, 'code') and error.code in [400, 401, 403, 404, 405, 500, 502, 503, 504]:
        return error
    
    # Log l'erreur
    exc_type, exc_value, exc_traceback = type(error), error, error.__traceback__
    log_http_error(500, f"Unhandled exception: {str(error)}", (exc_type, exc_value, exc_traceback))
    
    # Vérifier si la requête est AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur inattendue s\'est produite. Veuillez réessayer plus tard.',
            'code': 500
        }), 500
    
    return render_template(
        "500.html", 
        **get_error_template_data(500, "Une erreur inattendue s'est produite")
    ), 500


@app.errorhandler(sqlite3.OperationalError)
def handle_database_error(error):
    """Gestionnaire d'erreurs spécifiques à la base de données."""
    error_message = str(error)
    
    # Log l'erreur
    log_http_error(500, f"Database error: {error_message}")
    
    # Vérifier si c'est une erreur de verrouillage
    if "locked" in error_message.lower():
        error_message = "La base de données est temporairement verrouillée. Veuillez réessayer dans quelques instants."
    else:
        error_message = "Une erreur de base de données s'est produite. Veuillez réessayer plus tard."
    
    # Vérifier si la requête est AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Database Error',
            'message': error_message,
            'code': 500
        }), 500
    
    return render_template(
        "500.html", 
        **get_error_template_data(500, error_message)
    ), 500


@app.errorhandler(ValueError)
def handle_value_error(error):
    """Gestionnaire d'erreurs de validation."""
    log_http_error(400, f"Validation error: {str(error)}")
    
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Validation Error',
            'message': str(error),
            'code': 400
        }), 400
    
    return render_template(
        "400.html", 
        **get_error_template_data(400, str(error))
    ), 400


@app.errorhandler(TypeError)
def handle_type_error(error):
    """Gestionnaire d'erreurs de type."""
    log_http_error(400, f"Type error: {str(error)}")
    
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Type Error',
            'message': 'Une erreur de type s\'est produite. Veuillez vérifier vos données.',
            'code': 400
        }), 400
    
    return render_template(
        "400.html", 
        **get_error_template_data(400, "Une erreur de type s'est produite")
    ), 400


# ============================================================================
# IMPORT DES MODÈLES POUR ÉVITER LES PROBLÈMES DE CIRCULAR IMPORT
# ============================================================================

# Import tardif pour éviter les problèmes de circular import
from flask_login import current_user


def get_error_template_data(error_code, error_message=None):
    """Retourne les données pour le rendu des templates d'erreur."""
    return {
        'error_code': error_code,
        'error_message': error_message,
        'current_user': current_user
    }


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    return app