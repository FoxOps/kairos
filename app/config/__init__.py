"""
Configuration module for Leviia Schedule.

Config is the only class create_app() actually loads in practice (default
when no config_object is passed - see app/__init__.py). TestingConfig is
used explicitly by the test suite. ProductionConfig/DevelopmentConfig were
removed as dead code: nothing in this repo ever passed them to create_app()
(FLASK_ENV only selects gunicorn vs the Flask dev server in
docker/entrypoint.sh, it never selects a config class) - see CLAUDE.md
"Configuration: two parallel systems".
"""

from app.config.base import Config
from app.config.testing import TestingConfig

__all__ = ["Config", "TestingConfig"]
