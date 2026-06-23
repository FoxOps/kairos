"""
Module de pagination avancée pour Leviia Schedule.

Ce module fournit des outils pour une pagination efficace et configurable,
avec support pour :
- Pagination standard (offset/limit)
- Pagination par curseur (keyset pagination)
- Pagination infinie (pour le lazy loading)
- Paramètres configurables via l'URL
- Cache des résultats paginés

Utilisation :
    from app.utils.pagination import Pagination, PaginationConfig, paginate_query
    
    # Pagination standard
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query.order_by(User.name)
    paginated = paginate_query(query, page=page, per_page=per_page)
    
    # Dans le template
    {% for item in paginated.items %}
        {{ item.name }}
    {% endfor %}
    
    {{ paginated.pagination_links() }}
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from flask import Flask, request, url_for
from sqlalchemy.orm import Query
from sqlalchemy import asc, desc, text
import math
import json


# ============================================================================
# CONFIGURATION DE LA PAGINATION
# ============================================================================

class PaginationConfig:
    """
    Configuration de la pagination.
    
    Peut être configurée via variables d'environnement ou directement.
    """
    
    # Paramètres par défaut
    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100
    PER_PAGE_OPTIONS = [5, 10, 20, 50, 100]
    
    # Paramètres pour la pagination par curseur
    CURSOR_PAGE_SIZE = 20
    
    # Paramètres pour le lazy loading
    LAZY_LOAD_THRESHOLD = 100  # Nombre d'éléments avant de charger plus
    LAZY_LOAD_BATCH_SIZE = 20
    
    # Activer/désactiver la pagination (utile pour le développement)
    PAGINATION_ENABLED = True
    
    # Style des liens de pagination
    PAGINATION_STYLE = 'bulma'  # 'bulma', 'simple', 'none'
    
    # Nombre de pages à afficher autour de la page courante
    PAGINATION_WINDOW = 2
    
    @classmethod
    def from_env(cls):
        """Charge la configuration depuis les variables d'environnement."""
        import os
        
        def get_int(env_var, default=0):
            value = os.environ.get(env_var, '')
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        def get_list(env_var, default=None):
            value = os.environ.get(env_var, '')
            if not value:
                return default
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Essayer de parser comme une liste séparée par des virgules
                return [int(x.strip()) for x in value.split(',') if x.strip().isdigit()]
        
        cls.DEFAULT_PER_PAGE = get_int('PAGINATION_DEFAULT_PER_PAGE', cls.DEFAULT_PER_PAGE)
        cls.MAX_PER_PAGE = get_int('PAGINATION_MAX_PER_PAGE', cls.MAX_PER_PAGE)
        cls.PER_PAGE_OPTIONS = get_list('PAGINATION_PER_PAGE_OPTIONS', cls.PER_PAGE_OPTIONS)
        cls.CURSOR_PAGE_SIZE = get_int('PAGINATION_CURSOR_PAGE_SIZE', cls.CURSOR_PAGE_SIZE)
        cls.LAZY_LOAD_THRESHOLD = get_int('PAGINATION_LAZY_LOAD_THRESHOLD', cls.LAZY_LOAD_THRESHOLD)
        cls.LAZY_LOAD_BATCH_SIZE = get_int('PAGINATION_LAZY_LOAD_BATCH_SIZE', cls.LAZY_LOAD_BATCH_SIZE)
        cls.PAGINATION_WINDOW = get_int('PAGINATION_WINDOW', cls.PAGINATION_WINDOW)
        cls.PAGINATION_STYLE = os.environ.get('PAGINATION_STYLE', cls.PAGINATION_STYLE)


# Charger la configuration depuis l'environnement
PaginationConfig.from_env()


# ============================================================================
# CLASSE DE PAGINATION
# ============================================================================

