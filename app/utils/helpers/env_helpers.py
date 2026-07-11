"""
Module utilitaire pour la gestion des variables d'environnement.

Ce module centralise les fonctions de conversion des variables d'environnement
pour éviter la duplication de code.
"""

import json
import logging
import os


def get_bool(env_var, default=False):
    """
    Convertit une variable d'environnement en booléen.
    
    Accepte: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
    
    Args:
        env_var: Nom de la variable d'environnement
        default: Valeur par défaut si la variable n'est pas définie
        
    Returns:
        bool: Valeur booléenne de la variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    value_lower = value.lower().strip()
    if value_lower in ('true', '1', 'yes', 'y', 'on'):
        return True
    elif value_lower in ('false', '0', 'no', 'n', 'off'):
        return False
    else:
        # Pour la compatibilité ascendante, retourner la valeur par défaut
        if value_lower:
            logging.warning(f"Valeur non reconnue pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


def get_int(env_var, default=0):
    """
    Convertit une variable d'environnement en entier.
    
    Args:
        env_var: Nom de la variable d'environnement
        default: Valeur par défaut si la variable n'est pas définie ou invalide
        
    Returns:
        int: Valeur entière de la variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    try:
        return int(value.strip())
    except ValueError:
        logging.warning(f"Valeur non entière pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


def get_float(env_var, default=0.0):
    """
    Convertit une variable d'environnement en nombre à virgule flottante.
    
    Args:
        env_var: Nom de la variable d'environnement
        default: Valeur par défaut si la variable n'est pas définie ou invalide
        
    Returns:
        float: Valeur flottante de la variable
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    try:
        return float(value.strip())
    except ValueError:
        logging.warning(f"Valeur non flottante pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


def get_json(env_var, default=None):
    """
    Convertit une variable d'environnement en objet Python via JSON.
    
    Args:
        env_var: Nom de la variable d'environnement
        default: Valeur par défaut si la variable n'est pas définie ou JSON invalide
        
    Returns:
        any: Objet Python décodé depuis JSON
    """
    value = os.environ.get(env_var)
    if value is None or value.strip() == '':
        return default
    
    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        logging.warning(f"Valeur JSON invalide pour {env_var}: '{value}'. Utilisation de la valeur par défaut")
        return default


def get_list(env_var, separator=',', default=None):
    """
    Convertit une variable d'environnement en liste.
    
    Args:
        env_var: Nom de la variable d'environnement
        separator: Séparateur pour les éléments de la liste (par défaut: ',')
        default: Valeur par défaut si la variable n'est pas définie
        
    Returns:
        list: Liste des valeurs
    """
    value = os.environ.get(env_var)
    if value is None or value.strip() == '':
        return default or []
    
    return [item.strip() for item in value.split(separator) if item.strip()]
