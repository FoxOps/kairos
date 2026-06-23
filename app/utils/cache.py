"""
Module de cache pour Leviia Schedule.

Ce module fournit un système de cache flexible et configurable pour améliorer
les performances de l'application. Il supporte plusieurs backends :
- SimpleCache (en mémoire, par défaut)
- Redis (recommandé pour la production)
- Memcached

Utilisation :
    from app.utils.cache import cache, CacheConfig
    
    # Décorer une route pour le cache
    @cache.cached(timeout=60, key_prefix='my_route')
    def my_route():
        return expensive_operation()
    
    # Utiliser le cache manuellement
    cache.set('my_key', 'my_value', timeout=60)
    value = cache.get('my_key')
    
    # Invalider le cache
    cache.delete('my_key')
    cache.clear()
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union
from flask import Flask, request, current_app
import logging

# Logger pour le cache
cache_logger = logging.getLogger('cache')


# ============================================================================
# CONFIGURATION DU CACHE
# ============================================================================

class CacheConfig:
    """
    Configuration du cache.
    
    Peut être configurée via variables d'environnement ou directement.
    """
    
    # Type de cache : 'simple', 'redis', 'memcached'
    CACHE_TYPE = 'simple'
    
    # Configuration par défaut pour SimpleCache
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_MAX_ENTRIES = 1000  # Nombre maximal d'entrées en mémoire
    CACHE_THRESHOLD = 0.75  # Seuil pour le nettoyage automatique
    
    # Configuration pour Redis
    CACHE_REDIS_URL = None  # 'redis://localhost:6379/0'
    CACHE_REDIS_PASSWORD = None
    CACHE_REDIS_DB = 0
    CACHE_REDIS_SOCKET_TIMEOUT = 5
    CACHE_REDIS_SOCKET_CONNECT_TIMEOUT = 5
    
    # Configuration pour Memcached
    CACHE_MEMCACHED_SERVERS = []  # [('localhost', 11211)]
    CACHE_MEMCACHED_USERNAME = None
    CACHE_MEMCACHED_PASSWORD = None
    
    # Préfixe pour toutes les clés de cache
    CACHE_KEY_PREFIX = 'leviia:'
    
    # Activer/désactiver le cache (utile pour le développement)
    CACHE_ENABLED = True
    
    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement."""
        import os
        
        def get_bool(env_var, default=False):
            value = os.environ.get(env_var, '').lower()
            return value in ('true', '1', 'yes', 'y', 'on') if value else default
        
        def get_int(env_var, default=0):
            value = os.environ.get(env_var, '')
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        cls.CACHE_TYPE = os.environ.get('CACHE_TYPE', cls.CACHE_TYPE)
        cls.CACHE_DEFAULT_TIMEOUT = get_int('CACHE_DEFAULT_TIMEOUT', cls.CACHE_DEFAULT_TIMEOUT)
        cls.CACHE_MAX_ENTRIES = get_int('CACHE_MAX_ENTRIES', cls.CACHE_MAX_ENTRIES)
        cls.CACHE_THRESHOLD = float(os.environ.get('CACHE_THRESHOLD', str(cls.CACHE_THRESHOLD)))
        
        cls.CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', cls.CACHE_REDIS_URL)
        cls.CACHE_REDIS_PASSWORD = os.environ.get('CACHE_REDIS_PASSWORD', cls.CACHE_REDIS_PASSWORD)
        cls.CACHE_REDIS_DB = get_int('CACHE_REDIS_DB', cls.CACHE_REDIS_DB)
        
        cls.CACHE_MEMCACHED_SERVERS = json.loads(
            os.environ.get('CACHE_MEMCACHED_SERVERS', json.dumps(cls.CACHE_MEMCACHED_SERVERS))
        )
        cls.CACHE_MEMCACHED_USERNAME = os.environ.get('CACHE_MEMCACHED_USERNAME', cls.CACHE_MEMCACHED_USERNAME)
        cls.CACHE_MEMCACHED_PASSWORD = os.environ.get('CACHE_MEMCACHED_PASSWORD', cls.CACHE_MEMCACHED_PASSWORD)
        
        cls.CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', cls.CACHE_KEY_PREFIX)
        cls.CACHE_ENABLED = get_bool('CACHE_ENABLED', cls.CACHE_ENABLED)


