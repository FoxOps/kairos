"""
Gestionnaire de configuration pour l'automatisation.

Ce module permet de sauvegarder et charger la configuration de l'automatisation
(ordre de rotation des astreintes, règles personnalisées, etc.) dans un fichier JSON.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class AutomationConfig:
    """
    Classe pour gérer la configuration de l'automatisation.
    
    La configuration est stockée dans un fichier JSON dans le répertoire des données.
    """
    
    CONFIG_FILE = 'automation_config.json'
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Retourne le chemin du fichier de configuration."""
        # Utiliser le répertoire de l'application
        app_dir = Path(__file__).parent.parent.parent
        config_dir = app_dir / 'data'
        config_dir.mkdir(exist_ok=True)
        return config_dir / cls.CONFIG_FILE
    
    @classmethod
    def load(cls) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier.
        
        Returns:
            Dictionnaire de configuration (vide si le fichier n'existe pas)
        """
        config_path = cls.get_config_path()
        
        if not config_path.exists():
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # Si le fichier est corrompu, retourner une config vide
            print(f"Warning: Could not load automation config: {e}")
            return {}
    
    @classmethod
    def save(cls, config: Dict[str, Any]) -> bool:
        """
        Sauvegarde la configuration dans le fichier.
        
        Args:
            config: Dictionnaire de configuration à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        config_path = cls.get_config_path()
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error: Could not save automation config: {e}")
            return False
    
    @classmethod
    def save_rotation_order(cls, rotation_order: list) -> bool:
        """
        Sauvegarde l'ordre de rotation des astreintes.
        
        Args:
            rotation_order: Liste des IDs d'utilisateurs dans l'ordre de rotation
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        config = cls.load()
        if 'oncall' not in config:
            config['oncall'] = {}
        config['oncall']['rotation_order'] = rotation_order
        return cls.save(config)
    
    @classmethod
    def get_rotation_order(cls) -> Optional[list]:
        """
        Récupère l'ordre de rotation des astreintes.
        
        Returns:
            Liste des IDs d'utilisateurs, ou None si non configuré
        """
        config = cls.load()
        return config.get('oncall', {}).get('rotation_order')
