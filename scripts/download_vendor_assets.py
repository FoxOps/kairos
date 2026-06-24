#!/usr/bin/env python3
"""
Script pour télécharger les ressources statiques (Bulma, Font Awesome, FullCalendar)
nécessaires pour l'application Leviia Schedule.

Ce script télécharge les fichiers CSS/JS depuis les CDN et les place dans app/static/vendor/
pour permettre un fonctionnement hors ligne.

Utilise urllib.request au lieu de requests pour éviter les dépendances externes.
"""

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError

# Configuration
VENDOR_DIR = Path(__file__).parent.parent / "app" / "static" / "vendor"

# Ressources à télécharger
# Utilisation de jsdelivr avec des versions testées et fonctionnelles
# Note: FullCalendar v6 n'a pas de fichier CSS séparé - le CSS est inclus dans le JS
RESOURCES = {
    "bulma": {
        "url": "https://cdn.jsdelivr.net/npm/bulma@1.0.4/css/bulma.css",
        "path": VENDOR_DIR / "bulma" / "bulma.css"
    },
    "font-awesome": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        "path": VENDOR_DIR / "font-awesome" / "all.min.css"
    },
    # FullCalendar v6.1.21 - JS principal
    "fullcalendar-v6-js": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "index.global.min.js"
    },
    # FullCalendar v6.1.21 - Locale FR depuis @fullcalendar/core
    "fullcalendar-v6-locale-fr": {
        "url": "https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.21/locales/fr.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "locales" / "fr.global.min.js"
    },
    # FullCalendar v6.1.21 - Plugin Interaction pour le drag & drop
    "fullcalendar-v6-interaction": {
        "url": "https://cdn.jsdelivr.net/npm/@fullcalendar/interaction@6.1.21/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "interaction.global.min.js"
    }
}


def download_file(url, path):
    """Télécharge un fichier depuis une URL en utilisant urllib."""
    try:
        print(f"Téléchargement de {url}...")
        
        # Créer le dossier parent si nécessaire
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Télécharger le fichier
        urlretrieve(url, str(path))
        
        print(f"  ✅ Enregistré dans {path}")
        return True
    except HTTPError as e:
        print(f"  ❌ Erreur HTTP {e.code}: {e.reason}")
        return False
    except URLError as e:
        print(f"  ❌ Erreur URL: {e.reason}")
        return False
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
        return 0
    else:
        print("\n⚠️  Certaines ressources n'ont pas pu être téléchargées.")
        print("L'application peut avoir des problèmes d'affichage.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
