"""
Tests for app/utils/cache/cache_manager.py.

init_cache(app) runs unconditionally on every app startup
(app/__init__.py) - these tests cover its branches
(simple/redis/memcached/fallback on exception), the only path in this
module actually exercised in production.

get_cache()/clear_cache()/cache_key() have been removed: they had no
callers left once the cached_route/cache_result decorators were
removed as dead code, and those decorators already imported `cache`
from app.utils.cache in a broken way (it was never exported).
SimpleDictCache remains the only path actually exercised in production
(flask_caching isn't installed in this environment) - tested directly
here.
"""

import pytest

from app.utils.cache import cache_manager


@pytest.fixture(autouse=True)
def reset_global_cache():
    """cache_manager._cache is a module-level global - reset between tests."""
    cache_manager._cache = None
    yield
    cache_manager._cache = None


class TestInitCacheSimple:
    def test_default_simple_cache_falls_back_to_dict_cache(self, test_app):
        # flask_caching isn't installed in this environment (already visible
        # in the test logs elsewhere) - so even CACHE_TYPE=simple falls
        # into the ImportError -> SimpleDictCache fallback.
        with test_app.app_context():
            test_app.config["CACHE_TYPE"] = "simple"
            cache_manager.init_cache(test_app)
            assert isinstance(cache_manager._cache, cache_manager.SimpleDictCache)

    def test_cache_timeout_applied(self, test_app):
        with test_app.app_context():
            test_app.config["CACHE_TYPE"] = "simple"
            test_app.config["CACHE_DEFAULT_TIMEOUT"] = 42
            cache_manager.init_cache(test_app)
            assert cache_manager._cache.timeout == 42


class TestInitCacheRedisFallback:
    def test_redis_type_without_flask_caching_falls_back(self, test_app):
        with test_app.app_context():
            test_app.config["CACHE_TYPE"] = "redis"
            cache_manager.init_cache(test_app)
            # flask_caching missing -> ImportError -> falls back to the
            # dict cache, no crash.
            assert isinstance(cache_manager._cache, cache_manager.SimpleDictCache)


class TestInitCacheMemcachedFallback:
    def test_memcached_type_without_flask_caching_falls_back(self, test_app):
        with test_app.app_context():
            test_app.config["CACHE_TYPE"] = "memcached"
            cache_manager.init_cache(test_app)
            assert isinstance(cache_manager._cache, cache_manager.SimpleDictCache)


class TestSimpleDictCache:
    """The fallback is what actually runs in this environment - tested
    directly rather than via get_cache() (not called in production)."""

    def test_set_and_get(self):
        cache = cache_manager.SimpleDictCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key_returns_none(self):
        cache = cache_manager.SimpleDictCache()
        assert cache.get("missing") is None

    def test_get_expired_key_returns_none(self):
        cache = cache_manager.SimpleDictCache()
        cache.set("key1", "value1", timeout=-1)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = cache_manager.SimpleDictCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_missing_key_no_error(self):
        cache = cache_manager.SimpleDictCache()
        cache.delete("missing")  # ne doit pas lever

    def test_clear(self):
        cache = cache_manager.SimpleDictCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_has(self):
        cache = cache_manager.SimpleDictCache()
        cache.set("key1", "value1")
        assert cache.has("key1") is True
        assert cache.has("missing") is False
