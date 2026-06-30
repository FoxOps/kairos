"""
Module de monitoring des performances pour Leviia Schedule.

Ce module fournit des outils pour surveiller et analyser les performances
de l'application, incluant :
- Mesure du temps d'exécution des requêtes
- Détection des requêtes lentes
- Statistiques d'utilisation du cache
- Métriques de pagination
- Logging des performances

Utilisation :
    from app.utils.performance_monitor import PerformanceMonitor, monitor_performance
    
    # Décorer une route pour le monitoring
    @monitor_performance
    def my_route():
        return expensive_operation()
    
    # Ou utiliser le moniteur global
    monitor = PerformanceMonitor.get_instance()
    monitor.start_request()
    # ... code à surveiller ...
    monitor.end_request()
    
    # Récupérer les statistiques
    stats = monitor.get_stats()
"""

import time
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from flask import Flask, request, g
import logging

# Logger pour le monitoring des performances
performance_logger = logging.getLogger('performance')


# ============================================================================
# CONFIGURATION
# ============================================================================

class PerformanceMonitorConfig:
    """Configuration du monitoring des performances."""
    
    # Activation/désactivation
    ENABLED = True
    
    # Seuil pour les requêtes lentes (en secondes)
    SLOW_QUERY_THRESHOLD = 1.0
    
    # Seuil pour les avertissements (en secondes)
    WARNING_THRESHOLD = 0.5
    
    # Nombre maximum de requêtes à stocker en mémoire
    MAX_REQUESTS_STORED = 1000
    
    # Durée de conservation des statistiques (en secondes)
    STATS_RETENTION = 3600  # 1 heure
    
    # Activer le logging des requêtes lentes
    LOG_SLOW_QUERIES = True
    
    # Activer le logging des statistiques
    LOG_STATISTICS = True
    
    # Intervalle de logging des statistiques (en secondes)
    STATS_LOG_INTERVAL = 60
    
    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement."""
        import os
        
        
# Charger la configuration depuis l'environnement
PerformanceMonitorConfig.from_env()


# ============================================================================
# CLASSES DE DONNÉES
# ============================================================================

class RequestMetrics:
    """Métriques pour une requête individuelle."""
    
    def __init__(self, 
                 request_id: str,
                 path: str,
                 method: str,
                 start_time: float = None):
        """
        Initialise les métriques d'une requête.
        
        Args:
            request_id: Identifiant unique de la requête
            path: Chemin de la requête
            method: Méthode HTTP
            start_time: Heure de début (time.time())
        """
        self.request_id = request_id
        self.path = path
        self.method = method
        self.start_time = start_time or time.time()
        self.end_time = None
        self.duration = None
        self.sql_queries = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.memory_usage = None
        self.status_code = None
        self.is_slow = False
        self.is_warning = False
    
    def end(self, status_code: int = 200):
        """Termine la requête et calcule la durée."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status_code = status_code
        self.is_slow = self.duration >= PerformanceMonitorConfig.SLOW_QUERY_THRESHOLD
        self.is_warning = self.duration >= PerformanceMonitorConfig.WARNING_THRESHOLD
    
    def add_sql_query(self, query: str, duration: float, params: Optional[Dict] = None):
        """Ajoute une requête SQL exécutée."""
        self.sql_queries.append({
            'query': query,
            'duration': duration,
            'params': params,
            'timestamp': time.time()
        })
    
    def add_cache_access(self, hit: bool):
        """Ajoute un accès au cache."""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit les métriques en dictionnaire."""
        return {
            'request_id': self.request_id,
            'path': self.path,
            'method': self.method,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status_code': self.status_code,
            'is_slow': self.is_slow,
            'is_warning': self.is_warning,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hit_rate,
            'sql_query_count': len(self.sql_queries),
            'sql_total_duration': sum(q['duration'] for q in self.sql_queries),
            'memory_usage': self.memory_usage,
        }
    
    @property
    def cache_hit_rate(self) -> float:
        """Calcule le taux de succès du cache."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


