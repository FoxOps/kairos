"""
Configuration des performances pour Leviia Schedule.

Ce fichier centralise toutes les configurations liées aux optimisations
de performance : cache, pagination, lazy loading, etc.

Utilisation :
    # Dans config.py ou directement dans l'application
    from config_performance import PerformanceConfig
    
    # Appliquer la configuration
    PerformanceConfig.configure(app)
    
    # Ou charger depuis l'environnement
    PerformanceConfig.from_env()
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# ÉNUMÉRATIONS
# ============================================================================

class CacheType(Enum):
    """Types de cache disponibles."""
    SIMPLE = 'simple'      # Cache en mémoire (SimpleCache)
    REDIS = 'redis'        # Cache Redis
    MEMCACHED = 'memcached'  # Cache Memcached


class PaginationStyle(Enum):
    """Styles de pagination disponibles."""
    BOOTSTRAP = 'bootstrap'
    SIMPLE = 'simple'
    NONE = 'none'


# ============================================================================
# CONFIGURATION PRINCIPALE
# ============================================================================

@dataclass
class CacheSettings:
    """Configuration du cache."""
    # Type de cache
    cache_type: CacheType = CacheType.SIMPLE
    
    # Activation/désactivation
    enabled: bool = True
    
    # Configuration SimpleCache
    default_timeout: int = 300  # 5 minutes en secondes
    max_entries: int = 1000
    cleanup_threshold: float = 0.75
    
    # Configuration Redis
    redis_url: Optional[str] = None
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_socket_timeout: int = 5
    redis_connect_timeout: int = 5
    
    # Configuration Memcached
    memcached_servers: List[tuple] = field(default_factory=lambda: [('localhost', 11211)])
    memcached_username: Optional[str] = None
    memcached_password: Optional[str] = None
    
    # Préfixe des clés
    key_prefix: str = 'leviia:'
    
    # Clés spécifiques à mettre en cache
    cacheable_routes: List[str] = field(default_factory=lambda: [
        'index',
        'schedule',
        'oncall',
        'leave',
        'admin.users',
        'admin.groups',
        'admin.shift-types',
    ])
    
    # Durée de cache par route (en secondes)
    route_cache_timeout: Dict[str, int] = field(default_factory=lambda: {
        'index': 60,
        'schedule': 120,
        'oncall': 120,
        'leave': 120,
        'admin.users': 300,
        'admin.groups': 300,
        'admin.shift-types': 300,
    })


@dataclass
class PaginationSettings:
    """Configuration de la pagination."""
    # Activation/désactivation
    enabled: bool = True
    
    # Paramètres par défaut
    default_per_page: int = 20
    max_per_page: int = 100
    per_page_options: List[int] = field(default_factory=lambda: [5, 10, 20, 50, 100])
    
    # Style des liens
    style: PaginationStyle = PaginationStyle.BOOTSTRAP
    
    # Nombre de pages à afficher autour de la page courante
    window: int = 2
    
    # Pagination par curseur
    cursor_page_size: int = 20


@dataclass
class LazyLoadingSettings:
    """Configuration du lazy loading."""
    # Activation/désactivation
    enabled: bool = True
    
    # Taille des batches
    default_batch_size: int = 20
    
    # Scroll infini
    scroll_threshold: int = 100  # pixels
    debounce_delay: int = 300  # ms
    
    # Logging
    log_operations: bool = False


@dataclass
class QueryOptimizationSettings:
    """Configuration de l'optimisation des requêtes SQL."""
    # Utiliser joinedload pour éviter le N+1
    use_joinedload: bool = True
    
    # Utiliser selectinload pour les collections
    use_selectinload: bool = True
    
    # Charger les relations par défaut
    default_eager_loads: Dict[str, List[str]] = field(default_factory=lambda: {
        'User': ['group'],
        'Shift': ['user', 'shift_type'],
        'OnCall': ['user'],
        'Leave': ['user'],
    })
    
    # Index à créer automatiquement
    auto_indexes: List[Dict[str, Any]] = field(default_factory=lambda: [
        # Index pour les requêtes fréquentes
        {'model': 'Shift', 'columns': ['user_id', 'date']},
        {'model': 'Shift', 'columns': ['date', 'start_time']},
        {'model': 'OnCall', 'columns': ['user_id', 'start_time', 'end_time']},
        {'model': 'Leave', 'columns': ['user_id', 'start_date', 'end_date']},
    ])


