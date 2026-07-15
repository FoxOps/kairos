"""
Cache configuration for Leviia Schedule.

This module provides configuration for the cache system.
"""


class CacheConfig:
    """
    Cache configuration.

    Can be configured via environment variables or directly.

    Available environment variables:
    - CACHE_TYPE: 'simple' (default), 'redis', 'memcached'
    - CACHE_ENABLED: true/false (default: true)
    - CACHE_DEFAULT_TIMEOUT: duration in seconds (default: 300)
    - CACHE_MAX_ENTRIES: maximum number of entries (default: 1000)
    - CACHE_THRESHOLD: cleanup threshold (default: 0.75)
    - CACHE_KEY_PREFIX: prefix for keys (default: 'leviia:')
    - CACHE_REDIS_URL: Redis URL (e.g. 'redis://localhost:6379/0')
    - CACHE_REDIS_PASSWORD: Redis password
    - CACHE_REDIS_DB: Redis database number (default: 0)
    """

    # Enable/disable the cache
    CACHE_ENABLED = False

    # Cache type: 'simple', 'redis', 'memcached'
    CACHE_TYPE = "simple"

    # Default configuration for SimpleCache
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_MAX_ENTRIES = 1000  # Maximum number of in-memory entries
    CACHE_THRESHOLD = 0.75  # Threshold for automatic cleanup

    # Redis configuration
    CACHE_REDIS_URL = None  # 'redis://localhost:6379/0'
    CACHE_REDIS_PASSWORD = None
    CACHE_REDIS_DB = 0
    CACHE_REDIS_SOCKET_TIMEOUT = 5
    CACHE_REDIS_SOCKET_CONNECT_TIMEOUT = 5

    # Memcached configuration
    CACHE_MEMCACHED_SERVERS: list[tuple[str, int]] = []  # [('localhost', 11211)]
    CACHE_MEMCACHED_USERNAME = None
    CACHE_MEMCACHED_PASSWORD = None

    # Prefix for all cache keys
    CACHE_KEY_PREFIX = "leviia:"

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables."""
        import os

        from app.utils.helpers import get_bool, get_int

        cls.CACHE_ENABLED = get_bool("CACHE_ENABLED", cls.CACHE_ENABLED)
        cls.CACHE_TYPE = os.environ.get("CACHE_TYPE", cls.CACHE_TYPE)
        cls.CACHE_DEFAULT_TIMEOUT = get_int(
            "CACHE_DEFAULT_TIMEOUT", cls.CACHE_DEFAULT_TIMEOUT
        )
        cls.CACHE_MAX_ENTRIES = get_int("CACHE_MAX_ENTRIES", cls.CACHE_MAX_ENTRIES)
        cls.CACHE_THRESHOLD = float(
            os.environ.get("CACHE_THRESHOLD", cls.CACHE_THRESHOLD)
        )
        cls.CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", cls.CACHE_KEY_PREFIX)
        cls.CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", cls.CACHE_REDIS_URL)
        cls.CACHE_REDIS_PASSWORD = os.environ.get(
            "CACHE_REDIS_PASSWORD", cls.CACHE_REDIS_PASSWORD
        )
        cls.CACHE_REDIS_DB = get_int("CACHE_REDIS_DB", cls.CACHE_REDIS_DB)

        # Memcached configuration
        memcached_servers = os.environ.get("CACHE_MEMCACHED_SERVERS", "")
        if memcached_servers:
            cls.CACHE_MEMCACHED_SERVERS = [
                s.strip() for s in memcached_servers.split(",")
            ]
        cls.CACHE_MEMCACHED_USERNAME = os.environ.get(
            "CACHE_MEMCACHED_USERNAME", cls.CACHE_MEMCACHED_USERNAME
        )
        cls.CACHE_MEMCACHED_PASSWORD = os.environ.get(
            "CACHE_MEMCACHED_PASSWORD", cls.CACHE_MEMCACHED_PASSWORD
        )


# Load configuration from the environment
CacheConfig.from_env()
