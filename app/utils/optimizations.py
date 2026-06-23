"""
Module d'optimisations pour Leviia Schedule.

Ce module fournit des décorateurs et utilitaires pour optimiser les performances
des routes et fonctions de l'application.

Fonctionnalités :
- Décorateurs pour le cache des routes
- Décorateurs pour la pagination automatique
- Décorateurs pour le lazy loading
- Optimisation des requêtes SQLAlchemy
- Gestion des index de base de données

Utilisation :
    from app.utils.optimizations import (
        cached_route,
        paginated_route,
        optimize_query,
        eager_load,
    )
    
    # Route avec cache
    @app.route('/users')
    @cached_route(timeout=60)
    def list_users():
        users = User.query.order_by(User.name).all()
        return render_template('users.html', users=users)
    
    # Route avec pagination automatique
    @app.route('/shifts')
    @paginated_route(per_page=20)
    def list_shifts():
        return Shift.query.order_by(Shift.start_time)
    
    # Optimisation d'une requête
    @optimize_query(User, ['group'])
    def get_user_with_group(user_id):
        return User.query.get(user_id)
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from flask import Flask, request, jsonify, render_template
from sqlalchemy.orm import Query, joinedload, selectinload
from sqlalchemy import text, func, desc, asc
import time
import logging

# Logger pour les optimisations
optimization_logger = logging.getLogger('optimizations')


# ============================================================================
# DÉCORATEURS DE CACHE
# ============================================================================

def cached_route(timeout: int = 300, 
                key_prefix: str = '',
                unless: Optional[Callable[[], bool]] = None,
                vary_on: Optional[List[str]] = None,
                methods: Optional[List[str]] = None):
    """
    Décorateur pour mettre en cache le résultat d'une route Flask.
    
    Utilise le système de cache configuré dans app.utils.cache.
    
    Args:
        timeout: Durée de vie du cache en secondes
        key_prefix: Préfixe pour la clé de cache
        unless: Fonction qui retourne True pour désactiver le cache
        vary_on: Liste de paramètres de requête à inclure dans la clé
        methods: Méthodes HTTP pour lesquelles appliquer le cache
    
    Exemple:
        @app.route('/users')
        @cached_route(timeout=60, vary_on=['group_id'])
        def list_users():
            group_id = request.args.get('group_id')
            users = User.query.filter_by(group_id=group_id).all()
            return render_template('users.html', users=users)
    """
    from app.utils.cache import cache, CacheConfig
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Vérifier si le cache est désactivé
            if not CacheConfig.CACHE_ENABLED:
                return f(*args, **kwargs)
            
            # Vérifier la condition unless
            if unless and unless():
                return f(*args, **kwargs)
            
            # Vérifier la méthode HTTP
            if methods:
                current_method = request.method if request else 'GET'
                if current_method not in methods:
                    return f(*args, **kwargs)
            
            # Générer la clé de cache
            cache_key = _make_cache_key(f, request, key_prefix, vary_on)
            
            # Essayer de récupérer depuis le cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                optimization_logger.debug(f"Cache hit for {request.path}")
                return cached_response
            
            # Exécuter la fonction
            response = f(*args, **kwargs)
            
            # Mettre en cache la réponse
            if response is not None:
                cache.set(cache_key, response, timeout)
                optimization_logger.debug(f"Cache set for {request.path}")
            
            return response
        
        return wrapped
    
    return decorator


def _make_cache_key(f: Callable, request, key_prefix: str = '', vary_on: Optional[List[str]] = None) -> str:
    """Génère une clé de cache pour une route."""
    import hashlib
    
    # Base de la clé
    key_parts = [f.__module__, f.__name__, request.path]
    
    # Ajouter le préfixe
    if key_prefix:
        key_parts.insert(0, key_prefix)
    
    # Ajouter la méthode HTTP
    key_parts.append(request.method)
    
    # Ajouter les paramètres de requête
    if vary_on:
        for param in vary_on:
            value = request.args.get(param, '')
            key_parts.append(f"{param}={value}")
    else:
        # Utiliser tous les paramètres
        for key, value in request.args.items():
            key_parts.append(f"{key}={value}")
    
    # Ajouter l'ID de l'utilisateur si connecté
    from flask_login import current_user
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        key_parts.append(f"user_id={current_user.id}")
    
    # Créer un hash
    key_string = ':'.join(key_parts)
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def cache_result(timeout: int = 300, 
                key_func: Optional[Callable] = None,
                unless: Optional[Callable[[], bool]] = None):
    """
    Décorateur pour mettre en cache le résultat d'une fonction.
    
    Contrairement à cached_route, ce décorateur peut être utilisé sur n'importe
    quelle fonction, pas seulement les routes Flask.
    
    Args:
        timeout: Durée de vie du cache en secondes
        key_func: Fonction pour générer la clé de cache (reçoit *args, **kwargs)
        unless: Fonction qui retourne True pour désactiver le cache
    
    Exemple:
        @cache_result(timeout=60, key_func=lambda user_id: f'user:{user_id}')
        def get_user_data(user_id):
            return User.query.get(user_id)
    """
    from app.utils.cache import cache, CacheConfig
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not CacheConfig.CACHE_ENABLED:
                return f(*args, **kwargs)
            
            if unless and unless():
                return f(*args, **kwargs)
            
            # Générer la clé
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _make_function_cache_key(f, args, kwargs)
            
            # Essayer de récupérer depuis le cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                optimization_logger.debug(f"Cache hit for {f.__name__}")
                return cached_result
            
            # Exécuter la fonction
            result = f(*args, **kwargs)
            
            # Mettre en cache
            if result is not None:
                cache.set(cache_key, result, timeout)
                optimization_logger.debug(f"Cache set for {f.__name__}")
            
            return result
        
        return wrapped
    
    return decorator


def _make_function_cache_key(f: Callable, args: tuple, kwargs: dict) -> str:
    """Génère une clé de cache pour une fonction."""
    import hashlib
    
    key_parts = [f.__module__, f.__name__]
    
    # Ajouter les arguments
    for arg in args:
        key_parts.append(str(arg))
    
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={value}")
    
    # Créer un hash
    key_string = ':'.join(key_parts)
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


# ============================================================================
# DÉCORATEURS DE PAGINATION
# ============================================================================

def paginated_route(per_page: int = 20,
                  max_per_page: int = 100,
                  endpoint: Optional[str] = None,
                  count: bool = True):
    """
    Décorateur pour paginer automatiquement les résultats d'une route.
    
    Args:
        per_page: Nombre d'éléments par page par défaut
        max_per_page: Nombre maximum d'éléments par page
        endpoint: Endpoint Flask pour générer les URLs
        count: Compter le nombre total d'éléments
    
    Exemple:
        @app.route('/users')
        @paginated_route(per_page=20)
        def list_users():
            return User.query.order_by(User.name)
    """
    from app.utils.pagination import paginate_query, PaginationConfig
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not PaginationConfig.PAGINATION_ENABLED:
                result = f(*args, **kwargs)
                if isinstance(result, Query):
                    return result.all()
                return result
            
            # Récupérer les paramètres de pagination
            page = request.args.get('page', 1, type=int)
            per_page_param = request.args.get('per_page', per_page, type=int)
            
            # Valider per_page
            per_page = max(1, min(per_page_param, max_per_page))
            
            # Appeler la fonction pour obtenir la requête
            result = f(*args, **kwargs)
            
            # Si c'est une requête SQLAlchemy, la paginer
            if isinstance(result, Query):
                return paginate_query(
                    result,
                    page=page,
                    per_page=per_page,
                    endpoint=endpoint or f.__name__,
                    args=request.args.to_dict(),
                    count=count
                )
            
            # Si c'est une liste, créer une pagination simple
            if isinstance(result, list):
                from app.utils.pagination import Pagination
                total = len(result)
                offset = (page - 1) * per_page
                items = result[offset:offset + per_page]
                
                return Pagination(
                    items=items,
                    page=page,
                    per_page=per_page,
                    total=total,
                    endpoint=endpoint or f.__name__,
                    args=request.args.to_dict()
                )
            
            return result
        
        return wrapped
    
    return decorator


def paginated_api(per_page: int = 20,
                 max_per_page: int = 100,
                 model_name: Optional[str] = None):
    """
    Décorateur pour créer une API JSON paginée.
    
    Args:
        per_page: Nombre d'éléments par page par défaut
        max_per_page: Nombre maximum d'éléments par page
        model_name: Nom du modèle pour la sérialisation
    
    Exemple:
        @app.route('/api/users')
        @paginated_api(per_page=20, model_name='User')
        def api_users():
            return User.query.order_by(User.name)
    """
    from app.utils.pagination import paginate_query, PaginationConfig
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not PaginationConfig.PAGINATION_ENABLED:
                result = f(*args, **kwargs)
                if isinstance(result, Query):
                    items = result.all()
                else:
                    items = result
                
                return jsonify({
                    'items': [_serialize_item(item, model_name) for item in items],
                    'total': len(items),
                    'page': 1,
                    'per_page': len(items),
                })
            
            # Récupérer les paramètres de pagination
            page = request.args.get('page', 1, type=int)
            per_page_param = request.args.get('per_page', per_page, type=int)
            
            # Valider per_page
            per_page = max(1, min(per_page_param, max_per_page))
            
            # Appeler la fonction
            result = f(*args, **kwargs)
            
            # Paginer
            if isinstance(result, Query):
                pagination = paginate_query(
                    result,
                    page=page,
                    per_page=per_page,
                    count=True
                )
            else:
                from app.utils.pagination import Pagination
                items = result if isinstance(result, list) else [result]
                total = len(items)
                offset = (page - 1) * per_page
                page_items = items[offset:offset + per_page]
                
                pagination = Pagination(
                    items=page_items,
                    page=page,
                    per_page=per_page,
                    total=total
                )
            
            # Retourner au format JSON
            return jsonify({
                'items': [_serialize_item(item, model_name) for item in pagination.items],
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_previous': pagination.has_previous,
            })
        
        return wrapped
    
    return decorator


def _serialize_item(item: Any, model_name: Optional[str] = None) -> Any:
    """Sérialise un élément pour le JSON."""
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif hasattr(item, '__dict__'):
        # Exclure les attributs SQLAlchemy
        return {k: v for k, v in item.__dict__.items() 
                if not k.startswith('_') and not callable(v)}
    elif isinstance(item, dict):
        return item
    else:
        return str(item)


# ============================================================================
# OPTIMISATION DES REQUÊTES SQLALCHEMY
# ============================================================================

def eager_load(model_class: Type, 
              relationships: Optional[List[str]] = None,
              strategy: str = 'joinedload'):
    """
    Décorateur pour charger les relations de manière eager (éviter le N+1).
    
    Args:
        model_class: Classe du modèle
        relationships: Liste des relations à charger
        strategy: Stratégie de chargement ('joinedload' ou 'selectinload')
    
    Exemple:
        @eager_load(User, ['shifts', 'on_calls', 'leaves'])
        def get_user(user_id):
            return User.query.get(user_id)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Appeler la fonction pour obtenir la requête ou le résultat
            result = f(*args, **kwargs)
            
            # Si c'est une requête, appliquer le eager loading
            if isinstance(result, Query):
                if relationships:
                    for rel in relationships:
                        if strategy == 'selectinload':
                            result = result.options(selectinload(getattr(model_class, rel)))
                        else:
                            result = result.options(joinedload(getattr(model_class, rel)))
                return result
            
            # Si c'est un objet modèle, charger les relations
            if isinstance(result, model_class):
                if relationships:
                    for rel in relationships:
                        getattr(result, rel)  # Cela déclenche le lazy loading
                return result
            
            return result
        
        return wrapped
    
    return decorator