class Pagination:
    """
    Classe de pagination pour gérer les résultats paginés.
    
    Compatible avec SQLAlchemy Query et les listes Python.
    """
    
    def __init__(self, 
                 items: List[Any], 
                 page: int = 1, 
                 per_page: int = PaginationConfig.DEFAULT_PER_PAGE,
                 total: int = 0,
                 query: Optional[Query] = None,
                 endpoint: Optional[str] = None,
                 args: Optional[Dict] = None,
                 cursor: Optional[str] = None,
                 has_next: bool = False,
                 has_previous: bool = False):
        """
        Initialise une instance de pagination.
        
        Args:
            items: Liste des éléments de la page courante
            page: Numéro de la page courante (1-indexed)
            per_page: Nombre d'éléments par page
            total: Nombre total d'éléments
            query: Requête SQLAlchemy originale (optionnel)
            endpoint: Endpoint Flask pour générer les URLs
            args: Arguments supplémentaires pour les URLs
            cursor: Curseur pour la pagination par curseur
            has_next: Indique s'il y a une page suivante
            has_previous: Indique s'il y a une page précédente
        """
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.query = query
        self.endpoint = endpoint
        self.args = args or {}
        self.cursor = cursor
        self.has_next = has_next
        self.has_previous = has_previous
        
        # Calculer les propriétés dérivées
        self.pages = self._calculate_pages()
        self.first_item = (page - 1) * per_page + 1 if items else 0
        self.last_item = self.first_item + len(items) - 1 if items else 0
        
        # Stocker la configuration
        self.config = PaginationConfig
    
    def _calculate_pages(self) -> int:
        """Calcule le nombre total de pages."""
        if self.total == 0:
            return 0
        return math.ceil(self.total / self.per_page) if self.per_page > 0 else 1
    
    @property
    def next_page(self) -> Optional[int]:
        """Retourne le numéro de la page suivante, ou None s'il n'y en a pas."""
        if self.has_next:
            return self.page + 1
        return None
    
    @property
    def previous_page(self) -> Optional[int]:
        """Retourne le numéro de la page précédente, ou None s'il n'y en a pas."""
        if self.has_previous:
            return self.page - 1
        return None
    
    @property
    def next_cursor(self) -> Optional[str]:
        """Retourne le curseur pour la page suivante (pagination par curseur)."""
        if self.has_next and self.items:
            # Pour la pagination par curseur, utiliser l'ID du dernier élément
            last_item = self.items[-1]
            if hasattr(last_item, 'id'):
                return str(last_item.id)
            elif isinstance(last_item, dict) and 'id' in last_item:
                return str(last_item['id'])
        return None
    
    @property
    def previous_cursor(self) -> Optional[str]:
        """Retourne le curseur pour la page précédente (pagination par curseur)."""
        if self.has_previous and self.items:
            # Pour la pagination par curseur, utiliser l'ID du premier élément
            first_item = self.items[0]
            if hasattr(first_item, 'id'):
                return str(first_item.id)
            elif isinstance(first_item, dict) and 'id' in first_item:
                return str(first_item['id'])
        return None
    
    def pagination_links(self, style: Optional[str] = None) -> str:
        """
        Génère les liens de pagination HTML.
        
        Args:
            style: Style des liens ('bulma', 'simple', 'none')
        
        Returns:
            HTML des liens de pagination
        """
        style = style or self.config.PAGINATION_STYLE
        
        if style == 'none':
            return ''
        
        if style == 'bulma':
            return self._bulma_pagination()
        else:
            return self._simple_pagination()
    
    def _bulma_pagination(self) -> str:
        """Génère les liens de pagination au format Bulma."""
        if self.pages <= 1:
            return ''
        
        window = self.config.PAGINATION_WINDOW
        current = self.page
        total_pages = self.pages
        
        # Calculer la plage de pages à afficher
        start_page = max(1, current - window)
        end_page = min(total_pages, current + window)
        
        # Ajuster si on est au début ou à la fin
        if current - start_page < window and end_page - start_page < 2 * window:
            end_page = min(total_pages, start_page + 2 * window)
        if end_page - current < window and end_page - start_page < 2 * window:
            start_page = max(1, end_page - 2 * window)
        
        links = []
        
        # Lien vers la première page
        if current > 1:
            links.append(self._create_link(1, '«', 'first'))
        else:
            links.append('<a class="pagination-previous is-disabled" aria-label="Première page"><span>«</span></a>')
        
        # Lien vers la page précédente
        if self.has_previous:
            links.append(self._create_link(current - 1, '‹', 'previous'))
        else:
            links.append('<a class="pagination-previous is-disabled" aria-label="Page précédente"><span>‹</span></a>')
        
        # Pages
        if start_page > 1:
            links.append('<span class="pagination-ellipsis">…</span>')
        
        for page in range(start_page, end_page + 1):
            if page == current:
                links.append(f'<a class="pagination-link is-current" aria-label="Page {page}" aria-current="page">{page}</a>')
            else:
                links.append(self._create_link(page, str(page)))
        
        if end_page < total_pages:
            links.append('<span class="pagination-ellipsis">…</span>')
        
        # Lien vers la page suivante
        if self.has_next:
            links.append(self._create_link(current + 1, '›', 'next'))
        else:
            links.append('<a class="pagination-next is-disabled" aria-label="Page suivante"><span>›</span></a>')
        
        # Lien vers la dernière page
        if current < total_pages:
            links.append(self._create_link(total_pages, '»', 'last'))
        else:
            links.append('<a class="pagination-next is-disabled" aria-label="Dernière page"><span>»</span></a>')
        
        return f'<nav class="pagination is-centered" role="navigation" aria-label="pagination">{ " ".join(links) }</nav>'
    
    def _simple_pagination(self) -> str:
        """Génère les liens de pagination au format simple."""
        if self.pages <= 1:
            return ''
        
        links = []
        
        # Lien vers la page précédente
        if self.has_previous:
            links.append(self._create_link(self.page - 1, 'Previous'))
        
        # Numéros de page
        for page in range(1, self.pages + 1):
            if page == self.page:
                links.append(f'<strong>{page}</strong>')
            else:
                links.append(self._create_link(page, str(page)))
        
        # Lien vers la page suivante
        if self.has_next:
            links.append(self._create_link(self.page + 1, 'Next'))
        
        return ' | '.join(links)
    
    def _create_link(self, page: int, text: str, rel: Optional[str] = None) -> str:
        """Crée un lien de pagination compatible avec Bulma."""
        if not self.endpoint:
            return f'<span>{text}</span>'
        
        # Copier les arguments et mettre à jour la page
        args = self.args.copy()
        args['page'] = page
        
        # Supprimer les arguments de pagination existants
        args.pop('per_page', None)
        args.pop('cursor', None)
        
        url = url_for(self.endpoint, **args)
        
        # Pour Bulma, utiliser des classes spécifiques
        if rel == 'first':
            return f'<a class="pagination-previous" href="{url}" aria-label="Première page">{text}</a>'
        elif rel == 'previous':
            return f'<a class="pagination-previous" href="{url}" aria-label="Page précédente">{text}</a>'
        elif rel == 'next':
            return f'<a class="pagination-next" href="{url}" aria-label="Page suivante">{text}</a>'
        elif rel == 'last':
            return f'<a class="pagination-next" href="{url}" aria-label="Dernière page">{text}</a>'
        else:
            return f'<a class="pagination-link" href="{url}" aria-label="Page {page}">{text}</a>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la pagination en dictionnaire (pour les APIs JSON)."""
        return {
            'items': [self._serialize_item(item) for item in self.items],
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'pages': self.pages,
            'has_next': self.has_next,
            'has_previous': self.has_previous,
            'next_page': self.next_page,
            'previous_page': self.previous_page,
            'first_item': self.first_item,
            'last_item': self.last_item,
        }
    
    def _serialize_item(self, item: Any) -> Any:
        """Sérialise un élément pour le JSON."""
        if hasattr(item, 'to_dict'):
            return item.to_dict()
        elif hasattr(item, '__dict__'):
            # Exclure les attributs SQLAlchemy
            return {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
        elif isinstance(item, dict):
            return item
        else:
            return str(item)
    
    def __iter__(self):
        """Permet d'itérer directement sur les items."""
        return iter(self.items)
    
    def __len__(self):
        """Retourne le nombre d'items dans la page courante."""
        return len(self.items)
    
    def __bool__(self):
        """Retourne True s'il y a des items."""
        return bool(self.items)
    
    def __repr__(self):
        """Représentation string de la pagination."""
        return f'<Pagination page={self.page} per_page={self.per_page} total={self.total} items={len(self.items)}>'


# ============================================================================
# FONCTIONS DE PAGINATION
# ============================================================================

def get_pagination_parameters() -> Tuple[int, int, Optional[str]]:
    """
    Récupère les paramètres de pagination depuis la requête Flask.
    
    Returns:
        Tuple de (page, per_page, cursor)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', PaginationConfig.DEFAULT_PER_PAGE, type=int)
    cursor = request.args.get('cursor', None)
    
    # Valider per_page
    per_page = max(1, min(per_page, PaginationConfig.MAX_PER_PAGE))
    
    # Valider page
    page = max(1, page)
    
    return page, per_page, cursor


def paginate_query(query: Query, 
                   page: int = 1, 
                   per_page: int = PaginationConfig.DEFAULT_PER_PAGE,
                   endpoint: Optional[str] = None,
                   args: Optional[Dict] = None,
                   error_out: bool = True,
                   max_per_page: Optional[int] = None,
                   count: bool = True) -> Pagination:
    """
    Pagine une requête SQLAlchemy.
    
    Args:
        query: Requête SQLAlchemy à paginer
        page: Numéro de la page (1-indexed)
        per_page: Nombre d'éléments par page
        endpoint: Endpoint Flask pour générer les URLs
        args: Arguments supplémentaires pour les URLs
        error_out: Lever une exception 404 si la page n'existe pas
        max_per_page: Nombre maximum d'éléments par page
        count: Compter le nombre total d'éléments
    
    Returns:
        Objet Pagination avec les résultats
    """
    if not PaginationConfig.PAGINATION_ENABLED:
        # Désactivé, retourner tous les résultats
        items = query.all()
        return Pagination(
            items=items,
            page=1,
            per_page=len(items),
            total=len(items),
            endpoint=endpoint,
            args=args
        )
    
    # Valider per_page
    max_per_page = max_per_page or PaginationConfig.MAX_PER_PAGE
    per_page = max(1, min(per_page, max_per_page))
    
    # Valider page
    page = max(1, page)
    
    # Compter le nombre total d'éléments
    total = query.count() if count else 0
    
    # Calculer l'offset
    offset = (page - 1) * per_page
    
    # Exécuter la requête avec limit et offset
    items = query.offset(offset).limit(per_page).all()
    
    # Vérifier si la page existe
    if error_out and page > 1 and offset >= total:
        from werkzeug.exceptions import NotFound
        raise NotFound()
    
    # Calculer has_next et has_previous
    has_previous = page > 1
    has_next = offset + len(items) < total
    
    return Pagination(
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        query=query,
        endpoint=endpoint,
        args=args,
        has_next=has_next,
        has_previous=has_previous
    )


def paginate_cursor(query: Query,
                    cursor: Optional[str] = None,
                    page_size: int = PaginationConfig.CURSOR_PAGE_SIZE,
                    order_by: Optional[Union[str, List]] = None,
                    endpoint: Optional[str] = None,
                    args: Optional[Dict] = None) -> Pagination:
    """
    Pagine une requête SQLAlchemy en utilisant la pagination par curseur.
    
    Plus efficace que la pagination offset/limit pour les grandes tables.
    
    Args:
        query: Requête SQLAlchemy à paginer
        cursor: Curseur pour la page courante (ID du dernier élément de la page précédente)
        page_size: Nombre d'éléments par page
        order_by: Champ(s) pour le tri (doit être unique et indexé)
        endpoint: Endpoint Flask pour générer les URLs
        args: Arguments supplémentaires pour les URLs
    
    Returns:
        Objet Pagination avec les résultats
    """
    if not PaginationConfig.PAGINATION_ENABLED:
        items = query.all()
        return Pagination(
            items=items,
            page=1,
            per_page=len(items),
            total=len(items),
            endpoint=endpoint,
            args=args
        )
    
    # Définir l'ordre par défaut
    if order_by is None:
        # Essayer de trouver un champ ID
        if hasattr(query.column_descriptions[0]['entity'], 'id'):
            order_by = 'id'
        else:
            order_by = query.column_descriptions[0]['name']
    
    if isinstance(order_by, str):
        order_by = [order_by]
    
    # Construire la requête avec order_by
    ordered_query = query
    for field in order_by:
        if field.startswith('-'):
            ordered_query = ordered_query.order_by(desc(text(field[1:])))
        else:
            ordered_query = ordered_query.order_by(asc(text(field)))
    
    # Appliquer le curseur
    if cursor:
        # Le curseur contient l'ID du dernier élément de la page précédente
        # On veut les éléments avec ID > cursor
        cursor_value = int(cursor) if cursor.isdigit() else cursor
        ordered_query = ordered_query.filter(text(f"{order_by[0]} > :cursor").params(cursor=cursor_value))
    
    # Limiter la taille de la page + 1 (pour vérifier s'il y a une page suivante)
    items = ordered_query.limit(page_size + 1).all()
    
    # Vérifier s'il y a une page suivante
    has_next = len(items) > page_size
    if has_next:
        items = items[:-1]  # Retirer le dernier élément
    
    # Calculer has_previous (il y a une page précédente si cursor est défini)
    has_previous = cursor is not None
    
    # Calculer le numéro de page (approximatif)
    # Pour la pagination par curseur, le numéro de page n'est pas toujours précis
    page = 1
    if cursor:
        # Estimer la page en fonction du curseur
        # Cela nécessite de connaître le nombre total, ce qui n'est pas efficace
        # Donc on retourne simplement page=1 pour la pagination par curseur
        pass
    
    return Pagination(
        items=items,
        page=page,
        per_page=page_size,
        total=0,  # On ne connaît pas le total avec la pagination par curseur
        query=query,
        endpoint=endpoint,
        args=args,
        cursor=cursor,
        has_next=has_next,
        has_previous=has_previous
    )


def paginate_lazy(items: List[Any],
                  batch_size: int = PaginationConfig.LAZY_LOAD_BATCH_SIZE,
                  threshold: int = PaginationConfig.LAZY_LOAD_THRESHOLD,
                  page: int = 1) -> Pagination:
    """
    Crée une pagination pour le lazy loading.
    
    Args:
        items: Liste complète des éléments (ou un sous-ensemble)
        batch_size: Nombre d'éléments à charger par batch
        threshold: Nombre d'éléments avant de déclencher le chargement
        page: Numéro de la page courante
    
    Returns:
        Objet Pagination configuré pour le lazy loading
    """
    # Calculer l'offset
    offset = (page - 1) * batch_size
    
    # Extraire les éléments de la page courante
    page_items = items[offset:offset + batch_size]
    
    # Calculer has_next et has_previous
    has_previous = page > 1
    has_next = offset + len(page_items) < len(items)
    
    return Pagination(
        items=page_items,
        page=page,
        per_page=batch_size,
        total=len(items),
        has_next=has_next,
        has_previous=has_previous
    )


# ============================================================================
# DÉCORATEURS DE PAGINATION
# ============================================================================

def paginated(endpoint: Optional[str] = None,
              per_page: int = PaginationConfig.DEFAULT_PER_PAGE,
              max_per_page: Optional[int] = None,
              count: bool = True):
    """
    Décorateur pour paginer automatiquement les résultats d'une route.
    
    Exemple:
        @app.route('/users')
        @paginated(endpoint='users', per_page=20)
        def list_users():
            query = User.query.order_by(User.name)
            return query
    """
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            from flask import request
            
            # Récupérer les paramètres de pagination
            page = request.args.get('page', 1, type=int)
            per_page_param = request.args.get('per_page', per_page, type=int)
            
            # Valider per_page
            max_per_page = max_per_page or PaginationConfig.MAX_PER_PAGE
            per_page = max(1, min(per_page_param, max_per_page))
            
            # Appeler la fonction pour obtenir la requête
            result = f(*args, **kwargs)
            
            # Si c'est une requête SQLAlchemy, la paginer
            if isinstance(result, Query):
                return paginate_query(
                    result,
                    page=page,
                    per_page=per_page,
                    endpoint=endpoint,
                    args=request.args.to_dict(),
                    count=count
                )
            
            # Si c'est une liste, créer une pagination simple
            if isinstance(result, list):
                total = len(result)
                offset = (page - 1) * per_page
                items = result[offset:offset + per_page]
                
                return Pagination(
                    items=items,
                    page=page,
                    per_page=per_page,
                    total=total,
                    endpoint=endpoint,
                    args=request.args.to_dict()
                )
            
            return result
        
        return wrapped
    
    return decorator


# ============================================================================
# UTILITAIRES DE PAGINATION
# ============================================================================

class PaginationHelper:
    """Classe utilitaire pour la pagination."""
    
    @staticmethod
    def get_per_page_options() -> List[int]:
        """Retourne les options de pagination disponibles."""
        return PaginationConfig.PER_PAGE_OPTIONS
    
    @staticmethod
    def validate_per_page(per_page: int) -> int:
        """Valide et normalise le paramètre per_page."""
        per_page = max(1, per_page)
        per_page = min(per_page, PaginationConfig.MAX_PER_PAGE)
        return per_page
    
    @staticmethod
    def get_pagination_info(pagination: Pagination) -> Dict[str, Any]:
        """Retourne les informations de pagination pour l'API."""
        return {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_previous': pagination.has_previous,
            'next_page': pagination.next_page,
            'previous_page': pagination.previous_page,
            'first_item': pagination.first_item,
            'last_item': pagination.last_item,
        }
    
    @staticmethod
    def create_pagination_links(pagination: Pagination, 
                               style: str = 'bulma') -> str:
        """Crée les liens de pagination."""
        return pagination.pagination_links(style=style)


# ============================================================================
# EXPORT POUR L'APPLICATION
# ============================================================================

# Exporter les classes et fonctions principales
__all__ = [
    'Pagination',
    'PaginationConfig',
    'PaginationHelper',
    'paginate_query',
    'paginate_cursor',
    'paginate_lazy',
    'paginated',
    'get_pagination_parameters',
]
