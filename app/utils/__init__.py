"""
Utilities module for Leviia Schedule.

This module contains utility functions and helpers organized by category.

Submodules:
- cache: Caching utilities
- export: Export utilities (ICS, etc.)
- automation: Automation utilities
- helpers: General helper functions
- logging: Logging configuration
- health: Health check endpoints
"""

from app.utils.cache import clear_cache, get_cache, init_cache
from app.utils.export import export_to_ics, generate_ics_calendar
from app.utils.health import register_health_endpoints
from app.utils.helpers import format_date, format_datetime
from app.utils.logging import configure_logging

__all__ = [
    "init_cache",
    "get_cache",
    "clear_cache",
    "export_to_ics",
    "generate_ics_calendar",
    "format_date",
    "format_datetime",
    "configure_logging",
    "register_health_endpoints",
]
