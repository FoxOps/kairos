"""
Logger configuration for Kairos.

This module provides centralized logging configuration for the application.
It supports both console and file logging with configurable levels and formats.
"""

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from typing import Any

from flask import Flask

# 10 MiB per file, 5 rotated backups kept (app.log, app.log.1, ... app.log.5)
# - applies to every app/error/debug/http_errors/audit log file below.
# Overridable via env for deployments with different retention needs.
# Fixes unbounded growth observed in dev (app.log/debug.log reaching ~24 MB
# each with no rotation at all before this).
_LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))
_LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that masks sensitive data (passwords, tokens, API
    keys) in messages and arguments before they get written.
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

        file_handler = RotatingFileHandler(
            log_file, maxBytes=_LOG_MAX_BYTES, backupCount=_LOG_BACKUP_COUNT
        )
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

    # App log directory (app/error/http/audit) - next to the logs/
    # directory at the project root, ignored by git (*.log). Named
    # differently from log_dir above (Python functions share scope
    # across blocks, there's no block-level scoping) to avoid a type
    # annotation conflict with that earlier usage.
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
        handler = RotatingFileHandler(
            os.path.join(app_log_dir, filename),
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
        )
        handler.setLevel(min_level)
        handler.setFormatter(formatter)
        handler.addFilter(sensitive_filter)
        return handler

    if app is not None:
        # Main application logger: console + app file + error file +
        # debug file (at least 4 handlers, see tests/test_error_handlers.py)
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

    # Logger dedicated to HTTP errors (404, 403, ...)
    http_logger = logging.getLogger("http_errors")
    _reset_handlers(http_logger)
    http_logger.setLevel(logging.WARNING)
    http_logger.propagate = False
    http_logger.addFilter(sensitive_filter)
    http_handler = (
        _file_handler("http_errors.log", logging.WARNING) or logging.StreamHandler()
    )
    http_logger.addHandler(http_handler)

    # Audit logger (significant user actions)
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
    Log an HTTP error on the dedicated 'http_errors' logger.

    Args:
        code: HTTP status code (404, 403, 500, ...)
        message: Message describing the error
    """
    logger = logging.getLogger("http_errors")
    logger.error(f"HTTP {code}: {message}")


def get_error_template_data(code: int, message: str) -> dict:
    """
    Build the context data for error templates.

    Args:
        code: HTTP status code
        message: Error message

    Returns:
        Dictionary {'error_code': ..., 'error_message': ...}
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
    Log an audit action (resource creation/update/deletion, login, etc.)
    on the dedicated 'audit' logger.

    Args:
        action: Name of the action (e.g. 'delete_leave', 'login')
        user: User who performed the action (object with a .name
              attribute), or None for an anonymous user
        path: Path of the relevant request
        status: 'success' or 'failure'
        details: Optional additional details
    """
    logger = logging.getLogger("audit")
    username = getattr(user, "name", None) or "anonymous"
    logger.info(
        f"action={action} user={username} path={path} status={status} details={details}"
    )
