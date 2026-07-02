"""
Cache configuration for Leviia Schedule.

This module provides configuration for the cache system.
"""


class CacheConfig:
    """
    Configuration du cache.
    
    Peut être configurée via variables d'environnement ou directement.
    
    Variables d'environnement disponibles:
    - CACHE_TYPE: 'simple' (défaut), 'redis', 'memcached'
    - CACHE_ENABLED: true/false (défaut: true)
    - CACHE_DEFAULT_TIMEOUT: durée en secondes (défaut: 300)
    - CACHE_MAX_ENTRIES: nombre maximal d'entrées (défaut: 1000)
    - CACHE_THRESHOLD: seuil de nettoyage (défaut: 0.75)
    - CACHE_KEY_PREFIX: préfixe pour les clés (défaut: 'leviia:')
    - CACHE_REDIS_URL: URL Redis (ex: 'redis://localhost:6379/0')
    - CACHE_REDIS_PASSWORD: mot de passe Redis
    - CACHE_REDIS_DB: numéro de base Redis (défaut: 0)
    """
    
    # Activation/désactivation du cache
    CACHE_ENABLED = False
    
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
    
    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement."""
        import os
        from app.utils.helpers import get_bool, get_int
        
        cls.CACHE_ENABLED = get_bool('CACHE_ENABLED', cls.CACHE_ENABLED)
        cls.CACHE_TYPE = os.environ.get('CACHE_TYPE', cls.CACHE_TYPE)
        cls.CACHE_DEFAULT_TIMEOUT = get_int('CACHE_DEFAULT_TIMEOUT', cls.CACHE_DEFAULT_TIMEOUT)
        cls.CACHE_MAX_ENTRIES = get_int('CACHE_MAX_ENTRIES', cls.CACHE_MAX_ENTRIES)
        cls.CACHE_THRESHOLD = float(os.environ.get('CACHE_THRESHOLD', cls.CACHE_THRESHOLD))
        cls.CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', cls.CACHE_KEY_PREFIX)
        cls.CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', cls.CACHE_REDIS_URL)
        cls.CACHE_REDIS_PASSWORD = os.environ.get('CACHE_REDIS_PASSWORD', cls.CACHE_REDIS_PASSWORD)
        cls.CACHE_REDIS_DB = get_int('CACHE_REDIS_DB', cls.CACHE_REDIS_DB)
        
        # Configuration Memcached
        memcached_servers = os.environ.get('CACHE_MEMCACHED_SERVERS', '')
        if memcached_servers:
            cls.CACHE_MEMCACHED_SERVERS = [s.strip() for s in memcached_servers.split(',')]
        cls.CACHE_MEMCACHED_USERNAME = os.environ.get('CACHE_MEMCACHED_USERNAME', cls.CACHE_MEMCACHED_USERNAME)
        cls.CACHE_MEMCACHED_PASSWORD = os.environ.get('CACHE_MEMCACHED_PASSWORD', cls.CACHE_MEMCACHED_PASSWORD)


# Charger la configuration depuis l'environnement
CacheConfig.from_env()