class AggregatedMetrics:
    """Métriques agrégées pour une période."""
    
    def __init__(self):
        """Initialise les métriques agrégées."""
        self.start_time = time.time()
        self.end_time = None
        self.request_count = 0
        self.total_duration = 0.0
        self.sql_query_count = 0
        self.sql_total_duration = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.slow_requests = 0
        self.warning_requests = 0
        self.requests_by_path = {}
        self.sql_queries_by_type = {}
    
    def add_request(self, metrics: RequestMetrics):
        """Ajoute les métriques d'une requête."""
        self.request_count += 1
        self.total_duration += metrics.duration
        self.cache_hits += metrics.cache_hits
        self.cache_misses += metrics.cache_misses
        self.sql_query_count += len(metrics.sql_queries)
        self.sql_total_duration += sum(q['duration'] for q in metrics.sql_queries)
        
        if metrics.is_slow:
            self.slow_requests += 1
        if metrics.is_warning:
            self.warning_requests += 1
        
        # Agrégation par chemin
        if metrics.path not in self.requests_by_path:
            self.requests_by_path[metrics.path] = {
                'count': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0,
                'max_duration': 0.0,
                'min_duration': float('inf'),
            }
        
        path_metrics = self.requests_by_path[metrics.path]
        path_metrics['count'] += 1
        path_metrics['total_duration'] += metrics.duration
        path_metrics['avg_duration'] = path_metrics['total_duration'] / path_metrics['count']
        path_metrics['max_duration'] = max(path_metrics['max_duration'], metrics.duration)
        path_metrics['min_duration'] = min(path_metrics['min_duration'], metrics.duration)
        
        # Agrégation par type de requête SQL
        for query in metrics.sql_queries:
            # Extraire le type de requête (SELECT, INSERT, etc.)
            query_type = query['query'].split()[0].upper() if query['query'] else 'UNKNOWN'
            
            if query_type not in self.sql_queries_by_type:
                self.sql_queries_by_type[query_type] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'avg_duration': 0.0,
                }
            
            type_metrics = self.sql_queries_by_type[query_type]
            type_metrics['count'] += 1
            type_metrics['total_duration'] += query['duration']
            type_metrics['avg_duration'] = type_metrics['total_duration'] / type_metrics['count']
    
    def end(self):
        """Termine la période de collecte."""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Retourne la durée de la période."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    @property
    def avg_request_duration(self) -> float:
        """Calcule la durée moyenne des requêtes."""
        if self.request_count == 0:
            return 0.0
        return self.total_duration / self.request_count
    
    @property
    def avg_sql_query_duration(self) -> float:
        """Calcule la durée moyenne des requêtes SQL."""
        if self.sql_query_count == 0:
            return 0.0
        return self.sql_total_duration / self.sql_query_count
    
    @property
    def cache_hit_rate(self) -> float:
        """Calcule le taux de succès du cache."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    @property
    def requests_per_second(self) -> float:
        """Calcule le nombre de requêtes par seconde."""
        if self.duration == 0:
            return 0.0
        return self.request_count / self.duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit les métriques en dictionnaire."""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'request_count': self.request_count,
            'total_duration': self.total_duration,
            'avg_request_duration': self.avg_request_duration,
            'requests_per_second': self.requests_per_second,
            'sql_query_count': self.sql_query_count,
            'sql_total_duration': self.sql_total_duration,
            'avg_sql_query_duration': self.avg_sql_query_duration,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hit_rate,
            'slow_requests': self.slow_requests,
            'warning_requests': self.warning_requests,
            'requests_by_path': self.requests_by_path,
            'sql_queries_by_type': self.sql_queries_by_type,
        }


# ============================================================================
# MONITEUR DE PERFORMANCES
# ============================================================================

