#!/usr/bin/env python3
"""
Script pour télécharger les ressources statiques (Bulma, Font Awesome, FullCalendar)
nécessaires pour l'application Leviia Schedule.

Ce script télécharge les fichiers CSS/JS depuis les CDN ou les archives officielles
et les place dans app/static/vendor/ pour permettre un fonctionnement hors ligne.

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
    # Font Awesome 7.2.0 - CSS principal
    "font-awesome": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/css/all.min.css",
        "path": VENDOR_DIR / "font-awesome" / "all.min.css"
    },
    # Font Awesome 7.2.0 webfonts (polices nécessaires pour le CSS)
    # Note: Font Awesome 7.2.0 ne fournit que des fichiers WOFF2 (pas de TTF)
    "font-awesome-webfonts-brands-400": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-brands-400.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-brands-400.woff2"
    },
    "font-awesome-webfonts-regular-400": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-regular-400.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-regular-400.woff2"
    },
    "font-awesome-webfonts-solid-900": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-solid-900.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-solid-900.woff2"
    },
    "font-awesome-webfonts-v4compatibility": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-v4compatibility.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-v4compatibility.woff2"
    },
    # FullCalendar v6.1.21 - JS principal (inclut déjà interaction, daygrid, timegrid, list, multimonth)
    "fullcalendar-v6-js": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "index.global.min.js"
    },
    # FullCalendar v6.1.21 - Locale FR depuis @fullcalendar/core
    "fullcalendar-v6-locale-fr": {
        "url": "https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.21/locales/fr.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "locales" / "fr.global.min.js"
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


def create_symlink_for_fonts():
    """Crée un lien symbolique pour les polices Font Awesome.
    
    Le CSS de Font Awesome utilise des chemins relatifs comme ../webfonts/
    qui pointent vers app/static/vendor/webfonts/ au lieu de 
    app/static/vendor/font-awesome/webfonts/.
    
    Ce lien symbolique permet de résoudre ce problème.
    """
    webfonts_source = VENDOR_DIR / "font-awesome" / "webfonts"
    webfonts_link = VENDOR_DIR / "webfonts"
    
    # Vérifier si le lien symbolique existe déjà
    if webfonts_link.exists():
        # Supprimer le lien existant s'il pointe vers le mauvais endroit
        if webfonts_link.is_symlink():
            webfonts_link.unlink()
        elif webfonts_link.exists():
            # C'est un dossier, pas un lien symbolique - le supprimer
            import shutil
            shutil.rmtree(str(webfonts_link))
    
    # Créer le lien symbolique
    try:
        webfonts_link.symlink_to(webfonts_source, target_is_directory=True)
        print(f"  ✅ Lien symbolique créé: {webfonts_link} -> {webfonts_source}")
        return True
    except Exception as e:
        print(f"  ⚠️  Impossible de créer le lien symbolique: {e}")
        print(f"     Essayons de copier les fichiers à la place...")
        # Essayer de copier les fichiers
        try:
            import shutil
            if webfonts_source.exists():
                if webfonts_link.exists():
                    shutil.rmtree(str(webfonts_link))
                shutil.copytree(str(webfonts_source), str(webfonts_link))
                print(f"  ✅ Fichiers copiés: {webfonts_source} -> {webfonts_link}")
                return True
        except Exception as e2:
            print(f"  ❌ Impossible de copier les fichiers: {e2}")
            return False
        return False


def main():
    """Télécharge toutes les ressources."""
    print("Téléchargement des ressources statiques pour Leviia Schedule\n")
    
    success_count = 0
    for name, resource in RESOURCES.items():
        if download_file(resource["url"], resource["path"]):
            success_count += 1
    
    # Créer le lien symbolique pour les polices Font Awesome
    print("\nCréation du lien symbolique pour les polices Font Awesome...")
    if create_symlink_for_fonts():
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