def optimize_query(model_class: Optional[Type] = None,
                   relationships: Optional[List[str]] = None,
                   filters: Optional[Dict] = None,
                   order_by: Optional[Union[str, List[str]]] = None,
                   limit: Optional[int] = None):
    """
    Décorateur pour optimiser une requête SQLAlchemy.
    
    Applique plusieurs optimisations :
    - Eager loading des relations
    - Filtrage
    - Tri
    - Limite
    
    Args:
        model_class: Classe du modèle (optionnel)
        relationships: Relations à charger
        filters: Dictionnaire de filtres à appliquer
        order_by: Champ(s) pour le tri
        limit: Limite du nombre de résultats
    
    Exemple:
        @optimize_query(User, relationships=['group'], order_by='name', limit=100)
        def get_active_users():
            return User.query.filter_by(is_active=True)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            result = f(*args, **kwargs)
            
            if not isinstance(result, Query):
                return result
            
            # Appliquer les filtres
            if filters:
                for field, value in filters.items():
                    if isinstance(value, dict):
                        # Filtrage complexe
                        for op, op_value in value.items():
                            if op == 'in':
                                result = result.filter(getattr(model_class, field).in_(op_value))
                            elif op == 'like':
                                result = result.filter(getattr(model_class, field).like(op_value))
                            # Ajouter d'autres opérateurs si nécessaire
                    else:
                        result = result.filter_by(**{field: value})
            
            # Appliquer le tri
            if order_by:
                if isinstance(order_by, str):
                    order_by = [order_by]
                
                for field in order_by:
                    if field.startswith('-'):
                        result = result.order_by(desc(getattr(model_class, field[1:])))
                    else:
                        result = result.order_by(asc(getattr(model_class, field)))
            
            # Appliquer le eager loading
            if model_class and relationships:
                for rel in relationships:
                    result = result.options(joinedload(getattr(model_class, rel)))
            
            # Appliquer la limite
            if limit:
                result = result.limit(limit)
            
            return result
        
        return wrapped
    
    return decorator


def batch_load(model_class: Type,
              ids: List[int],
              relationships: Optional[List[str]] = None) -> Dict[int, Any]:
    """
    Charge plusieurs objets en une seule requête (évite le N+1).
    
    Args:
        model_class: Classe du modèle
        ids: Liste des IDs à charger
        relationships: Relations à charger
    
    Returns:
        Dictionnaire {id: objet}
    
    Exemple:
        user_ids = [1, 2, 3, 4, 5]
        users = batch_load(User, user_ids, relationships=['group'])
        # users = {1: <User 1>, 2: <User 2>, ...}
    """
    from app import db
    
    if not ids:
        return {}
    
    # Construire la requête
    query = model_class.query.filter(model_class.id.in_(ids))
    
    # Appliquer le eager loading
    if relationships:
        for rel in relationships:
            query = query.options(joinedload(getattr(model_class, rel)))
    
    # Exécuter la requête
    items = query.all()
    
    # Créer le dictionnaire
    return {item.id: item for item in items}


# ============================================================================
# DÉCORATEURS DE LAZY LOADING
# ============================================================================

def lazy_route(batch_size: int = 20,
              cursor_field: str = 'id',
              order_by: Optional[Union[str, List[str]]] = None):
    """
    Décorateur pour implémenter le lazy loading sur une route.
    
    Args:
        batch_size: Taille des batches
        cursor_field: Champ à utiliser comme curseur
        order_by: Champ(s) pour le tri
    
    Exemple:
        @app.route('/api/users')
        @lazy_route(batch_size=20, cursor_field='id')
        def api_users():
            return User.query.order_by(User.id)
    """
    from app.utils.lazy_loading import LazyLoader
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Appeler la fonction pour obtenir la requête
            result = f(*args, **kwargs)
            
            if not isinstance(result, Query):
                return jsonify({'error': 'Expected a SQLAlchemy Query'}), 400
            
            # Créer le chargeur lazy
            loader = LazyLoader(result, batch_size=batch_size)
            
            # Récupérer le curseur depuis la requête
            cursor = request.args.get('cursor', None)
            
            # Charger le batch
            batch = loader.load_next_batch(cursor)
            
            # Sérialiser les résultats
            items = [_serialize_item(item) for item in batch['items']]
            
            return jsonify({
                'items': items,
                'next_cursor': batch['next_cursor'],
                'has_more': batch['has_more'],
            })
        
        return wrapped
    
    return decorator


def lazy_property_cache(timeout: int = 300):
    """
    Décorateur pour créer une propriété lazy avec cache.
    
    La valeur est calculée une seule fois et mise en cache.
    
    Args:
        timeout: Durée de vie du cache en secondes
    
    Exemple:
        class User:
            @lazy_property_cache(timeout=60)
            def expensive_computation(self):
                return complex_calculation(self.id)
    """
    from app.utils.cache import cache
    from app.utils.lazy_loading import lazy_property
    
    def decorator(func: Callable) -> property:
        attr_name = f'_{func.__name__}_cached'
        
        @property
        @wraps(func)
        def wrapper(self):
            if not hasattr(self, attr_name):
                result = func(self)
                if result is not None:
                    cache_key = f"{type(self).__name__}:{self.id}:{func.__name__}"
                    cache.set(cache_key, result, timeout)
                setattr(self, attr_name, result)
            return getattr(self, attr_name)
        
        return wrapper
    
    return decorator


# ============================================================================
# UTILITAIRES DIVERS
# ============================================================================

def measure_time(func: Callable) -> Callable:
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.
    
    Exemple:
        @measure_time
        def slow_function():
            time.sleep(1)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        optimization_logger.debug(
            f"Function {func.__name__} executed in {duration:.4f}s"
        )
        
        # Ajouter au monitoring des performances
        from app.utils.performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor.get_instance()
        if monitor.get_current_request_metrics():
            monitor.add_sql_query(
                f"function:{func.__name__}",
                duration
            )
        
        return result
    
    return wrapper


def retry_on_failure(max_retries: int = 3,
                    delay: float = 0.1,
                    exceptions: tuple = (Exception,)):
    """
    Décorateur pour réessayer une fonction en cas d'échec.
    
    Utile pour les opérations qui peuvent échouer temporairement
    (ex: verrouillage de base de données).
    
    Args:
        max_retries: Nombre maximum de tentatives
        delay: Délai entre les tentatives en secondes
        exceptions: Tuple d'exceptions à capturer
    
    Exemple:
        @retry_on_failure(max_retries=3, delay=0.1)
        def save_user(user):
            db.session.add(user)
            db.session.commit()
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise
            
            raise last_exception
        
        return wrapper
    
    return decorator