@dataclass
class PerformanceConfig:
    """
    Configuration complète des performances.
    
    Centralise toutes les configurations liées aux optimisations.
    """
    cache: CacheSettings = field(default_factory=CacheSettings)
    pagination: PaginationSettings = field(default_factory=PaginationSettings)
    lazy_loading: LazyLoadingSettings = field(default_factory=LazyLoadingSettings)
    query_optimization: QueryOptimizationSettings = field(default_factory=QueryOptimizationSettings)
    
    # Activation globale
    performance_monitoring: bool = False
    
    # Seuil pour les avertissements de performance
    slow_query_threshold: float = 1.0  # secondes
    
    @classmethod
    def from_env(cls) -> 'PerformanceConfig':
        """
        Charge la configuration depuis les variables d'environnement.
        
        Returns:
            Instance de PerformanceConfig avec les valeurs de l'environnement
        """
        def get_bool(env_var: str, default: bool = False) -> bool:
            value = os.environ.get(env_var, '').lower()
            return value in ('true', '1', 'yes', 'y', 'on') if value else default
        
        def get_int(env_var: str, default: int = 0) -> int:
            value = os.environ.get(env_var, '')
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        def get_float(env_var: str, default: float = 0.0) -> float:
            value = os.environ.get(env_var, '')
            try:
                return float(value) if value else default
            except ValueError:
                return default
        
        def get_list(env_var: str, default: Optional[List] = None) -> List:
            value = os.environ.get(env_var, '')
            if not value:
                return default or []
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [x.strip() for x in value.split(',') if x.strip()]
        
        # Configuration du cache
        cache_type = os.environ.get('CACHE_TYPE', 'simple')
        cache_settings = CacheSettings(
            cache_type=CacheType(cache_type),
            enabled=get_bool('CACHE_ENABLED', True),
            default_timeout=get_int('CACHE_DEFAULT_TIMEOUT', 300),
            max_entries=get_int('CACHE_MAX_ENTRIES', 1000),
            cleanup_threshold=get_float('CACHE_THRESHOLD', 0.75),
            redis_url=os.environ.get('CACHE_REDIS_URL'),
            redis_password=os.environ.get('CACHE_REDIS_PASSWORD'),
            redis_db=get_int('CACHE_REDIS_DB', 0),
            redis_socket_timeout=get_int('CACHE_REDIS_SOCKET_TIMEOUT', 5),
            redis_connect_timeout=get_int('CACHE_REDIS_CONNECT_TIMEOUT', 5),
            key_prefix=os.environ.get('CACHE_KEY_PREFIX', 'leviia:'),
        )
        
        # Configuration de la pagination
        pagination_settings = PaginationSettings(
            enabled=get_bool('PAGINATION_ENABLED', True),
            default_per_page=get_int('PAGINATION_DEFAULT_PER_PAGE', 20),
            max_per_page=get_int('PAGINATION_MAX_PER_PAGE', 100),
            per_page_options=get_list('PAGINATION_PER_PAGE_OPTIONS', [5, 10, 20, 50, 100]),
            style=PaginationStyle(os.environ.get('PAGINATION_STYLE', 'bootstrap')),
            window=get_int('PAGINATION_WINDOW', 2),
            cursor_page_size=get_int('PAGINATION_CURSOR_PAGE_SIZE', 20),
        )
        
        # Configuration du lazy loading
        lazy_loading_settings = LazyLoadingSettings(
            enabled=get_bool('LAZY_LOADING_ENABLED', True),
            default_batch_size=get_int('LAZY_LOAD_DEFAULT_BATCH_SIZE', 20),
            scroll_threshold=get_int('LAZY_LOAD_SCROLL_THRESHOLD', 100),
            debounce_delay=get_int('LAZY_LOAD_DEBOUNCE_DELAY', 300),
            log_operations=get_bool('LAZY_LOAD_LOG_OPERATIONS', False),
        )
        
        # Configuration globale
        return cls(
            cache=cache_settings,
            pagination=pagination_settings,
            lazy_loading=lazy_loading_settings,
            performance_monitoring=get_bool('PERFORMANCE_MONITORING_ENABLED', False),
            slow_query_threshold=get_float('SLOW_QUERY_THRESHOLD', 1.0),
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceConfig':
        """
        Charge la configuration depuis un dictionnaire.
        
        Args:
            data: Dictionnaire de configuration
        
        Returns:
            Instance de PerformanceConfig
        """
        # Convertir les sous-configurations
        cache_data = data.get('cache', {})
        cache_settings = CacheSettings(
            cache_type=CacheType(cache_data.get('cache_type', 'simple')),
            enabled=cache_data.get('enabled', True),
            default_timeout=cache_data.get('default_timeout', 300),
            max_entries=cache_data.get('max_entries', 1000),
            cleanup_threshold=cache_data.get('cleanup_threshold', 0.75),
            redis_url=cache_data.get('redis_url'),
            redis_password=cache_data.get('redis_password'),
            redis_db=cache_data.get('redis_db', 0),
            key_prefix=cache_data.get('key_prefix', 'leviia:'),
        )
        
        pagination_data = data.get('pagination', {})
        pagination_settings = PaginationSettings(
            enabled=pagination_data.get('enabled', True),
            default_per_page=pagination_data.get('default_per_page', 20),
            max_per_page=pagination_data.get('max_per_page', 100),
            per_page_options=pagination_data.get('per_page_options', [5, 10, 20, 50, 100]),
            style=PaginationStyle(pagination_data.get('style', 'bootstrap')),
            window=pagination_data.get('window', 2),
        )
        
        lazy_loading_data = data.get('lazy_loading', {})
        lazy_loading_settings = LazyLoadingSettings(
            enabled=lazy_loading_data.get('enabled', True),
            default_batch_size=lazy_loading_data.get('default_batch_size', 20),
            scroll_threshold=lazy_loading_data.get('scroll_threshold', 100),
            debounce_delay=lazy_loading_data.get('debounce_delay', 300),
            log_operations=lazy_loading_data.get('log_operations', False),
        )
        
        return cls(
            cache=cache_settings,
            pagination=pagination_settings,
            lazy_loading=lazy_loading_settings,
            performance_monitoring=data.get('performance_monitoring', False),
            slow_query_threshold=data.get('slow_query_threshold', 1.0),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        return {
            'cache': {
                'cache_type': self.cache.cache_type.value,
                'enabled': self.cache.enabled,
                'default_timeout': self.cache.default_timeout,
                'max_entries': self.cache.max_entries,
                'cleanup_threshold': self.cache.cleanup_threshold,
                'redis_url': self.cache.redis_url,
                'redis_db': self.cache.redis_db,
                'key_prefix': self.cache.key_prefix,
            },
            'pagination': {
                'enabled': self.pagination.enabled,
                'default_per_page': self.pagination.default_per_page,
                'max_per_page': self.pagination.max_per_page,
                'per_page_options': self.pagination.per_page_options,
                'style': self.pagination.style.value,
                'window': self.pagination.window,
            },
            'lazy_loading': {
                'enabled': self.lazy_loading.enabled,
                'default_batch_size': self.lazy_loading.default_batch_size,
                'scroll_threshold': self.lazy_loading.scroll_threshold,
                'debounce_delay': self.lazy_loading.debounce_delay,
                'log_operations': self.lazy_loading.log_operations,
            },
            'performance_monitoring': self.performance_monitoring,
            'slow_query_threshold': self.slow_query_threshold,
        }
    
    def configure(self, app) -> None:
        """
        Configure une application Flask avec ces paramètres de performance.
        
        Args:
            app: Application Flask à configurer
        """
        # Configuration du cache
        app.config['CACHE_TYPE'] = self.cache.cache_type.value
        app.config['CACHE_ENABLED'] = self.cache.enabled
        app.config['CACHE_DEFAULT_TIMEOUT'] = self.cache.default_timeout
        app.config['CACHE_MAX_ENTRIES'] = self.cache.max_entries
        app.config['CACHE_THRESHOLD'] = self.cache.cleanup_threshold
        app.config['CACHE_KEY_PREFIX'] = self.cache.key_prefix
        
        if self.cache.redis_url:
            app.config['CACHE_REDIS_URL'] = self.cache.redis_url
        if self.cache.redis_password:
            app.config['CACHE_REDIS_PASSWORD'] = self.cache.redis_password
        app.config['CACHE_REDIS_DB'] = self.cache.redis_db
        
        # Configuration de la pagination
        app.config['PAGINATION_ENABLED'] = self.pagination.enabled
        app.config['PAGINATION_DEFAULT_PER_PAGE'] = self.pagination.default_per_page
        app.config['PAGINATION_MAX_PER_PAGE'] = self.pagination.max_per_page
        app.config['PAGINATION_PER_PAGE_OPTIONS'] = json.dumps(self.pagination.per_page_options)
        app.config['PAGINATION_STYLE'] = self.pagination.style.value
        app.config['PAGINATION_WINDOW'] = self.pagination.window
        
        # Configuration du lazy loading
        app.config['LAZY_LOADING_ENABLED'] = self.lazy_loading.enabled
        app.config['LAZY_LOAD_DEFAULT_BATCH_SIZE'] = self.lazy_loading.default_batch_size
        app.config['LAZY_LOAD_SCROLL_THRESHOLD'] = self.lazy_loading.scroll_threshold
        app.config['LAZY_LOAD_DEBOUNCE_DELAY'] = self.lazy_loading.debounce_delay
        app.config['LAZY_LOAD_LOG_OPERATIONS'] = self.lazy_loading.log_operations
        
        # Configuration du monitoring
        app.config['PERFORMANCE_MONITORING_ENABLED'] = self.performance_monitoring
        app.config['SLOW_QUERY_THRESHOLD'] = self.slow_query_threshold


# ============================================================================
# CONFIGURATIONS PRÉDÉFINIES
# ============================================================================

def get_development_config() -> PerformanceConfig:
    """
    Retourne une configuration optimisée pour le développement.
    
    Désactive le cache et active le logging pour le débogage.
    """
    return PerformanceConfig(
        cache=CacheSettings(
            cache_type=CacheType.SIMPLE,
            enabled=False,  # Désactivé en développement
            default_timeout=60,
            max_entries=100,
        ),
        pagination=PaginationSettings(
            enabled=True,
            default_per_page=10,
            max_per_page=50,
        ),
        lazy_loading=LazyLoadingSettings(
            enabled=True,
            default_batch_size=10,
            log_operations=True,
        ),
        performance_monitoring=True,
        slow_query_threshold=0.5,
    )


def get_production_config() -> PerformanceConfig:
    """
    Retourne une configuration optimisée pour la production.
    
    Active le cache Redis si disponible, sinon SimpleCache.
    """
    # Vérifier si Redis est disponible
    redis_available = os.environ.get('CACHE_REDIS_URL') is not None
    
    return PerformanceConfig(
        cache=CacheSettings(
            cache_type=CacheType.REDIS if redis_available else CacheType.SIMPLE,
            enabled=True,
            default_timeout=300,
            max_entries=5000,
            redis_url=os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0'),
        ),
        pagination=PaginationSettings(
            enabled=True,
            default_per_page=20,
            max_per_page=100,
        ),
        lazy_loading=LazyLoadingSettings(
            enabled=True,
            default_batch_size=20,
            log_operations=False,
        ),
        performance_monitoring=True,
        slow_query_threshold=1.0,
    )


def get_testing_config() -> PerformanceConfig:
    """
    Retourne une configuration optimisée pour les tests.
    
    Désactive toutes les optimisations pour des tests prévisibles.
    """
    return PerformanceConfig(
        cache=CacheSettings(
            cache_type=CacheType.SIMPLE,
            enabled=False,
        ),
        pagination=PaginationSettings(
            enabled=False,
        ),
        lazy_loading=LazyLoadingSettings(
            enabled=False,
        ),
        performance_monitoring=False,
    )


# ============================================================================
# UTILITAIRES
# ============================================================================

def apply_performance_config(app, config: Optional[PerformanceConfig] = None) -> PerformanceConfig:
    """
    Applique une configuration de performance à une application Flask.
    
    Args:
        app: Application Flask
        config: Configuration à appliquer (par défaut, charge depuis l'environnement)
    
    Returns:
        La configuration appliquée
    """
    if config is None:
        config = PerformanceConfig.from_env()
    
    config.configure(app)
    return config


def get_performance_config() -> PerformanceConfig:
    """
    Récupère la configuration de performance actuelle.
    
    Charge depuis l'environnement ou utilise les valeurs par défaut.
    """
    return PerformanceConfig.from_env()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'PerformanceConfig',
    'CacheSettings',
    'PaginationSettings',
    'LazyLoadingSettings',
    'QueryOptimizationSettings',
    'CacheType',
    'PaginationStyle',
    'get_development_config',
    'get_production_config',
    'get_testing_config',
    'apply_performance_config',
    'get_performance_config',
]
