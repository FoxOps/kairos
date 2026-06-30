"""
Module utilitaire pour la génération de clés de cache.

Ce module centralise les fonctions de génération de clés de cache
pour éviter la duplication de code entre cache.py et optimizations.py.
"""

import hashlib
from typing import Callable, Optional, List, Tuple, Any

from flask import current_app, request
from flask_login import current_user


def make_cache_key(
    f: Callable,
    args: Tuple = (),
    kwargs: dict = None,
    key_prefix: str = '',
    vary_on: Optional[List[str]] = None,
    include_user: bool = True
) -> str:
    """
    Génère une clé de cache unique pour une fonction et ses arguments.
    
    Cette fonction unifiée remplace les implémentations dupliquées dans
    cache.py et optimizations.py.
    
    Args:
        f: Fonction pour laquelle générer la clé
        args: Arguments positionnels de la fonction
        kwargs: Arguments nommés de la fonction
        key_prefix: Préfixe à ajouter à la clé
        vary_on: Liste des noms d'arguments à inclure dans la clé
        include_user: Inclure l'ID de l'utilisateur dans la clé si connecté
        
    Returns:
        str: Clé de cache unique (hash SHA-256)
    """
    if kwargs is None:
        kwargs = {}
    
    # Base de la clé
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
                # Pour les arguments positionnels
                key_parts.extend(str(arg) for arg in args)
                break
    else:
        # Utiliser tous les arguments
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    # Ajouter l'ID de l'utilisateur si connecté
    if include_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        key_parts.append(f"user_id={current_user.id}")
    
    # Créer un hash de la clé pour éviter les clés trop longues
    # Note: SHA-256 est utilisé au lieu de MD5 pour des raisons de sécurité et de bonnes pratiques
    # Ce hash n'est pas utilisé pour la sécurité, mais pour générer des clés de cache uniques
    key_string = ':'.join(key_parts)
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()


def make_route_cache_key(
    f: Callable,
    request_obj: Any = None,
    key_prefix: str = '',
    vary_on: Optional[List[str]] = None
) -> str:
    """
    Génère une clé de cache pour une route Flask.
    
    Args:
        f: Fonction route pour laquelle générer la clé
        request_obj: Objet request Flask (par défaut: request global)
        key_prefix: Préfixe à ajouter à la clé
        vary_on: Liste des paramètres de requête à inclure dans la clé
        
    Returns:
        str: Clé de cache unique (hash SHA-256)
    """
    if request_obj is None:
        request_obj = request
    
    # Base de la clé
    key_parts = [f.__module__, f.__name__, request_obj.path]
    
    # Ajouter le préfixe
    if key_prefix:
        key_parts.insert(0, key_prefix)
    
    # Ajouter la méthode HTTP
    key_parts.append(request_obj.method)
    
    # Ajouter les paramètres de requête
    if vary_on:
        for param in vary_on:
            value = request_obj.args.get(param, '')
            key_parts.append(f"{param}={value}")
    else:
        # Utiliser tous les paramètres
        for key, value in request_obj.args.items():
            key_parts.append(f"{key}={value}")
    
    # Ajouter l'ID de l'utilisateur si connecté
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        key_parts.append(f"user_id={current_user.id}")
    
    # Créer un hash
    key_string = ':'.join(key_parts)
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
