import os
import json
import logging
from datetime import timedelta
import secrets

# Charger les variables d'environnement depuis un fichier .env si présent
# Cela permet une configuration facile sans modifier le code
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv n'est pas installé, on utilise uniquement les variables d'environnement système
    pass


# Fonction utilitaire pour convertir les valeurs booléennes depuis les variables d'environnement
def get_bool_from_env(env_var, default=False):
    """Convertit une variable d'environnement en booléen.
    
    Accepte: true, True, TRUE, 1, yes, Yes, YES, false, False, FALSE, 0, no, No, NO
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
        # mais logger un avertissement si la valeur n'est pas reconnue
        if value_lower:
            logging.warning(f"Valeur non reconnue pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


# Fonction utilitaire pour obtenir une valeur entière depuis les variables d'environnement
def get_int_from_env(env_var, default=0):
    """Convertit une variable d'environnement en entier."""
    value = os.environ.get(env_var)
    if value is None:
        return default
    
    try:
        return int(value.strip())
    except ValueError:
        logging.warning(f"Valeur non entière pour {env_var}: '{value}'. Utilisation de la valeur par défaut: {default}")
        return default


# Fonction utilitaire pour obtenir une valeur JSON depuis les variables d'environnement
def get_str_from_env(env_var, default=''):
    """Convertit une variable d'environnement en string."""
    value = os.environ.get(env_var)
    if value is None or value.strip() == '':
        return default
    return value.strip()


def get_json_from_env(env_var, default=None):
    """Convertit une variable d'environnement en objet Python via JSON."""
    value = os.environ.get(env_var)
    if value is None or value.strip() == '':
        return default
    
    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        logging.warning(f"Valeur JSON invalide pour {env_var}: '{value}'. Utilisation de la valeur par défaut")
        return default


# Fonction utilitaire pour détecter le type de base de données
# Doit être définie avant la classe Config pour éviter les problèmes de référence circulaire
def get_database_type(database_uri=None):
    """Détecte le type de base de données à partir de l'URI."""
    if database_uri is None:
        database_uri = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    
    if database_uri.startswith("postgresql://") or database_uri.startswith("postgres://"):
        return "postgresql"
    elif database_uri.startswith("mysql://") or database_uri.startswith("mariadb://"):
        return "mysql"
    elif database_uri.startswith("sqlite://"):
        return "sqlite"
    else:
        # Par défaut, on suppose SQLite
        return "sqlite"


# Configuration de base pour Flask
class Config:
    # Clé secrète pour Flask (OBLIGATOIRE en production)
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
    
    # URI de la base de données - peut être configurée via DATABASE_URL
    # SQLite reste la base de données par défaut
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = get_bool_from_env("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    
    # ✅ Configuration pour que Flask écoute sur 0.0.0.0:5000
    HOST = os.environ.get("FLASK_HOST") or "0.0.0.0"
    PORT = int(os.environ.get("FLASK_PORT") or 5000)
    
    # Détecter le type de base de données à partir de l'URI
    @staticmethod
    def get_database_type(database_uri=None):
        """Détecte le type de base de données à partir de l'URI."""
        return get_database_type(database_uri or Config.SQLALCHEMY_DATABASE_URI)
    
    # Configuration des options du moteur SQLAlchemy selon le type de base de données
    custom_engine_options = get_json_from_env("SQLALCHEMY_ENGINE_OPTIONS")
