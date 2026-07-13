"""
Logger configuration for Leviia Schedule.

This module provides centralized logging configuration for the application.
It supports both console and file logging with configurable levels and formats.
"""

import logging
import os
import re
from typing import Any

from flask import Flask


class SensitiveDataFilter(logging.Filter):
    """
    Filtre de logging qui masque les données sensibles (mots de passe, tokens,
    clés API) dans les messages et arguments avant qu'ils ne soient écrits.
    """

    _PATTERN = re.compile(r"(password|token|api_key)=\S+", re.IGNORECASE)

    @classmethod
    def _mask(cls, text: str) -> str:
        return cls._PATTERN.sub(lambda m: f"{m.group(1)}=***", text)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._mask(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: self._mask(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    self._mask(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def configure_logging(
    app: Flask | None = None, level: str | None = None, format_str: str | None = None
) -> None:
    """
    Configure logging for the application.

    Args:
        app: Flask application instance (optional, for getting config)
        level: Logging level (default: from app.config or INFO)
        format_str: Log format string (default: from app.config or standard format)
    """
    # Determine log level
    if level is None:
        if app is not None:
            level = app.config.get("LOG_LEVEL", "INFO")
        else:
            level = os.environ.get("LOG_LEVEL", "INFO")

    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Determine log format
    if format_str is None:
        if app is not None:
            format_str = app.config.get(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_str)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    log_file = os.environ.get("LOG_FILE")
    if app is not None:
        log_file = app.config.get("LOG_FILE", log_file)

    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific loggers
    # Flask logger
    flask_logger = logging.getLogger("flask.app")
    flask_logger.setLevel(log_level)

    # SQLAlchemy logger (for query logging)
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if app is not None:
        sqlalchemy_level = app.config.get("SQLALCHEMY_LOG_LEVEL", "WARNING")
    else:
        sqlalchemy_level = "WARNING"
    sqlalchemy_logger.setLevel(
        getattr(logging, sqlalchemy_level.upper(), logging.WARNING)
    )

    # Werkzeug logger (for request logging)
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(log_level)

    # Dossier de logs applicatif (app/error/http/audit) - à côté du dossier logs/
    # à la racine du projet, ignoré par git (*.log). Nom distinct de log_dir
    # ci-dessus (portée de fonction partagée en Python, pas de scope de bloc)
    # pour éviter un conflit d'annotation de type avec ce premier usage.
    _app_logs_path = os.path.join(os.getcwd(), "logs")
    app_log_dir: str | None
    try:
        os.makedirs(_app_logs_path, exist_ok=True)
        app_log_dir = _app_logs_path
    except OSError:
        app_log_dir = None

    sensitive_filter = SensitiveDataFilter()

    def _reset_handlers(logger: logging.Logger) -> None:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def _file_handler(filename: str, min_level: int) -> logging.Handler | None:
        if not app_log_dir:
            return None
        handler = logging.FileHandler(os.path.join(app_log_dir, filename))
        handler.setLevel(min_level)
        handler.setFormatter(formatter)
        handler.addFilter(sensitive_filter)
        return handler

    if app is not None:
        # Logger applicatif principal : console + fichier app + fichier erreurs
        # + fichier debug (au moins 4 handlers, cf. tests/test_error_handlers.py)
        _reset_handlers(app.logger)
        app.logger.setLevel(log_level)
        app.logger.propagate = False

        app_console_handler = logging.StreamHandler()
        app_console_handler.setLevel(log_level)
        app_console_handler.setFormatter(formatter)
        app_console_handler.addFilter(sensitive_filter)
        app.logger.addHandler(app_console_handler)

        for filename, min_level in (
            ("app.log", log_level),
            ("error.log", logging.ERROR),
            ("debug.log", logging.DEBUG),
        ):
            maybe_handler: logging.Handler | None = _file_handler(filename, min_level)
            if maybe_handler is not None:
                app.logger.addHandler(maybe_handler)

    # Logger dédié aux erreurs HTTP (404, 403, ...)
    http_logger = logging.getLogger("http_errors")
    _reset_handlers(http_logger)
    http_logger.setLevel(logging.WARNING)
    http_logger.propagate = False
    http_logger.addFilter(sensitive_filter)
    http_handler = (
        _file_handler("http_errors.log", logging.WARNING) or logging.StreamHandler()
    )
    http_logger.addHandler(http_handler)

    # Logger d'audit (actions utilisateur significatives)
    audit_logger = logging.getLogger("audit")
    _reset_handlers(audit_logger)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    audit_logger.addFilter(sensitive_filter)
    audit_handler = _file_handler("audit.log", logging.INFO) or logging.StreamHandler()
    audit_logger.addHandler(audit_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name, ensuring it has at least one handler.

    Args:
        name: Name of the logger

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)
    return logger


def log_http_error(code: int, message: str) -> None:
    """
    Log une erreur HTTP sur le logger dédié 'http_errors'.

    Args:
        code: Code de statut HTTP (404, 403, 500, ...)
        message: Message décrivant l'erreur
    """
    logger = logging.getLogger("http_errors")
    logger.error(f"HTTP {code}: {message}")


def get_error_template_data(code: int, message: str) -> dict:
    """
    Construit les données de contexte pour les templates d'erreur.

    Args:
        code: Code de statut HTTP
        message: Message d'erreur

    Returns:
        Dictionnaire {'error_code': ..., 'error_message': ...}
    """
    return {"error_code": code, "error_message": message}


def log_audit_action(
    action: str,
    user: Any = None,
    path: str | None = None,
    status: str = "success",
    details: str | None = None,
) -> None:
    """
    Log une action d'audit (création/modification/suppression de ressource,
    connexion, etc.) sur le logger dédié 'audit'.

    Args:
        action: Nom de l'action (ex: 'delete_leave', 'login')
        user: Utilisateur ayant effectué l'action (objet avec un attribut .name),
              ou None pour un utilisateur anonyme
        path: Chemin de la requête concernée
        status: 'success' ou 'failure'
        details: Détails complémentaires optionnels
    """
    logger = logging.getLogger("audit")
    username = getattr(user, "name", None) or "anonyme"
    logger.info(
        f"action={action} user={username} path={path} status={status} details={details}"
    )
