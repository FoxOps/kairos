"""
Cache utilities for Leviia Schedule.

This module provides caching functionality for the application.
"""

from app.utils.cache.cache_manager import init_cache
from app.utils.cache.config import CacheConfig

__all__ = ["init_cache", "CacheConfig"]