def bulk_operation(model_class: Type, 
                  operation: str = 'insert',
                  batch_size: int = 100):
    """
    Décorateur pour optimiser les opérations en masse.
    
    Args:
        model_class: Classe du modèle
        operation: Type d'opération ('insert', 'update', 'delete')
        batch_size: Taille des batches
    
    Exemple:
        @bulk_operation(User, operation='insert', batch_size=100)
        def create_users(user_data_list):
            users = [User(**data) for data in user_data_list]
            return users
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            from app import db
            
            result = f(*args, **kwargs)
            
            if operation == 'insert' and isinstance(result, list):
                # Insertion en masse
                for i in range(0, len(result), batch_size):
                    batch = result[i:i + batch_size]
                    db.session.bulk_save_objects(batch)
                db.session.commit()
                return result
            
            elif operation == 'update' and isinstance(result, list):
                # Mise à jour en masse
                for i in range(0, len(result), batch_size):
                    batch = result[i:i + batch_size]
                    db.session.bulk_update_mappings(model_class, batch)
                db.session.commit()
                return result
            
            elif operation == 'delete' and isinstance(result, list):
                # Suppression en masse
                for i in range(0, len(result), batch_size):
                    batch = result[i:i + batch_size]
                    for item in batch:
                        db.session.delete(item)
                db.session.commit()
                return result
            
            return result
        
        return wrapped
    
    return decorator


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Décorateurs de cache
    'cached_route',
    'cache_result',
    
    # Décorateurs de pagination
    'paginated_route',
    'paginated_api',
    
    # Optimisation des requêtes
    'eager_load',
    'optimize_query',
    'batch_load',
    
    # Décorateurs de lazy loading
    'lazy_route',
    'lazy_property_cache',
    
    # Utilitaires
    'measure_time',
    'retry_on_failure',
    'bulk_operation',
]
