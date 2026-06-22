from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import time
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import os
import traceback
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

def setup_logging():
    """Configure le logging pour l'application avec rotation des fichiers."""
    # Créer le dossier de logs s'il n'existe pas
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configuration du logger principal
    app.logger.setLevel(logging.INFO)
    
    # Handler pour les fichiers (rotation)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'leviia-app.log'),
        maxBytes=1024 * 1024 * 5,  # 5 Mo
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    app.logger.addHandler(file_handler)
    
    # Handler pour les erreurs
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'leviia-errors.log'),
        maxBytes=1024 * 1024 * 5,  # 5 Mo
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n\n%(exc_text)s'
    )
    error_handler.setFormatter(error_formatter)
    app.logger.addHandler(error_handler)
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    app.logger.addHandler(console_handler)
    
    # Logger dédié aux erreurs HTTP
    http_error_logger = logging.getLogger('http_errors')
    http_error_logger.setLevel(logging.WARNING)
    http_error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'leviia-http-errors.log'),
        maxBytes=1024 * 1024 * 5,
        backupCount=10,
        encoding='utf-8'
    )
    http_error_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - IP: %(ip)s - Path: %(path)s - User: %(user)s - Error: %(message)s'
    )
    http_error_handler.setFormatter(http_error_formatter)
    http_error_logger.addHandler(http_error_handler)
    
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
    
    http_error_logger.error(
        error_msg,
        extra={'ip': ip, 'path': path, 'user': user}
    )


def get_error_template_data(error_code, error_message=None):
    """Retourne les données pour le rendu des templates d'erreur."""
    return {
        'error_code': error_code,
        'error_message': error_message,
        'current_user': current_user
    }


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


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    return app
