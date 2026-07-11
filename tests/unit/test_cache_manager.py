"""
Tests pour app/utils/cache/cache_manager.py.

init_cache(app) tourne inconditionnellement à chaque démarrage de
l'application (app/__init__.py) - ces tests couvrent ses branches
(simple/redis/memcached/fallback sur exception), le seul chemin de ce
module réellement exercé en production.

get_cache()/clear_cache()/cache_key()/SimpleDictCache existent toujours
mais n'ont plus aucun appelant dans app/ depuis la suppression des
décorateurs cached_route/cache_result (Phase 4) - ils importaient
`cache` depuis app.utils.cache, qui n'a jamais existé comme export (import
cassé, cohérent avec le reste du code mort déjà supprimé). Signalé pour
suppression plutôt que testé à vide - voir rapport Phase 4.
"""

import pytest

from app.utils.cache import cache_manager


@pytest.fixture(autouse=True)
def reset_global_cache():
    """cache_manager._cache est un global module-level - reset entre tests."""
    cache_manager._cache = None
    yield
    cache_manager._cache = None


class TestInitCacheSimple:
    def test_default_simple_cache_falls_back_to_dict_cache(self, test_app):
        # flask_caching n'est pas installé dans cet environnement (déjà visible
        # dans les logs de test partout ailleurs) - donc même CACHE_TYPE=simple
        # tombe dans le fallback ImportError -> SimpleDictCache.
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
            # flask_caching absent -> ImportError -> fallback dict cache,
            # pas de crash.
            assert isinstance(cache_manager._cache, cache_manager.SimpleDictCache)


class TestInitCacheMemcachedFallback:
    def test_memcached_type_without_flask_caching_falls_back(self, test_app):
        with test_app.app_context():
            test_app.config["CACHE_TYPE"] = "memcached"
            cache_manager.init_cache(test_app)
            assert isinstance(cache_manager._cache, cache_manager.SimpleDictCache)


class TestSimpleDictCache:
    """Le fallback est ce qui tourne réellement dans cet environnement -
    testé directement plutôt que via get_cache() (non appelé en prod)."""

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