class PerformanceMonitor:
    """
    Moniteur de performances pour l'application.
    
    Collecte et agrège les métriques de performance des requêtes.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implémentation du singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le moniteur."""
        if self._initialized:
            return
        
        self._initialized = True
        self._requests = []
        self._current_request = None
        self._aggregated_metrics = AggregatedMetrics()
        self._last_stats_log = time.time()
        self._stats = {}
        self._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'PerformanceMonitor':
        """Retourne l'instance singleton du moniteur."""
        return cls()
    
    def start_request(self, path: Optional[str] = None, method: Optional[str] = None) -> str:
        """
        Débute le suivi d'une requête.
        
        Args:
            path: Chemin de la requête (par défaut, utilise request.path)
            method: Méthode HTTP (par défaut, utilise request.method)
        
        Returns:
            Identifiant unique de la requête
        """
        if not PerformanceMonitorConfig.ENABLED:
            return ''
        
        import uuid
        request_id = str(uuid.uuid4())
        
        if path is None:
            from flask import request
            path = request.path if request else 'unknown'
        
        if method is None:
            from flask import request
            method = request.method if request else 'UNKNOWN'
        
        metrics = RequestMetrics(request_id, path, method)
        
        with self._lock:
            self._current_request = metrics
            self._requests.append(metrics)
            
            # Limiter le nombre de requêtes stockées
            if len(self._requests) > PerformanceMonitorConfig.MAX_REQUESTS_STORED:
                self._requests = self._requests[-PerformanceMonitorConfig.MAX_REQUESTS_STORED:]
        
        if PerformanceMonitorConfig.LOG_STATISTICS:
            self._maybe_log_stats()
        
        return request_id
    
    def end_request(self, status_code: int = 200) -> Optional[RequestMetrics]:
        """
        Termine le suivi d'une requête.
        
        Args:
            status_code: Code de statut HTTP
        
        Returns:
            Métriques de la requête terminée
        """
        if not PerformanceMonitorConfig.ENABLED:
            return None
        
        with self._lock:
            if self._current_request is None:
                return None
            
            self._current_request.end(status_code)
            
            # Ajouter aux métriques agrégées
            self._aggregated_metrics.add_request(self._current_request)
            
            # Loguer si la requête est lente
            if PerformanceMonitorConfig.LOG_SLOW_QUERIES and self._current_request.is_slow:
                performance_logger.warning(
                    f"Slow request: {self._current_request.method} {self._current_request.path} "
                    f"({self._current_request.duration:.3f}s)"
                )
            
            if self._current_request.is_warning:
                performance_logger.info(
                    f"Slow request warning: {self._current_request.method} {self._current_request.path} "
                    f"({self._current_request.duration:.3f}s)"
                )
            
            metrics = self._current_request
            self._current_request = None
            return metrics
    
    def add_sql_query(self, query: str, duration: float, params: Optional[Dict] = None):
        """
        Ajoute une requête SQL exécutée.
        
        Args:
            query: Requête SQL
            duration: Durée d'exécution en secondes
            params: Paramètres de la requête
        """
        if not PerformanceMonitorConfig.ENABLED:
            return
        
        with self._lock:
            if self._current_request is not None:
                self._current_request.add_sql_query(query, duration, params)
    
    def add_cache_access(self, hit: bool):
        """
        Ajoute un accès au cache.
        
        Args:
            hit: True si c'est un hit, False si c'est un miss
        """
        if not PerformanceMonitorConfig.ENABLED:
            return
        
        with self._lock:
            if self._current_request is not None:
                self._current_request.add_cache_access(hit)
    
    def get_current_request_metrics(self) -> Optional[RequestMetrics]:
        """Retourne les métriques de la requête courante."""
        return self._current_request
    
    def get_request_metrics(self, request_id: str) -> Optional[RequestMetrics]:
        """Retourne les métriques d'une requête spécifique."""
        with self._lock:
            for metrics in self._requests:
                if metrics.request_id == request_id:
                    return metrics
        return None
    
    def get_recent_requests(self, limit: int = 100) -> List[RequestMetrics]:
        """Retourne les métriques des requêtes récentes."""
        with self._lock:
            return list(reversed(self._requests[-limit:]))
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques globales.
        
        Returns:
            Dictionnaire avec les statistiques agrégées
        """
        with self._lock:
            # Finaliser les métriques agrégées actuelles
            self._aggregated_metrics.end()
            
            stats = {
                'monitoring_enabled': PerformanceMonitorConfig.ENABLED,
                'current_requests': len([r for r in self._requests if r.end_time is None]),
                'recent_requests': [m.to_dict() for m in self._requests[-100:]],
                'aggregated': self._aggregated_metrics.to_dict(),
                'config': {
                    'slow_query_threshold': PerformanceMonitorConfig.SLOW_QUERY_THRESHOLD,
                    'warning_threshold': PerformanceMonitorConfig.WARNING_THRESHOLD,
                }
            }
            
            # Réinitialiser les métriques agrégées
            self._aggregated_metrics = AggregatedMetrics()
            
            return stats
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé des performances.
        
        Returns:
            Dictionnaire avec un résumé des métriques
        """
        stats = self.get_stats()
        aggregated = stats['aggregated']
        
        return {
            'requests_per_second': aggregated['requests_per_second'],
            'avg_request_duration_ms': aggregated['avg_request_duration'] * 1000,
            'avg_sql_query_duration_ms': aggregated['avg_sql_query_duration'] * 1000,
            'cache_hit_rate': aggregated['cache_hit_rate'],
            'slow_requests_percentage': (
                (aggregated['slow_requests'] / aggregated['request_count']) * 100
                if aggregated['request_count'] > 0 else 0
            ),
            'sql_queries_per_request': (
                aggregated['sql_query_count'] / aggregated['request_count']
                if aggregated['request_count'] > 0 else 0
            ),
        }
    
    def reset(self):
        """Réinitialise toutes les métriques."""
        with self._lock:
            self._requests.clear()
            self._current_request = None
            self._aggregated_metrics = AggregatedMetrics()
    
    def _maybe_log_stats(self):
        """Log les statistiques périodiquement."""
        now = time.time()
        if now - self._last_stats_log >= PerformanceMonitorConfig.STATS_LOG_INTERVAL:
            summary = self.get_summary()
            performance_logger.info(
                f"Performance summary: {summary['requests_per_second']:.2f} req/s, "
                f"avg {summary['avg_request_duration_ms']:.2f}ms, "
                f"cache hit rate {summary['cache_hit_rate']:.2%}, "
                f"slow requests {summary['slow_requests_percentage']:.2f}%"
            )
            self._last_stats_log = now


