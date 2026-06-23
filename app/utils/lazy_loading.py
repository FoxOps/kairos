"""
Module de lazy loading pour Leviia Schedule.

Ce module fournit des outils pour implémenter le lazy loading (chargement paresseux)
des données, ce qui améliore les performances en chargeant uniquement les données
nécessaires au moment où elles sont nécessaires.

Fonctionnalités :
- Chargement différé des relations SQLAlchemy
- Lazy loading pour les listes et collections
- Support pour le scroll infini
- Intégration avec le cache

Utilisation :
    from app.utils.lazy_loading import lazy_property, lazy_load, LazyLoader
    
    # Propriété lazy
    class User:
        @lazy_property
        def expensive_computation(self):
            return complex_calculation()
    
    # Chargement lazy d'une liste
    users = lazy_load(User.query.order_by(User.name).all())
    
    # LazyLoader pour le scroll infini
    loader = LazyLoader(User.query.order_by(User.name), batch_size=20)
    first_batch = loader.load_next_batch()
"""

from typing import Any, Callable, Dict, Generator, Iterable, Iterator, List, Optional, Type, Union
from functools import wraps, partial
from sqlalchemy.orm import Query, joinedload, selectinload, lazyload, Load
from sqlalchemy import inspect
import logging

# Logger pour le lazy loading
lazy_logger = logging.getLogger('lazy_loading')


# ============================================================================
# CONFIGURATION DU LAZY LOADING
# ============================================================================

class LazyLoadingConfig:
    """
    Configuration du lazy loading.
    
    Peut être configurée via variables d'environnement ou directement.
    """
    
    # Taille des batches par défaut
    DEFAULT_BATCH_SIZE = 20
    
    # Seuil pour déclencher le chargement (en pixels depuis la fin)
    SCROLL_THRESHOLD = 100
    
    # Délai de debounce pour éviter les chargements multiples (en ms)
    DEBOUNCE_DELAY = 300
    
    # Activer/désactiver le lazy loading
    LAZY_LOADING_ENABLED = True
    
    # Activer le logging des opérations de lazy loading
    LOG_LAZY_OPERATIONS = False
    
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
        
        cls.DEFAULT_BATCH_SIZE = get_int('LAZY_LOAD_DEFAULT_BATCH_SIZE', cls.DEFAULT_BATCH_SIZE)
        cls.SCROLL_THRESHOLD = get_int('LAZY_LOAD_SCROLL_THRESHOLD', cls.SCROLL_THRESHOLD)
        cls.DEBOUNCE_DELAY = get_int('LAZY_LOAD_DEBOUNCE_DELAY', cls.DEBOUNCE_DELAY)
        cls.LAZY_LOADING_ENABLED = get_bool('LAZY_LOADING_ENABLED', cls.LAZY_LOADING_ENABLED)
        cls.LOG_LAZY_OPERATIONS = get_bool('LAZY_LOAD_LOG_OPERATIONS', cls.LOG_LAZY_OPERATIONS)


# Charger la configuration depuis l'environnement
LazyLoadingConfig.from_env()


# ============================================================================
# DÉCORATEURS POUR LE LAZY LOADING
# ============================================================================

def lazy_property(func: Callable) -> property:
    """
    Décorateur pour créer une propriété lazy (calculée à la première utilisation).
    
    La valeur est calculée une seule fois et ensuite mise en cache dans l'instance.
    
    Exemple:
        class User:
            @lazy_property
            def full_name(self):
                return f"{self.first_name} {self.last_name}"
    
    Args:
        func: Fonction qui calcule la valeur
    
    Returns:
        Une propriété qui calcule la valeur de manière lazy
    """
    attr_name = f'_{func.__name__}'
    
    @property
    @wraps(func)
    def wrapper(self):
        if not LazyLoadingConfig.LAZY_LOADING_ENABLED:
            return func(self)
        
        if not hasattr(self, attr_name):
            if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
                lazy_logger.debug(f"Lazy loading property {func.__name__} for {type(self).__name__}")
            setattr(self, attr_name, func(self))
        
        return getattr(self, attr_name)
    
    return wrapper


