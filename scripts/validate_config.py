#!/usr/bin/env python3
"""
Script de validation de la configuration pour Leviia Schedule.

Ce script vérifie que toutes les variables d'environnement nécessaires sont définies
et que leurs valeurs sont valides.

Utilisation:
    python scripts/validate_config.py

    ou

    python scripts/validate_config.py --env-file .env
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importer les fonctions utilitaires depuis config
from config import get_bool_from_env

# Variables d'environnement critiques qui doivent être définies en production
CRITICAL_VARIABLES = {
    "SECRET_KEY": {
        "required_in_production": True,
        "type": "string",
        "min_length": 16,
        "description": "Clé secrète pour Flask (doit être longue et aléatoire)",
    },
    "DATABASE_URL": {
        "required_in_production": True,
        "type": "string",
        "description": "URI de la base de données",
        "pattern": r"^(sqlite|postgresql|mysql|mariadb)://",
    },
}

# Variables d'environnement recommandées
RECOMMENDED_VARIABLES = {
    "FLASK_ENV": {
        "type": "string",
        "allowed_values": ["development", "production", "testing", "default"],
        "description": "Environnement Flask",
    },
    "LOG_LEVEL": {
        "type": "string",
        "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "description": "Niveau de log principal",
    },
    "SQLALCHEMY_ECHO": {
        "type": "boolean",
        "description": "Afficher les requêtes SQL dans les logs",
    },
    "DEBUG_ERRORS": {
        "type": "boolean",
        "description": "Afficher les détails des erreurs (DANGER: ne jamais activer en production!)",
    },
    "LOGIN_DISABLED": {
        "type": "boolean",
        "description": "Désactiver l'authentification (DANGER: ne jamais activer en production!)",
    },
    "CORS_ENABLED": {
        "type": "boolean",
        "description": "Activer CORS",
    },
    "SYSLOG_ENABLED": {
        "type": "boolean",
        "description": "Activer syslog pour la production",
    },
    "LOG_FILTER_SENSITIVE": {
        "type": "boolean",
        "description": "Filtrer les données sensibles dans les logs",
    },
}

# Variables d'environnement numériques
NUMERIC_VARIABLES = {
    "LOG_FILE_SIZE": {
        "type": "int",
        "min": 1024,
        "description": "Taille maximale des fichiers de log en octets",
    },
    "LOG_BACKUP_COUNT": {
        "type": "int",
        "min": 1,
        "max": 100,
        "description": "Nombre de fichiers de backup à conserver",
    },
    "REMEMBER_COOKIE_DURATION": {
        "type": "int",
        "min": 0,
        "description": "Durée du cookie en secondes",
    },
    "ERROR_503_RETRY_AFTER": {
        "type": "int",
        "min": 0,
        "description": "Délai de réessai pour les erreurs 503 en secondes",
    },
    "DATABASE_CONNECT_TIMEOUT": {
        "type": "int",
        "min": 1,
        "max": 300,
        "description": "Délai d'attente pour la connexion à la base de données",
    },
    "DATABASE_POOL_SIZE": {
        "type": "int",
        "min": 1,
        "max": 50,
        "description": "Taille du pool de connexions",
    },
    "DATABASE_MAX_OVERFLOW": {
        "type": "int",
        "min": 0,
        "max": 100,
        "description": "Nombre maximal de connexions supplémentaires",
    },
    "SMTP_PORT": {"type": "int", "min": 1, "max": 65535, "description": "Port SMTP"},
    "ICS_TOKEN_EXPIRY_DAYS": {
        "type": "int",
        "min": 1,
        "max": 3650,
        "description": "Durée de validité du token ICS en jours",
    },
}


class ConfigValidator:
    """Valideur de configuration."""

    def __init__(self, env_file=None):
        """Initialise le valideur.

        Args:
            env_file: Chemin vers un fichier .env à charger (optionnel)
        """
        self.env_file = env_file
        self.errors = []
        self.warnings = []
        self.info = []

        # Charger le fichier .env si spécifié
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)

    def _load_env_file(self, env_file):
        """Charge un fichier .env dans l'environnement."""
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
            self.info.append(f"Fichier {env_file} chargé avec succès")
        except ImportError:
            # Charger manuellement
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
            self.info.append(
                f"Fichier {env_file} chargé manuellement (python-dotenv non disponible)"
            )
        except Exception as e:
            self.errors.append(f"Erreur lors du chargement de {env_file}: {str(e)}")

    def validate_critical_variables(self, is_production=False):
        """Valide les variables d'environnement critiques."""
        for var_name, config in CRITICAL_VARIABLES.items():
            value = os.environ.get(var_name)

            if is_production and config.get("required_in_production"):
                if not value:
                    self.errors.append(
                        f"Variable critique manquante en production: {var_name}"
                    )
                    continue

            if value:
                # Vérifier le type
                if config.get("type") == "string":
                    if config.get("min_length") and len(value) < config["min_length"]:
                        self.warnings.append(
                            f"{var_name} est trop court (min: {config['min_length']} caractères, actuel: {len(value)})"
                        )

                    # Vérifier le pattern si spécifié
                    if "pattern" in config:
                        import re

                        if not re.match(config["pattern"], value):
                            self.errors.append(
                                f"{var_name} ne correspond pas au format attendu: {config['pattern']}"
                            )

                self.info.append(f"{var_name}: OK")

    def validate_recommended_variables(self):
        """Valide les variables d'environnement recommandées."""
        for var_name, config in RECOMMENDED_VARIABLES.items():
            value = os.environ.get(var_name)

            if value:
                # Vérifier les valeurs autorisées
                if "allowed_values" in config:
                    if value not in config["allowed_values"]:
                        self.warnings.append(
                            f"{var_name} a une valeur non autorisée: '{value}'. "
                            f"Valeurs autorisées: {config['allowed_values']}"
                        )

                # Vérifier le type booléen
                if config.get("type") == "boolean":
                    if value.lower() not in (
                        "true",
                        "false",
                        "1",
                        "0",
                        "yes",
                        "no",
                        "y",
                        "n",
                        "on",
                        "off",
                    ):
                        self.warnings.append(
                            f"{var_name} devrait être une valeur booléenne (true/false, 1/0, yes/no)"
                        )

                self.info.append(f"{var_name}: OK")

    def validate_numeric_variables(self):
        """Valide les variables d'environnement numériques."""
        for var_name, config in NUMERIC_VARIABLES.items():
            value = os.environ.get(var_name)

            if value:
                try:
                    int_value = int(value)

                    # Vérifier les contraintes
                    if "min" in config and int_value < config["min"]:
                        self.warnings.append(
                            f"{var_name} est inférieur au minimum: {config['min']} (actuel: {int_value})"
                        )

                    if "max" in config and int_value > config["max"]:
                        self.warnings.append(
                            f"{var_name} est supérieur au maximum: {config['max']} (actuel: {int_value})"
                        )

                    self.info.append(f"{var_name}: OK ({int_value})")

                except ValueError:
                    self.errors.append(
                        f"{var_name} doit être un entier valide: '{value}'"
                    )

    def validate_json_variables(self):
        """Valide les variables d'environnement JSON."""
        json_vars = ["SQLALCHEMY_ENGINE_OPTIONS", "DEFAULT_SHIFT_TYPES"]

        for var_name in json_vars:
            value = os.environ.get(var_name)

            if value and value.strip():
                try:
                    json.loads(value)
                    self.info.append(f"{var_name}: JSON valide")
                except json.JSONDecodeError as e:
                    self.errors.append(
                        f"{var_name} contient un JSON invalide: {str(e)}"
                    )

    def validate_security(self):
        """Valide les paramètres de sécurité."""
        # Vérifier que LOGIN_DISABLED n'est pas activé en production
        flask_env = os.environ.get("FLASK_ENV", "development")
        login_disabled = get_bool_from_env("LOGIN_DISABLED", False)

        if flask_env == "production" and login_disabled:
            self.errors.append(
                "DANGER: LOGIN_DISABLED est activé en production! "
                "Cela désactive complètement l'authentification."
            )

        # Vérifier que DEBUG_ERRORS n'est pas activé en production
        debug_errors = get_bool_from_env("DEBUG_ERRORS", False)

        if flask_env == "production" and debug_errors:
            self.errors.append(
                "DANGER: DEBUG_ERRORS est activé en production! "
                "Cela peut exposer des informations sensibles."
            )

        # Vérifier que SECRET_KEY n'est pas la valeur par défaut en production.
        # Placeholder public connu, pas un vrai secret (S105).
        default_secret_key_placeholder = "ta-cle-secrete-ici"  # noqa: S105
        secret_key = os.environ.get("SECRET_KEY", default_secret_key_placeholder)

        if flask_env == "production" and secret_key == default_secret_key_placeholder:
            self.errors.append(
                "DANGER: SECRET_KEY utilise la valeur par défaut en production! "
                'Générez une clé sécurisée avec: python -c "import secrets; print(secrets.token_hex(32))"'
            )

    def validate_all(self):
        """Valide toute la configuration."""
        flask_env = os.environ.get("FLASK_ENV", "development")
        is_production = flask_env == "production"

        self.info.append(f"Début de la validation pour l'environnement: {flask_env}")

        self.validate_critical_variables(is_production)
        self.validate_recommended_variables()
        self.validate_numeric_variables()
        self.validate_json_variables()
        self.validate_security()

        # Vérifier que le dossier de logs existe ou peut être créé
        log_dir = os.environ.get("LOG_DIR") or os.path.join(
            os.path.dirname(__file__), "..", "logs"
        )
        try:
            os.makedirs(log_dir, exist_ok=True)
            self.info.append(f"Dossier des logs: {log_dir} - OK")
        except Exception as e:
            self.warnings.append(
                f"Impossible de créer le dossier des logs {log_dir}: {str(e)}"
            )

    def print_results(self):
        """Affiche les résultats de la validation."""
        print("\n" + "=" * 70)
        print("VALIDATION DE LA CONFIGURATION - LEVIIA SCHEDULE")
        print("=" * 70)

        # Afficher les informations
        if self.info:
            print("\n[INFO] Informations:")
            for msg in self.info:
                print(f"  ✓ {msg}")

        # Afficher les avertissements
        if self.warnings:
            print("\n[WARNING] Avertissements:")
            for msg in self.warnings:
                print(f"  ⚠ {msg}")

        # Afficher les erreurs
        if self.errors:
            print("\n[ERROR] Erreurs:")
            for msg in self.errors:
                print(f"  ✗ {msg}")

        # Résumé
        print("\n" + "-" * 70)
        total_checks = len(self.info) + len(self.warnings) + len(self.errors)
        success = len(self.info)
        warnings_count = len(self.warnings)
        errors_count = len(self.errors)

        print(f"Total des vérifications: {total_checks}")
        print(f"  Réussies: {success}")
        print(f"  Avertissements: {warnings_count}")
        print(f"  Erreurs: {errors_count}")

        if errors_count > 0:
            print(
                "\n❌ VALIDATION ECHOUEE - Des erreurs critiques doivent être corrigées"
            )
            return False
        elif warnings_count > 0:
            print("\n⚠️  VALIDATION AVEC AVERTISSEMENTS - Vérifiez les avertissements")
            return True
        else:
            print("\n✅ VALIDATION REUSSIE - Configuration valide")
            return True


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Valider la configuration de Leviia Schedule"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Chemin vers le fichier .env à valider (par défaut: .env)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Valider pour un environnement de production",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Traiter les avertissements comme des erreurs",
    )

    args = parser.parse_args()

    # Définir FLASK_ENV si --production est spécifié
    if args.production:
        os.environ["FLASK_ENV"] = "production"

    # Créer le valideur
    validator = ConfigValidator(env_file=args.env_file)

    # Valider toute la configuration
    validator.validate_all()

    # Afficher les résultats
    success = validator.print_results()

    # Quitter avec le code approprié
    if args.strict and validator.warnings:
        sys.exit(1)
    elif not success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
