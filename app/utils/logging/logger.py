"""
Logger configuration for Leviia Schedule.

This module provides centralized logging configuration for the application.
It supports both console and file logging with configurable levels and formats.
"""

import logging
import os
from typing import Optional
from flask import Flask


def configure_logging(app: Optional[Flask] = None, level: Optional[str] = None, 
                      format_str: Optional[str] = None) -> None:
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
            level = app.config.get('LOG_LEVEL', 'INFO')
        else:
            level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Determine log format
    if format_str is None:
        if app is not None:
            format_str = app.config.get('LOG_FORMAT', 
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        else:
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
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
    log_file = os.environ.get('LOG_FILE')
    if app is not None:
        log_file = app.config.get('LOG_FILE', log_file)
    
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
    flask_logger = logging.getLogger('flask.app')
    flask_logger.setLevel(log_level)
    
    # SQLAlchemy logger (for query logging)
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    if app is not None:
        sqlalchemy_level = app.config.get('SQLALCHEMY_LOG_LEVEL', 'WARNING')
    else:
        sqlalchemy_level = 'WARNING'
    sqlalchemy_logger.setLevel(getattr(logging, sqlalchemy_level.upper(), logging.WARNING))
    
    # Werkzeug logger (for request logging)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