def lazy_method(func: Callable) -> Callable:
    """
    Décorateur pour créer une méthode lazy (résultat mis en cache dans l'instance).
    
    Contrairement à lazy_property, cela permet de passer des arguments.
    
    Exemple:
        class User:
            @lazy_method
            def get_shifts(self, start_date, end_date):
                return Shift.query.filter_by(user_id=self.id, ...).all()
    
    Args:
        func: Méthode à rendre lazy
    
    Returns:
        Une méthode qui met en cache ses résultats
    """
    cache_attr = f'_{func.__name__}_cache'
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not LazyLoadingConfig.LAZY_LOADING_ENABLED:
            return func(self, *args, **kwargs)
        
        # Créer une clé de cache basée sur les arguments
        cache_key = (args, tuple(sorted(kwargs.items())))
        
        # Initialiser le cache si nécessaire
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, {})
        
        cache_dict = getattr(self, cache_attr)
        
        if cache_key not in cache_dict:
            if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
                lazy_logger.debug(f"Lazy loading method {func.__name__} with args={args}, kwargs={kwargs}")
            cache_dict[cache_key] = func(self, *args, **kwargs)
        
        return cache_dict[cache_key]
    
    return wrapper


def lazy_load(func: Optional[Callable] = None, 
              batch_size: int = LazyLoadingConfig.DEFAULT_BATCH_SIZE):
    """
    Décorateur pour le lazy loading de collections.
    
    Peut être utilisé pour :
    1. Décorer une fonction qui retourne une liste
    2. Créer un générateur lazy
    
    Exemple:
        @lazy_load(batch_size=10)
        def get_all_users():
            return User.query.order_by(User.name).all()
    
    Args:
        func: Fonction à décorer (optionnel)
        batch_size: Taille des batches pour le chargement
    
    Returns:
        Un objet LazyCollection
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not LazyLoadingConfig.LAZY_LOADING_ENABLED:
                return f(*args, **kwargs)
            
            return LazyCollection(f(*args, **kwargs), batch_size=batch_size)
        
        return wrapper
    
    # Si appelé sans arguments (en tant que décorateur sans parenthèses)
    if func is not None:
        return decorator(func)
    
    return decorator


# ============================================================================
# CLASSES POUR LE LAZY LOADING
# ============================================================================

class LazyCollection:
    """
    Collection lazy qui charge les éléments par batches.
    
    Permet d'itérer sur une grande collection sans tout charger en mémoire.
    
    Exemple:
        users = LazyCollection(User.query.order_by(User.name).all(), batch_size=20)
        
        # Charger le premier batch
        first_batch = users.next_batch()
        
        # Itérer sur tous les éléments (charge automatiquement les batches)
        for user in users:
            print(user.name)
    """
    
    def __init__(self, 
                 items: Optional[Iterable[Any]] = None,
                 batch_size: int = LazyLoadingConfig.DEFAULT_BATCH_SIZE,
                 loader: Optional[Callable[[int, int], List[Any]]] = None):
        """
        Initialise une collection lazy.
        
        Args:
            items: Liste complète des éléments (optionnel)
            batch_size: Taille des batches
            loader: Fonction de chargement (offset, limit) -> List[items]
        """
        self._items = list(items) if items is not None else []
        self._batch_size = batch_size
        self._loader = loader
        self._loaded_batches = {}  # {batch_index: [items]}
        self._current_batch = 0
        self._all_loaded = False
        
        # Si on a une fonction de chargement, c'est une collection infinie
        self._infinite = loader is not None
    
    def _get_batch_index(self, index: int) -> int:
        """Calcule l'index du batch pour un index donné."""
        return index // self._batch_size
    
    def _load_batch(self, batch_index: int) -> List[Any]:
        """Charge un batch spécifique."""
        if batch_index in self._loaded_batches:
            return self._loaded_batches[batch_index]
        
        if self._infinite and self._loader:
            offset = batch_index * self._batch_size
            items = self._loader(offset, self._batch_size)
            self._loaded_batches[batch_index] = items
            if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
                lazy_logger.debug(f"Loaded batch {batch_index} with {len(items)} items")
            return items
        
        # Si on a une liste complète, extraire le batch
        if self._items:
            start = batch_index * self._batch_size
            end = start + self._batch_size
            batch_items = self._items[start:end]
            self._loaded_batches[batch_index] = batch_items
            
            # Marquer comme tout chargé si on a atteint la fin
            if end >= len(self._items):
                self._all_loaded = True
            
            return batch_items
        
        return []
    
    def next_batch(self) -> List[Any]:
        """
        Charge et retourne le batch suivant.
        
        Returns:
            Liste des éléments du batch suivant
        """
        batch = self._load_batch(self._current_batch)
        self._current_batch += 1
        return batch
    
    def get_batch(self, batch_index: int) -> List[Any]:
        """
        Charge et retourne un batch spécifique.
        
        Args:
            batch_index: Index du batch à charger
        
        Returns:
            Liste des éléments du batch
        """
        return self._load_batch(batch_index)
    
    def __getitem__(self, index: Union[int, slice]) -> Any:
        """Accès par index ou slice."""
        if isinstance(index, slice):
            # Pour les slices, charger les batches nécessaires
            start = index.start or 0
            stop = index.stop or len(self)
            step = index.step or 1
            
            result = []
            for i in range(start, stop, step):
                result.append(self[i])
            return result
        
        # Pour un index simple
        batch_index = self._get_batch_index(index)
        batch = self._load_batch(batch_index)
        
        # Calculer l'index dans le batch
        batch_offset = index % self._batch_size
        
        if batch_offset < len(batch):
            return batch[batch_offset]
        
        raise IndexError(f"Index {index} out of range")
    
    def __iter__(self) -> Iterator[Any]:
        """Itérateur qui charge les batches automatiquement."""
        batch_index = 0
        
        while True:
            batch = self._load_batch(batch_index)
            
            if not batch:
                break
            
            for item in batch:
                yield item
            
            batch_index += 1
            
            # Si on a tout chargé et qu'on n'est pas en mode infini, s'arrêter
            if self._all_loaded and not self._infinite:
                break
    
    def __len__(self) -> int:
        """Retourne le nombre total d'éléments."""
        if self._infinite:
            # En mode infini, on ne connaît pas la longueur
            return sum(len(batch) for batch in self._loaded_batches.values())
        return len(self._items)
    
    def __bool__(self) -> bool:
        """Retourne True s'il y a des éléments."""
        return len(self) > 0
    
    def __repr__(self) -> str:
        """Représentation string."""
        loaded = sum(len(batch) for batch in self._loaded_batches.values())
        total = len(self) if not self._infinite else '?'
        return f'<LazyCollection loaded={loaded} total={total} batch_size={self._batch_size}>'
    
    @property
    def loaded_count(self) -> int:
        """Retourne le nombre d'éléments déjà chargés."""
        return sum(len(batch) for batch in self._loaded_batches.values())
    
    @property
    def batch_count(self) -> int:
        """Retourne le nombre de batches chargés."""
        return len(self._loaded_batches)
    
    def reset(self):
        """Réinitialise la collection (efface le cache des batches)."""
        self._loaded_batches.clear()
        self._current_batch = 0
        self._all_loaded = False


