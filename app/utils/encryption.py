"""
Module utilitaire pour le chiffrement des données sensibles.

Ce module fournit des fonctions pour chiffrer et déchiffrer les données
sensibles comme les tokens ICS.
"""

import base64
import os
from cryptography.fernet import Fernet

# Générer ou charger une clé de chiffrement
# En production, cette clé devrait être stockée dans une variable d'environnement
_ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

if _ENCRYPTION_KEY is None:
    # Générer une clé par défaut (pour le développement uniquement)
    # En production, toujours définir ENCRYPTION_KEY dans les variables d'environnement
    _ENCRYPTION_KEY = Fernet.generate_key().decode()

# Créer un objet Fernet pour le chiffrement
_cipher_suite = Fernet(_ENCRYPTION_KEY.encode())


def encrypt_data(data: str) -> str:
    """
    Chiffre une chaîne de caractères.
    
    Args:
        data: Donnée à chiffrer
        
    Returns:
        str: Donnée chiffrée (encodée en base64)
    """
    if not data:
        return ""
    encrypted = _cipher_suite.encrypt(data.encode())
    return encrypted.decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Déchiffre une chaîne de caractères.
    
    Args:
        encrypted_data: Donnée chiffrée (encodée en base64)
        
    Returns:
        str: Donnée déchiffrée
        
    Raises:
        ValueError: Si la donnée ne peut pas être déchiffrée
    """
    if not encrypted_data:
        return ""
    try:
        decrypted = _cipher_suite.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Impossible de déchiffrer les données: {e}")


def get_encryption_key() -> str:
    """
    Retourne la clé de chiffrement actuelle.
    
    Returns:
        str: Clé de chiffrement (encodée en base64)
    """
    return _ENCRYPTION_KEY


def rotate_encryption_key() -> str:
    """
    Génère une nouvelle clé de chiffrement.
    
    ATTENTION: Cela invalidera toutes les données chiffrées avec l'ancienne clé.
    
    Returns:
        str: Nouvelle clé de chiffrement
    """
    global _ENCRYPTION_KEY, _cipher_suite
    _ENCRYPTION_KEY = Fernet.generate_key().decode()
    _cipher_suite = Fernet(_ENCRYPTION_KEY.encode())
    return _ENCRYPTION_KEY