# Charger la configuration depuis l'environnement
CacheConfig.from_env()


# ============================================================================
# BACKENDS DE CACHE
# ============================================================================

class BaseCache:
    """Classe de base pour les backends de cache."""
    
    def __init__(self, default_timeout: int = CacheConfig.CACHE_DEFAULT_TIMEOUT):
        self.default_timeout = default_timeout
        self._prefix = CacheConfig.CACHE_KEY_PREFIX
    
    def _make_key(self, key: str) -> str:
        """Crée une clé de cache avec préfixe."""
        return f"{self._prefix}{key}"
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache."""
        raise NotImplementedError
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache."""
        raise NotImplementedError
    
    def clear(self) -> bool:
        """Efface tout le cache."""
        raise NotImplementedError
    
    def has(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache."""
        return self.get(key) is not None
    
    def get_many(self, *keys) -> dict:
        """Récupère plusieurs valeurs du cache."""
        return {key: self.get(key) for key in keys}
    
    def set_many(self, mapping: dict, timeout: Optional[int] = None) -> bool:
        """Stocke plusieurs valeurs dans le cache."""
        success = True
        for key, value in mapping.items():
            if not self.set(key, value, timeout):
                success = False
        return success
    
    def delete_many(self, *keys) -> bool:
        """Supprime plusieurs entrées du cache."""
        success = True
        for key in keys:
            if not self.delete(key):
                success = False
        return success


class SimpleCache(BaseCache):
    """
    Backend de cache simple en mémoire.
    
    Utilise un dictionnaire Python avec gestion du TTL (Time To Live).
    Idéal pour le développement et les petites applications.
    """
    
    def __init__(self, default_timeout: int = CacheConfig.CACHE_DEFAULT_TIMEOUT,
                 max_entries: int = CacheConfig.CACHE_MAX_ENTRIES,
                 threshold: float = CacheConfig.CACHE_THRESHOLD):
        super().__init__(default_timeout)
        self._cache = {}
        self._max_entries = max_entries
        self._threshold = threshold
        self._hits = 0
        self._misses = 0
    
    def _cleanup(self):
        """Nettoie les entrées expirées et gère la taille maximale."""
        now = time.time()
        
        # Supprimer les entrées expirées
        expired_keys = [
            key for key, (value, expiry) in self._cache.items()
            if expiry is not None and expiry <= now
        ]
        for key in expired_keys:
            del self._cache[key]
        
        # Vérifier si on dépasse le seuil
        if len(self._cache) >= self._max_entries * self._threshold:
            # Supprimer les entrées les plus anciennes (FIFO)
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1] or 0)
            keys_to_remove = sorted_keys[:int(self._max_entries * (1 - self._threshold))]
            for key in keys_to_remove:
                del self._cache[key]
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache."""
        if not CacheConfig.CACHE_ENABLED:
            return None
        
        full_key = self._make_key(key)
        
        if full_key not in self._cache:
            self._misses += 1
            cache_logger.debug(f"Cache miss: {full_key}")
            return None
        
        value, expiry = self._cache[full_key]
        
        # Vérifier si l'entrée a expiré
        if expiry is not None and expiry <= time.time():
            del self._cache[full_key]
            self._misses += 1
            cache_logger.debug(f"Cache expired: {full_key}")
            return None
        
        self._hits += 1
        cache_logger.debug(f"Cache hit: {full_key}")
        return value
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        if not CacheConfig.CACHE_ENABLED:
            return False
        
        full_key = self._make_key(key)
        expiry = None
        
        if timeout is not None:
            expiry = time.time() + timeout
        elif self.default_timeout > 0:
            expiry = time.time() + self.default_timeout
        
        # Nettoyer avant d'ajouter si nécessaire
        if len(self._cache) >= self._max_entries:
            self._cleanup()
        
        self._cache[full_key] = (value, expiry)
        cache_logger.debug(f"Cache set: {full_key} (expires: {expiry})")
        return True
    
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache."""
        full_key = self._make_key(key)
        if full_key in self._cache:
            del self._cache[full_key]
            cache_logger.debug(f"Cache deleted: {full_key}")
            return True
        return False
    
    def clear(self) -> bool:
        """Efface tout le cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        cache_logger.info("Cache cleared")
        return True
    
    def stats(self) -> dict:
        """Retourne les statistiques du cache."""
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
            'size': len(self._cache),
            'max_entries': self._max_entries
        }