# ============================================================================
# DÉCORATEURS
# ============================================================================

def monitor_performance(func: Callable) -> Callable:
    """
    Décorateur pour surveiller les performances d'une route ou fonction.
    
    Exemple:
        @app.route('/expensive-route')
        @monitor_performance
        def expensive_route():
            return expensive_operation()
    
    Args:
        func: Fonction à surveiller
    
    Returns:
        Fonction décorée
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not PerformanceMonitorConfig.ENABLED:
            return func(*args, **kwargs)
        
        monitor = PerformanceMonitor.get_instance()
        
        # Débuter la requête
        monitor.start_request()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Terminer la requête
            monitor.end_request()
    
    return wrapper


def monitor_sql_queries(func: Callable) -> Callable:
    """
    Décorateur pour surveiller les requêtes SQL.
    
    Exemple:
        @monitor_sql_queries
        def get_users():
            return User.query.all()
    
    Args:
        func: Fonction à surveiller
    
    Returns:
        Fonction décorée
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not PerformanceMonitorConfig.ENABLED:
            return func(*args, **kwargs)
        
        from app import db
        from sqlalchemy import event
        
        monitor = PerformanceMonitor.get_instance()
        
        # Fonction pour intercepter les requêtes SQL
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            start_time = context._query_start_time
            duration = time.time() - start_time
            monitor.add_sql_query(statement, duration, dict(parameters) if parameters else None)
        
        # Enregistrer les interceptors
        event.listen(db.engine, 'before_cursor_execute', before_cursor_execute)
        event.listen(db.engine, 'after_cursor_execute', after_cursor_execute)
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Retirer les interceptors
            event.remove(db.engine, 'before_cursor_execute', before_cursor_execute)
            event.remove(db.engine, 'after_cursor_execute', after_cursor_execute)
    
    return wrapper