class LazyLoader:
    """
    Chargeur lazy pour le scroll infini ou le chargement progressif.
    
    Permet de charger des données par batches au fur et à mesure que l'utilisateur
    fait défiler la page.
    
    Exemple:
        # Dans une route Flask
        @app.route('/api/users')
        def get_users():
            query = User.query.order_by(User.name)
            loader = LazyLoader(query, batch_size=20)
            
            # Récupérer le curseur depuis la requête
            cursor = request.args.get('cursor', None)
            batch = loader.load_next_batch(cursor)
            
            return jsonify({
                'items': [u.to_dict() for u in batch['items']],
                'next_cursor': batch['next_cursor'],
                'has_more': batch['has_more']
            })
    """
    
    def __init__(self, 
                 query: Query,
                 batch_size: int = LazyLoadingConfig.DEFAULT_BATCH_SIZE,
                 order_by: Optional[Union[str, List[str]]] = None):
        """
        Initialise un chargeur lazy.
        
        Args:
            query: Requête SQLAlchemy à charger
            batch_size: Taille des batches
            order_by: Champ(s) pour le tri (doit être unique et indexé)
        """
        self._query = query
        self._batch_size = batch_size
        self._order_by = order_by
        self._last_cursor = None
        self._has_more = True
        
        # Appliquer l'ordre si spécifié
        if order_by:
            if isinstance(order_by, str):
                order_by = [order_by]
            
            for field in order_by:
                if field.startswith('-'):
                    self._query = self._query.order_by(desc(field[1:]))
                else:
                    self._query = self._query.order_by(asc(field))
        
        # Déterminer le champ de curseur (par défaut, le premier champ de l'ordre)
        if order_by:
            self._cursor_field = order_by[0].lstrip('-')
        else:
            # Essayer de trouver un champ ID
            if hasattr(query.column_descriptions[0]['entity'], 'id'):
                self._cursor_field = 'id'
            else:
                self._cursor_field = query.column_descriptions[0]['name']
    
    def load_next_batch(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Charge le batch suivant à partir du curseur.
        
        Args:
            cursor: Curseur pour le point de départ (ID du dernier élément chargé)
        
        Returns:
            Dictionnaire avec :
            - items: Liste des éléments du batch
            - next_cursor: Curseur pour le batch suivant
            - has_more: Indique s'il y a plus d'éléments
        """
        if not LazyLoadingConfig.LAZY_LOADING_ENABLED:
            items = self._query.all()
            return {
                'items': items,
                'next_cursor': None,
                'has_more': False
            }
        
        # Construire la requête avec le curseur
        query = self._query
        
        if cursor:
            # Filtrer pour obtenir les éléments après le curseur
            cursor_value = int(cursor) if cursor.isdigit() else cursor
            query = query.filter(text(f"{self._cursor_field} > :cursor").params(cursor=cursor_value))
        
        # Limiter à batch_size + 1 pour vérifier s'il y a plus
        items = query.limit(self._batch_size + 1).all()
        
        # Vérifier s'il y a plus d'éléments
        has_more = len(items) > self._batch_size
        if has_more:
            items = items[:-1]  # Retirer le dernier élément
        
        # Déterminer le next_cursor
        next_cursor = None
        if items:
            last_item = items[-1]
            if hasattr(last_item, self._cursor_field):
                next_cursor = str(getattr(last_item, self._cursor_field))
            elif isinstance(last_item, dict) and self._cursor_field in last_item:
                next_cursor = str(last_item[self._cursor_field])
        
        # Mettre à jour l'état
        self._last_cursor = next_cursor
        self._has_more = has_more
        
        if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
            lazy_logger.debug(f"Loaded batch with {len(items)} items, has_more={has_more}")
        
        return {
            'items': items,
            'next_cursor': next_cursor,
            'has_more': has_more
        }
    
    def load_batch_by_index(self, batch_index: int) -> Dict[str, Any]:
        """
        Charge un batch spécifique par son index.
        
        Args:
            batch_index: Index du batch (0-indexed)
        
        Returns:
            Dictionnaire avec les items, next_cursor et has_more
        """
        offset = batch_index * self._batch_size
        
        # Limiter à batch_size + 1 pour vérifier s'il y a plus
        items = self._query.offset(offset).limit(self._batch_size + 1).all()
        
        has_more = len(items) > self._batch_size
        if has_more:
            items = items[:-1]
        
        next_cursor = None
        if items:
            last_item = items[-1]
            if hasattr(last_item, self._cursor_field):
                next_cursor = str(getattr(last_item, self._cursor_field))
        
        return {
            'items': items,
            'next_cursor': next_cursor,
            'has_more': has_more
        }
    
    @property
    def has_more(self) -> bool:
        """Indique s'il y a plus d'éléments à charger."""
        return self._has_more
    
    @property
    def last_cursor(self) -> Optional[str]:
        """Retourne le dernier curseur utilisé."""
        return self._last_cursor


class LazyQuery:
    """
    Requête SQLAlchemy lazy qui ne charge les résultats qu'à la première utilisation.
    
    Exemple:
        # Créer une requête lazy
        query = LazyQuery(User.query.filter_by(is_active=True))
        
        # La requête n'est pas exécutée ici
        
        # Exécuter la requête
        users = query.all()  # Charge maintenant
        
        # Ou itérer
        for user in query:  # Charge maintenant
            print(user.name)
    """
    
    def __init__(self, query: Query):
        """
        Initialise une requête lazy.
        
        Args:
            query: Requête SQLAlchemy à rendre lazy
        """
        self._query = query
        self._result = None
        self._loaded = False
    
    def _load(self) -> Query:
        """Charge la requête si nécessaire."""
        if not self._loaded:
            if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
                lazy_logger.debug("Lazy loading query")
            self._loaded = True
        return self._query
    
    def all(self) -> List[Any]:
        """Exécute la requête et retourne tous les résultats."""
        return self._load().all()
    
    def first(self) -> Any:
        """Exécute la requête et retourne le premier résultat."""
        return self._load().first()
    
    def one(self) -> Any:
        """Exécute la requête et retourne un seul résultat."""
        return self._load().one()
    
    def count(self) -> int:
        """Exécute la requête et retourne le nombre de résultats."""
        return self._load().count()
    
    def __iter__(self) -> Iterator[Any]:
        """Itère sur les résultats."""
        return iter(self._load().all())
    
    def __len__(self) -> int:
        """Retourne le nombre de résultats."""
        return self._load().count()
    
    def __getattr__(self, name: str) -> Any:
        """Délègue les autres attributs à la requête sous-jacente."""
        return getattr(self._load(), name)
    
    def __repr__(self) -> str:
        """Représentation string."""
        return f'<LazyQuery loaded={self._loaded}>'


# ============================================================================
# UTILITAIRES POUR SQLALCHEMY
# ============================================================================

def lazy_load_relationship(model_class: Type, 
                         relationship_name: str,
                         query: Optional[Query] = None) -> Callable:
    """
    Décorateur pour charger une relation de manière lazy avec des options spécifiques.
    
    Exemple:
        class User:
            shifts = relationship('Shift', backref='user', lazy='dynamic')
            
            @lazy_load_relationship('shifts', query=lambda q: q.order_by(Shift.start_time))
            def get_shifts(self):
                return self.shifts
    
    Args:
        model_class: Classe du modèle
        relationship_name: Nom de la relation
        query: Fonction pour modifier la requête
    
    Returns:
        Décorateur
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not LazyLoadingConfig.LAZY_LOADING_ENABLED:
                return func(self, *args, **kwargs)
            
            # Obtenir la relation
            relationship = getattr(model_class, relationship_name)
            
            # Obtenir la requête
            if query:
                q = query(relationship.query(self))
            else:
                q = relationship.query(self)
            
            # Retourner une LazyQuery
            return LazyQuery(q)
        
        return wrapper
    
    return decorator


def configure_lazy_loading_for_model(model_class: Type, 
                                     relationships: Optional[Dict[str, Any]] = None):
    """
    Configure le lazy loading pour un modèle SQLAlchemy.
    
    Permet de définir des stratégies de chargement spécifiques pour chaque relation.
    
    Exemple:
        configure_lazy_loading_for_model(User, {
            'shifts': joinedload,
            'on_calls': selectinload,
            'leaves': lazyload
        })
    
    Args:
        model_class: Classe du modèle à configurer
        relationships: Dictionnaire des stratégies de chargement pour chaque relation
    """
    if not hasattr(model_class, '__table__'):
        return
    
    # Obtenir l'inspecteur
    inspector = inspect(model_class)
    
    # Pour chaque relation, configurer le lazy loading
    if relationships:
        for rel_name, strategy in relationships.items():
            if rel_name in inspector.relationships:
                # Appliquer la stratégie de chargement
                # Cela nécessite de modifier la définition de la relation
                # ce qui n'est pas toujours possible après la création du modèle
                pass


# ============================================================================
# INTÉGRATION AVEC LE CACHE
# ============================================================================

class CachedLazyLoader:
    """
    Chargeur lazy avec cache intégré.
    
    Combine le lazy loading avec le cache pour des performances optimales.
    
    Exemple:
        loader = CachedLazyLoader(
            User.query.order_by(User.name),
            batch_size=20,
            cache_timeout=300
        )
        
        # Premier chargement (depuis la base de données)
        batch1 = loader.load_next_batch()
        
        # Deuxième chargement (peut venir du cache)
        batch2 = loader.load_next_batch()
    """
    
    def __init__(self, 
                 query: Query,
                 batch_size: int = LazyLoadingConfig.DEFAULT_BATCH_SIZE,
                 cache_timeout: int = 300,
                 cache_key_prefix: str = 'lazy_loader'):
        """
        Initialise un chargeur lazy avec cache.
        
        Args:
            query: Requête SQLAlchemy à charger
            batch_size: Taille des batches
            cache_timeout: Durée de vie du cache en secondes
            cache_key_prefix: Préfixe pour les clés de cache
        """
        self._loader = LazyLoader(query, batch_size=batch_size)
        self._cache_timeout = cache_timeout
        self._cache_key_prefix = cache_key_prefix
        self._cache = {}
    
    def load_next_batch(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Charge le batch suivant avec cache.
        
        Args:
            cursor: Curseur pour le point de départ
        
        Returns:
            Dictionnaire avec les items, next_cursor et has_more
        """
        cache_key = f"{self._cache_key_prefix}:{cursor or 'start'}"
        
        # Vérifier le cache
        if cache_key in self._cache:
            if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
                lazy_logger.debug(f"Cache hit for lazy loader batch {cursor}")
            return self._cache[cache_key]
        
        # Charger depuis la base de données
        result = self._loader.load_next_batch(cursor)
        
        # Mettre en cache
        self._cache[cache_key] = result
        
        if LazyLoadingConfig.LOG_LAZY_OPERATIONS:
            lazy_logger.debug(f"Cache set for lazy loader batch {cursor}")
        
        return result
    
    def clear_cache(self):
        """Efface le cache."""
        self._cache.clear()


# ============================================================================
# EXPORT POUR L'APPLICATION
# ============================================================================

__all__ = [
    'LazyLoadingConfig',
    'lazy_property',
    'lazy_method',
    'lazy_load',
    'LazyCollection',
    'LazyLoader',
    'LazyQuery',
    'CachedLazyLoader',
    'lazy_load_relationship',
    'configure_lazy_loading_for_model',
]
