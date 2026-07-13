"""
Cache manager for Leviia Schedule.

This module provides caching functionality for the application.
It supports multiple cache backends: SimpleCache, Redis, and Memcached.

Note: This implementation uses Flask-Caching compatible backends.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from flask import Flask

logger = logging.getLogger(__name__)

# Global cache instance
_cache = None


def init_cache(app: Flask) -> None:
    """
    Initialize the cache for the Flask application.

    Args:
        app: Flask application instance
    """
    global _cache

    cache_type = app.config.get("CACHE_TYPE", "simple")
    cache_timeout = app.config.get("CACHE_DEFAULT_TIMEOUT", 300)

    try:
        if cache_type == "redis":
            # Use Flask-Caching's RedisCache
            from flask_caching.backends import RedisCache

            cache_url = app.config.get("CACHE_REDIS_URL", "redis://localhost:6379/0")
            _cache = RedisCache(app, config={"CACHE_REDIS_URL": cache_url})
            logger.info(f"Initialized Redis cache with URL: {cache_url}")
        elif cache_type == "memcached":
            # Use Flask-Caching's MemcachedCache
            from flask_caching.backends import MemcachedCache

            cache_servers = app.config.get(
                "CACHE_MEMCACHED_SERVERS", ["localhost:11211"]
            )
            _cache = MemcachedCache(app, servers=cache_servers)
            logger.info(f"Initialized Memcached cache with servers: {cache_servers}")
        else:
            # Default to Flask-Caching's SimpleCache
            from flask_caching.backends import SimpleCache

            _cache = SimpleCache(app)
            logger.info("Initialized SimpleCache (in-memory)")

        # Set default timeout
        _cache.timeout = cache_timeout
        logger.info(f"Cache timeout set to: {cache_timeout} seconds")

    except ImportError:
        # Fallback to a simple dictionary-based cache
        logger.warning("Flask-Caching not available, using simple dictionary cache")
        _cache = SimpleDictCache()
        _cache.timeout = cache_timeout
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Fallback to simple dictionary cache
        _cache = SimpleDictCache()
        _cache.timeout = cache_timeout
        logger.warning("Falling back to simple dictionary cache")


def get_cache():
    """
    Get the cache instance.

    Returns:
        The configured cache instance

    Raises:
        RuntimeError: If cache is not initialized
    """
    global _cache
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call init_cache(app) first.")
    return _cache


def clear_cache() -> None:
    """Clear all cached data."""
    global _cache
    if _cache is not None:
        _cache.clear()
        logger.info("Cache cleared")


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from the provided arguments.

    Args:
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key

    Returns:
        A string cache key
    """
    key_parts = []

    for arg in args:
        if isinstance(arg, (list, tuple)):
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        if isinstance(value, (list, tuple)):
            key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
        else:
            key_parts.append(f"{key}={value}")

    return ":".join(key_parts)


class SimpleDictCache:
    """
    Simple dictionary-based cache for fallback purposes.

    This is a minimal cache implementation used when Flask-Caching
    is not available.
    """

    def __init__(self):
        self._cache = {}
        self.timeout = 300

    def set(self, key: str, value: Any, timeout: int | None = None) -> None:
        """Set a value in the cache."""
        self._cache[key] = {
            "value": value,
            "expires": datetime.utcnow() + timedelta(seconds=timeout or self.timeout),
        }

    def get(self, key: str) -> Any:
        """Get a value from the cache."""
        item = self._cache.get(key)
        if item is None:
            return None

        if datetime.utcnow() > item["expires"]:
            del self._cache[key]
            return None

        return item["value"]

    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self._cache
