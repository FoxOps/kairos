#!/usr/bin/env python3
"""
Script pour télécharger les ressources statiques (Bulma, Font Awesome, FullCalendar)
nécessaires pour l'application Leviia Schedule.

Ce script télécharge les fichiers CSS/JS depuis les CDN et les place dans app/static/vendor/
pour permettre un fonctionnement hors ligne.
"""

import os
import requests
from pathlib import Path

# Configuration
VENDOR_DIR = Path(__file__).parent.parent / "app" / "static" / "vendor"

# Ressources à télécharger
RESOURCES = {
    "bulma": {
        "url": "https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css",
        "path": VENDOR_DIR / "bulma" / "bulma.min.css"
    },
    "font-awesome": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        "path": VENDOR_DIR / "font-awesome" / "all.min.css"
    },
    "fullcalendar-core-css": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css",
        "path": VENDOR_DIR / "fullcalendar" / "index.global.min.css"
    },
    "fullcalendar-core-js": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "index.global.min.js"
    },
    "fullcalendar-fr-locale": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/locales/fr.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "locales" / "fr.global.min.js"
    },
    "fullcalendar-interaction": {
        "url": "https://cdn.jsdelivr.net/npm/@fullcalendar/interaction@6.1.11/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "interaction.global.min.js"
    }
}


def download_file(url, path):
    """Télécharge un fichier depuis une URL."""
    try:
        print(f"Téléchargement de {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Créer le dossier parent si nécessaire
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Écrire le fichier
        with open(path, 'wb') as f:
            f.write(response.content)
        
        print(f"  ✅ Enregistré dans {path}")
        return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def main():
    """Télécharge toutes les ressources."""
    print("Téléchargement des ressources statiques pour Leviia Schedule\n")
    
    success_count = 0
    for name, resource in RESOURCES.items():
        if download_file(resource["url"], resource["path"]):
            success_count += 1
    
    print(f"\n{success_count}/{len(RESOURCES)} fichiers téléchargés avec succès.")
    
    if success_count == len(RESOURCES):
        print("\n✅ Toutes les ressources ont été téléchargées.")
        print("L'application peut maintenant fonctionner sans connexion internet.")
    else:
        print("\n⚠️  Certaines ressources n'ont pas pu être téléchargées.")
        print("L'application peut avoir des problèmes d'affichage.")


if __name__ == "__main__":
    main()
