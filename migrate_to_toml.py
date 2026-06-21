#!/usr/bin/env python
# =============================================================================
# SCRIPT DE MIGRATION VERS LE FORMAT TOML
# =============================================================================
"""
Script pour migrer les données de configuration existantes vers le nouveau format TOML.

Utilisation :
    python migrate_to_toml.py

Ce script :
1. Charge l'application Flask
2. Extrait les données de configuration de la base de données
3. Génère le fichier automation_rules.toml
4. Synchronise la base de données avec le fichier TOML
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config.migration import migrate_and_sync, DatabaseConfigMigrator, ConfigValidator
from app.config.automation_rules import AutomationConfig


def main():
    """Fonction principale du script de migration."""
    print("=" * 70)
    print("SCRIPT DE MIGRATION VERS LE FORMAT TOML")
    print("=" * 70)
    print()
    
    # Créer l'application Flask
    app = create_app()
    
    with app.app_context():
        print("✓ Application Flask chargée")
        print()
        
        # Afficher la configuration actuelle
        print("Configuration actuelle dans le fichier TOML :")
        print("-" * 70)
        try:
            config = AutomationConfig.load()
            print(f"  Groupes schedule: {config['groups']['schedule_groups']}")
            print(f"  Groupes astreintes: {config['groups']['oncall_groups']}")
            print(f"  Types de shifts: {len(config['shifts']['shift_types'])} types")
            print(f"  Ordre de rotation: {config['oncall']['rotation_order']}")
            print()
        except Exception as e:
            print(f"  ⚠️  Impossible de charger la configuration: {str(e)}")
            print()
        
        # Effectuer la migration
        print("Lancement de la migration...")
        print("-" * 70)
        
        try:
            result = migrate_and_sync()
            print(result)
            print()
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {str(e)}")
            print()
            sys.exit(1)
        
        # Afficher la nouvelle configuration
        print("Nouvelle configuration dans le fichier TOML :")
        print("-" * 70)
        try:
            AutomationConfig.reload()
            config = AutomationConfig.load()
            print(f"  Groupes schedule: {config['groups']['schedule_groups']}")
            print(f"  Groupes astreintes: {config['groups']['oncall_groups']}")
            print(f"  Types de shifts: {len(config['shifts']['shift_types'])} types")
            print(f"  Ordre de rotation: {config['oncall']['rotation_order']}")
            print()
        except Exception as e:
            print(f"  ⚠️  Impossible de recharger la configuration: {str(e)}")
            print()
        
        # Valider la configuration
        print("Validation de la configuration...")
        print("-" * 70)
        is_valid, errors = ConfigValidator.validate_all(config)
        if is_valid:
            print("✅ Configuration valide")
        else:
            print("❌ Erreurs de validation :")
            for error in errors:
                print(f"  - {error}")
        print()
        
        print("=" * 70)
        print("MIGRATION TERMINÉE")
        print("=" * 70)


if __name__ == "__main__":
    main()