def monitor_cache_access(func: Callable) -> Callable:
    """
    Décorateur pour surveiller les accès au cache.
    
    Exemple:
        @monitor_cache_access
        def get_cached_data():
            return cache.get('my_key')
    
    Args:
        func: Fonction à surveiller
    
    Returns:
        Fonction décorée
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not PerformanceMonitorConfig.ENABLED:
            return func(*args, **kwargs)
        
        monitor = PerformanceMonitor.get_instance()
        
        # Intercepter les accès au cache
        from app.utils.cache import cache
        original_get = cache.cache.get
        original_set = cache.cache.set
        
        def monitored_get(key):
            result = original_get(key)
            monitor.add_cache_access(result is not None)
            return result
        
        def monitored_set(key, value, timeout=None):
            result = original_set(key, value, timeout)
            # On ne compte pas les set comme des hits
            return result
        
        cache.cache.get = monitored_get
        cache.cache.set = monitored_set
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Restaurer les méthodes originales
            cache.cache.get = original_get
            cache.cache.set = original_set
    
    return wrapper


# ============================================================================
# MIDDLEWARE FLASK
# ============================================================================

class PerformanceMiddleware:
    """
    Middleware Flask pour le monitoring des performances.
    
    À enregistrer dans l'application Flask.
    
    Exemple:
        app = Flask(__name__)
        app.wsgi_app = PerformanceMiddleware(app.wsgi_app)
    """
    
    def __init__(self, app):
        """
        Initialise le middleware.
        
        Args:
            app: Application WSGI à envelopper
        """
        self.app = app
    
    def __call__(self, environ, start_response):
        """Traite une requête."""
        if not PerformanceMonitorConfig.ENABLED:
            return self.app(environ, start_response)
        
        monitor = PerformanceMonitor.get_instance()
        
        # Débuter la requête
        from flask import request
        path = request.path if request else environ.get('PATH_INFO', 'unknown')
        method = request.method if request else environ.get('REQUEST_METHOD', 'UNKNOWN')
        request_id = monitor.start_request(path, method)
        
        # Stocker l'ID de la requête dans l'environnement
        environ['performance.request_id'] = request_id
        
        def custom_start_response(status, response_headers, exc_info=None):
            # Extraire le code de statut
            status_code = int(status.split(' ')[0]) if isinstance(status, str) else status
            
            # Terminer la requête
            monitor.end_request(status_code)
            
            return start_response(status, response_headers, exc_info)
        
        try:
            return self.app(environ, custom_start_response)
        except Exception as e:
            # Terminer la requête en cas d'erreur
            monitor.end_request(500)
            raise


# ============================================================================
# UTILITAIRES
# ============================================================================

def get_performance_metrics() -> Dict[str, Any]:
    """
    Récupère les métriques de performance actuelles.
    
    Returns:
        Dictionnaire avec les métriques
    """
    monitor = PerformanceMonitor.get_instance()
    return monitor.get_stats()


def get_performance_summary() -> Dict[str, Any]:
    """
    Récupère un résumé des performances.
    
    Returns:
        Dictionnaire avec un résumé
    """
    monitor = PerformanceMonitor.get_instance()
    return monitor.get_summary()


def reset_performance_metrics():
    """Réinitialise les métriques de performance."""
    monitor = PerformanceMonitor.get_instance()
    monitor.reset()


def log_slow_query(query: str, duration: float, threshold: Optional[float] = None):
    """
    Log une requête SQL lente.
    
    Args:
        query: Requête SQL
        duration: Durée d'exécution en secondes
        threshold: Seuil pour considérer la requête comme lente
    """
    threshold = threshold or PerformanceMonitorConfig.SLOW_QUERY_THRESHOLD
    
    if duration >= threshold:
        performance_logger.warning(
            f"Slow SQL query ({duration:.3f}s >= {threshold:.3f}s): {query[:200]}..."
        )


# ============================================================================
# INTÉGRATION AVEC FLASK
# ============================================================================

def init_performance_monitoring(app: Flask):
    """
    Initialise le monitoring des performances pour une application Flask.
    
    Args:
        app: Application Flask
    """
    # Enregistrer le middleware
    app.wsgi_app = PerformanceMiddleware(app.wsgi_app)
    
    # Ajouter un template global pour les métriques
    @app.context_processor
    def inject_performance_metrics():
        monitor = PerformanceMonitor.get_instance()
        return {
            'performance_metrics': monitor.get_summary(),
            'performance_config': PerformanceMonitorConfig,
        }
    
    # Route pour les statistiques de performance (optionnelle)
    @app.route('/_performance/stats')
    def performance_stats():
        from flask import jsonify
        monitor = PerformanceMonitor.get_instance()
        return jsonify(monitor.get_stats())
    
    @app.route('/_performance/summary')
    def performance_summary():
        from flask import jsonify
        monitor = PerformanceMonitor.get_instance()
        return jsonify(monitor.get_summary())
    
    @app.route('/_performance/reset', methods=['POST'])
    def performance_reset():
        from flask import jsonify
        monitor = PerformanceMonitor.get_instance()
        monitor.reset()
        return jsonify({'status': 'ok', 'message': 'Performance metrics reset'})


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'PerformanceMonitor',
    'PerformanceMonitorConfig',
    'RequestMetrics',
    'AggregatedMetrics',
    'PerformanceMiddleware',
    'monitor_performance',
    'monitor_sql_queries',
    'monitor_cache_access',
    'init_performance_monitoring',
    'get_performance_metrics',
    'get_performance_summary',
    'reset_performance_metrics',
    'log_slow_query',
]