class RedisCache(BaseCache):
    """
    Backend de cache Redis.
    
    Recommandé pour la production avec plusieurs workers.
    """
    
    def __init__(self, default_timeout: int = CacheConfig.CACHE_DEFAULT_TIMEOUT):
        super().__init__(default_timeout)
        self._redis = None
        self._connected = False
    
    def _get_redis(self):
        """Obtient ou crée la connexion Redis."""
        if self._redis is None:
            try:
                import redis
                
                url = CacheConfig.CACHE_REDIS_URL or 'redis://localhost:6379/0'
                password = CacheConfig.CACHE_REDIS_PASSWORD
                db = CacheConfig.CACHE_REDIS_DB
                socket_timeout = CacheConfig.CACHE_REDIS_SOCKET_TIMEOUT
                socket_connect_timeout = CacheConfig.CACHE_REDIS_SOCKET_CONNECT_TIMEOUT
                
                self._redis = redis.Redis.from_url(
                    url,
                    password=password,
                    db=db,
                    socket_timeout=socket_timeout,
                    socket_connect_timeout=socket_connect_timeout,
                    decode_responses=True
                )
                
                # Tester la connexion
                self._redis.ping()
                self._connected = True
                cache_logger.info("Connected to Redis")
                
            except ImportError:
                cache_logger.warning("Redis package not installed. Falling back to SimpleCache.")
                self._redis = None
                self._connected = False
            except Exception as e:
                cache_logger.error(f"Failed to connect to Redis: {e}")
                self._redis = None
                self._connected = False
        
        return self._redis
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache."""
        if not CacheConfig.CACHE_ENABLED or not self._connected:
            return None
        
        redis = self._get_redis()
        if redis is None:
            return None
        
        full_key = self._make_key(key)
        
        try:
            value = redis.get(full_key)
            if value is None:
                cache_logger.debug(f"Redis cache miss: {full_key}")
                return None
            
            cache_logger.debug(f"Redis cache hit: {full_key}")
            return json.loads(value)
        except Exception as e:
            cache_logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        if not CacheConfig.CACHE_ENABLED or not self._connected:
            return False
        
        redis = self._get_redis()
        if redis is None:
            return False
        
        full_key = self._make_key(key)
        
        try:
            # Sérialiser la valeur
            serialized_value = json.dumps(value)
            
            # Définir le timeout (en secondes)
            if timeout is not None:
                redis.setex(full_key, timeout, serialized_value)
            elif self.default_timeout > 0:
                redis.setex(full_key, self.default_timeout, serialized_value)
            else:
                redis.set(full_key, serialized_value)
            
            cache_logger.debug(f"Redis cache set: {full_key}")
            return True
        except Exception as e:
            cache_logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache."""
        if not self._connected:
            return False
        
        redis = self._get_redis()
        if redis is None:
            return False
        
        full_key = self._make_key(key)
        
        try:
            result = redis.delete(full_key)
            cache_logger.debug(f"Redis cache deleted: {full_key}")
            return result > 0
        except Exception as e:
            cache_logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Efface tout le cache."""
        if not self._connected:
            return False
        
        redis = self._get_redis()
        if redis is None:
            return False
        
        try:
            # Utiliser SCAN pour supprimer toutes les clés avec notre préfixe
            # C'est plus sûr que FLUSHDB qui supprime tout
            prefix = self._make_key('')
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=f"{prefix}*")
                if keys:
                    redis.delete(*keys)
                if cursor == 0:
                    break
            
            cache_logger.info("Redis cache cleared")
            return True
        except Exception as e:
            cache_logger.error(f"Redis clear error: {e}")
            return False


class MemcachedCache(BaseCache):
    """
    Backend de cache Memcached.
    """
    
    def __init__(self, default_timeout: int = CacheConfig.CACHE_DEFAULT_TIMEOUT):
        super().__init__(default_timeout)
        self._client = None
        self._connected = False
    
    def _get_client(self):
        """Obtient ou crée la connexion Memcached."""
        if self._client is None:
            try:
                import memcache
                
                servers = CacheConfig.CACHE_MEMCACHED_SERVERS or [('localhost', 11211)]
                username = CacheConfig.CACHE_MEMCACHED_USERNAME
                password = CacheConfig.CACHE_MEMCACHED_PASSWORD
                
                self._client = memcache.Client(
                    servers,
                    cache_cas=True,
                    username=username,
                    password=password
                )
                
                # Tester la connexion
                self._client.set('test', '1', time=1)
                self._client.get('test')
                self._connected = True
                cache_logger.info("Connected to Memcached")
                
            except ImportError:
                cache_logger.warning("Memcached package not installed. Falling back to SimpleCache.")
                self._client = None
                self._connected = False
            except Exception as e:
                cache_logger.error(f"Failed to connect to Memcached: {e}")
                self._client = None
                self._connected = False
        
        return self._client
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache."""
        if not CacheConfig.CACHE_ENABLED or not self._connected:
            return None
        
        client = self._get_client()
        if client is None:
            return None
        
        full_key = self._make_key(key)
        
        try:
            value = client.get(full_key)
            if value is None:
                cache_logger.debug(f"Memcached cache miss: {full_key}")
                return None
            
            cache_logger.debug(f"Memcached cache hit: {full_key}")
            return value
        except Exception as e:
            cache_logger.error(f"Memcached get error: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        if not CacheConfig.CACHE_ENABLED or not self._connected:
            return False
        
        client = self._get_client()
        if client is None:
            return False
        
        full_key = self._make_key(key)
        
        try:
            # Définir le timeout (en secondes)
            expiry = timeout if timeout is not None else self.default_timeout
            
            client.set(full_key, value, time=expiry)
            cache_logger.debug(f"Memcached cache set: {full_key}")
            return True
        except Exception as e:
            cache_logger.error(f"Memcached set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache."""
        if not self._connected:
            return False
        
        client = self._get_client()
        if client is None:
            return False
        
        full_key = self._make_key(key)
        
        try:
            result = client.delete(full_key)
            cache_logger.debug(f"Memcached cache deleted: {full_key}")
            return result
        except Exception as e:
            cache_logger.error(f"Memcached delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Efface tout le cache."""
        if not self._connected:
            return False
        
        client = self._get_client()
        if client is None:
            return False
        
        try:
            client.flush_all()
            cache_logger.info("Memcached cache cleared")
            return True
        except Exception as e:
            cache_logger.error(f"Memcached clear error: {e}")
            return False


# ============================================================================
# GESTIONNAIRE DE CACHE PRINCIPAL
# ============================================================================

class CacheManager:
    """
    Gestionnaire de cache principal.
    
    Fournit une interface unifiée pour le cache et gère la création du backend
    approprié en fonction de la configuration.
    """
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self._cache = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialise le cache avec une application Flask."""
        self.app = app
        
        # Charger la configuration depuis l'app si disponible
        if hasattr(app, 'config'):
            self._load_config_from_app(app.config)
        
        # Créer le backend de cache approprié
        self._create_cache_backend()
        
        # Enregistrer les décorateurs
        self._register_decorators()
    
    def _load_config_from_app(self, config):
        """Charge la configuration depuis l'application Flask."""
        # Mettre à jour CacheConfig depuis app.config
        if hasattr(config, 'get'):
            cache_type = config.get('CACHE_TYPE', CacheConfig.CACHE_TYPE)
            if cache_type:
                CacheConfig.CACHE_TYPE = cache_type
            
            default_timeout = config.get('CACHE_DEFAULT_TIMEOUT', CacheConfig.CACHE_DEFAULT_TIMEOUT)
            if default_timeout:
                CacheConfig.CACHE_DEFAULT_TIMEOUT = default_timeout
            
            cache_enabled = config.get('CACHE_ENABLED', CacheConfig.CACHE_ENABLED)
            if cache_enabled is not None:
                CacheConfig.CACHE_ENABLED = cache_enabled
            
            cache_key_prefix = config.get('CACHE_KEY_PREFIX', CacheConfig.CACHE_KEY_PREFIX)
            if cache_key_prefix:
                CacheConfig.CACHE_KEY_PREFIX = cache_key_prefix
    
    def _create_cache_backend(self):
        """Crée le backend de cache approprié."""
        cache_type = CacheConfig.CACHE_TYPE.lower()
        
        if cache_type == 'redis':
            self._cache = RedisCache()
        elif cache_type == 'memcached':
            self._cache = MemcachedCache()
        else:
            # Par défaut, utiliser SimpleCache
            self._cache = SimpleCache()
        
        cache_logger.info(f"Cache backend initialized: {cache_type}")
    
    def _register_decorators(self):
        """Enregistre les décorateurs de cache."""
        if self.app:
            # Décorateur pour les routes
            self.app.template_filter('cache_buster')(self.cache_buster_filter)
    
    @property
    def cache(self) -> BaseCache:
        """Retourne l'instance du cache."""
        if self._cache is None:
            self._create_cache_backend()
        return self._cache
    
    def get(self, key: str) -> Any:
        """Récupère une valeur du cache."""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        return self.cache.set(key, value, timeout)
    
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache."""
        return self.cache.delete(key)
    
    def clear(self) -> bool:
        """Efface tout le cache."""
        return self.cache.clear()
    
    def cached(self, timeout: Optional[int] = None, key_prefix: str = '', 
              unless: Optional[Callable] = None, 
              vary_on: Optional[list] = None):
        """
        Décorateur pour mettre en cache le résultat d'une fonction.
        
        Args:
            timeout: Durée de vie du cache en secondes
            key_prefix: Préfixe pour la clé de cache
            unless: Fonction qui retourne True pour désactiver le cache
            vary_on: Liste de noms d'arguments à inclure dans la clé
        
        Exemple:
            @cache.cached(timeout=60, key_prefix='user_data', vary_on=['user_id'])
            def get_user_data(user_id):
                return expensive_query(user_id)
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Vérifier si le cache est désactivé
                if not CacheConfig.CACHE_ENABLED:
                    return f(*args, **kwargs)
                
                # Vérifier la condition unless
                if unless and unless():
                    return f(*args, **kwargs)
                
                # Générer la clé de cache
                cache_key = self._make_cache_key(
                    f, args, kwargs, key_prefix, vary_on
                )
                
                # Essayer de récupérer depuis le cache
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    cache_logger.debug(f"Cache hit for {f.__name__}")
                    return cached_value
                
                # Exécuter la fonction et mettre en cache le résultat
                result = f(*args, **kwargs)
                
                # Mettre en cache uniquement si le résultat n'est pas None
                if result is not None:
                    self.cache.set(cache_key, result, timeout)
                    cache_logger.debug(f"Cache set for {f.__name__}")
                
                return result
            
            # Ajouter un attribut pour identifier les fonctions cachées
            wrapped._cached = True
            wrapped._cache_timeout = timeout
            wrapped._cache_key_prefix = key_prefix
            
            return wrapped
        
        return decorator
    
    def memoize(self, timeout: Optional[int] = None, key_prefix: str = ''):
        """
        Décorateur pour mémoïser une fonction (cache basé sur les arguments).
        
        Similaire à cached, mais utilise toujours tous les arguments pour la clé.
        """
        return self.cached(timeout=timeout, key_prefix=key_prefix, vary_on=None)
    
    def _make_cache_key(self, f: Callable, args: tuple, kwargs: dict, 
                       key_prefix: str = '', vary_on: Optional[list] = None) -> str:
        """Génère une clé de cache unique pour une fonction et ses arguments."""
        # Base de la clé : nom de la fonction
        key_parts = [f.__module__, f.__name__]
        
        # Ajouter le préfixe
        if key_prefix:
            key_parts.insert(0, key_prefix)
        
        # Ajouter les arguments
        if vary_on:
            # Utiliser uniquement les arguments spécifiés
            for arg_name in vary_on:
                if arg_name in kwargs:
                    key_parts.append(str(kwargs[arg_name]))
                elif args and len(args) > vary_on.index(arg_name):
                    # Pour les arguments positionnels, c'est plus complexe
                    # On va simplement utiliser tous les args
                    key_parts.extend(str(arg) for arg in args)
                    break
        else:
            # Utiliser tous les arguments
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        # Ajouter des informations contextuelles (user_id, etc.)
        if hasattr(current_app, 'login_manager') and hasattr(current_app.login_manager, '_login_disabled'):
            # Si l'utilisateur est connecté, inclure son ID dans la clé
            from flask_login import current_user
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                key_parts.append(f"user_id={current_user.id}")
        
        # Créer un hash de la clé pour éviter les clés trop longues
        key_string = ':'.join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def cache_buster_filter(self, version: str = '1.0') -> str:
        """
        Filtre Jinja2 pour ajouter un cache buster aux URLs de ressources statiques.
        
        Utilisation dans les templates :
            <link href="{{ '/static/css/style.css' | cache_buster }}" />
        """
        import hashlib
        from flask import url_for
        
        # Si c'est une URL, ajouter un paramètre de version
        if version:
            return f"{self}?v={version}"
        return self
    
    def invalidate_on_change(self, model_class: type, 
                           key_prefix: str = '', 
                           id_field: str = 'id'):
        """
        Décorateur pour invalider automatiquement le cache lorsqu'un modèle change.
        
        Exemple:
            @cache.invalidate_on_change(User, key_prefix='user_data')
            def get_user_data(user_id):
                return User.query.get(user_id)
        """
        def decorator(f: Callable) -> Callable:
            # Enregistrer la fonction pour invalidation future
            if not hasattr(f, '_cache_invalidation_models'):
                f._cache_invalidation_models = []
            
            f._cache_invalidation_models.append({
                'model': model_class,
                'key_prefix': key_prefix,
                'id_field': id_field
            })
            
            return f
        
        return decorator
    
    def invalidate_model_cache(self, model_class: type, instance_id: Optional[int] = None):
        """
        Invalide le cache pour un modèle spécifique.
        
        Args:
            model_class: La classe du modèle
            instance_id: L'ID de l'instance (optionnel, pour invalider uniquement une instance)
        """
        # Trouver toutes les fonctions qui ont enregistré ce modèle pour invalidation
        # Cela nécessiterait un registre global, à implémenter si nécessaire
        pass


# ============================================================================
# CLÉS DE CACHE SPÉCIFIQUES À L'APPLICATION
# ============================================================================

class CacheKeys:
    """
    Clés de cache standardisées pour l'application Leviia Schedule.
    """
    
    # Utilisateurs
    ALL_USERS = 'all_users'
    USER_BY_ID = 'user:{user_id}'
    USER_BY_EMAIL = 'user:email:{email}'
    
    # Groupes
    ALL_GROUPS = 'all_groups'
    GROUP_BY_ID = 'group:{group_id}'
    
    # Types de shifts
    ALL_SHIFT_TYPES = 'all_shift_types'
    SHIFT_TYPE_BY_ID = 'shift_type:{shift_type_id}'
    
    # Shifts
    ALL_SHIFTS = 'all_shifts'
    SHIFTS_BY_DATE = 'shifts:date:{date}'
    SHIFTS_BY_USER = 'shifts:user:{user_id}'
    SHIFTS_BY_DATE_RANGE = 'shifts:date_range:{start_date}:{end_date}'
    
    # Astreintes
    ALL_ONCALLS = 'all_oncalls'
    ONCALL_BY_DATE = 'oncall:date:{date}'
    ONCALL_BY_USER = 'oncall:user:{user_id}'
    
    # Congés
    ALL_LEAVES = 'all_leaves'
    LEAVES_BY_DATE = 'leaves:date:{date}'
    LEAVES_BY_USER = 'leaves:user:{user_id}'
    
    # Statistiques
    DASHBOARD_STATS = 'dashboard:stats'
    USER_STATS = 'user:stats:{user_id}'
    
    # Export ICS
    ICS_EXPORT_SHIFTS = 'ics:export:shifts:{user_id}:{scope}'
    ICS_EXPORT_ONCALL = 'ics:export:oncall:{user_id}:{scope}'
    ICS_EXPORT_LEAVES = 'ics:export:leaves:{user_id}:{scope}'
    
    # Automatisation
    AUTOMATION_STATUS = 'automation:status'
    AUTOMATION_ELIGIBLE_USERS = 'automation:eligible_users'
    
    @staticmethod
    def format_key(key_template: str, **kwargs) -> str:
        """Formate une clé de cache avec des paramètres."""
        return key_template.format(**kwargs)


# ============================================================================
# INSTANCE GLOBALE DU CACHE
# ============================================================================

# Créer une instance globale du cache
cache = CacheManager()


def init_cache(app: Flask):
    """
    Initialise le cache avec une application Flask.
    
    À appeler depuis app/__init__.py après l'initialisation de l'application.
    """
    cache.init_app(app)
    return cache


def get_cache():
    """Retourne l'instance globale du cache."""
    return cache
