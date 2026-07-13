#!/usr/bin/env python3
"""
Script pour télécharger les ressources statiques (Bulma, Font Awesome, FullCalendar)
nécessaires pour l'application Leviia Schedule.

Ce script télécharge les fichiers CSS/JS depuis les CDN ou les archives officielles
et les place dans app/static/vendor/ pour permettre un fonctionnement hors ligne.

Utilise urllib.request au lieu de requests pour éviter les dépendances externes.
"""

import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

# Configuration
VENDOR_DIR = Path(__file__).parent.parent / "app" / "static" / "vendor"

# Ressources à télécharger
# Utilisation de jsdelivr avec des versions testées et fonctionnelles
# Note: FullCalendar v6 n'a pas de fichier CSS séparé - le CSS est inclus dans le JS
RESOURCES = {
    "bulma": {
        "url": "https://cdn.jsdelivr.net/npm/bulma@1.0.4/css/bulma.css",
        "path": VENDOR_DIR / "bulma" / "bulma.css",
    },
    # Font Awesome 7.2.0 - CSS principal
    "font-awesome": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/css/all.min.css",
        "path": VENDOR_DIR / "font-awesome" / "all.min.css",
    },
    # Font Awesome 7.2.0 webfonts (polices nécessaires pour le CSS)
    # Note: Font Awesome 7.2.0 ne fournit que des fichiers WOFF2 (pas de TTF)
    "font-awesome-webfonts-brands-400": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-brands-400.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-brands-400.woff2",
    },
    "font-awesome-webfonts-regular-400": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-regular-400.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-regular-400.woff2",
    },
    "font-awesome-webfonts-solid-900": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-solid-900.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-solid-900.woff2",
    },
    "font-awesome-webfonts-v4compatibility": {
        "url": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/webfonts/fa-v4compatibility.woff2",
        "path": VENDOR_DIR / "font-awesome" / "webfonts" / "fa-v4compatibility.woff2",
    },
    # FullCalendar v6.1.21 - JS principal (inclut déjà interaction, daygrid, timegrid, list, multimonth)
    "fullcalendar-v6-js": {
        "url": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/index.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "index.global.min.js",
    },
    # FullCalendar v6.1.21 - Locale FR depuis @fullcalendar/core
    "fullcalendar-v6-locale-fr": {
        "url": "https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.21/locales/fr.global.min.js",
        "path": VENDOR_DIR / "fullcalendar" / "locales" / "fr.global.min.js",
    },
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


def copy_webfonts_to_vendor():
    """Copie les fichiers de polices Font Awesome dans app/static/vendor/webfonts/.

    Le CSS de Font Awesome utilise des chemins relatifs comme ../webfonts/
    qui pointent vers app/static/vendor/webfonts/.

    Cette fonction copie les fichiers de polices depuis
    app/static/vendor/font-awesome/webfonts/ vers app/static/vendor/webfonts/.
    """
    webfonts_source = VENDOR_DIR / "font-awesome" / "webfonts"
    webfonts_target = VENDOR_DIR / "webfonts"

    # Vérifier que la source existe
    if not webfonts_source.exists():
        print(f"  ⚠️  Le dossier source n'existe pas: {webfonts_source}")
        return False

    # Supprimer la cible si elle existe déjà
    if webfonts_target.exists():
        import shutil

        shutil.rmtree(str(webfonts_target))

    # Copier les fichiers
    try:
        import shutil

        shutil.copytree(str(webfonts_source), str(webfonts_target))
        print(f"  ✅ Fichiers copiés: {webfonts_source} -> {webfonts_target}")

        # Patcher le CSS pour utiliser des chemins relatifs
        # Le CSS est servi depuis /static/vendor/font-awesome/all.min.css
        # donc ../webfonts/ pointe vers /static/vendor/webfonts/ qui est correct
        css_file = VENDOR_DIR / "font-awesome" / "all.min.css"
        if css_file.exists():
            with open(css_file) as f:
                css_content = f.read()

            # S'assurer que le CSS utilise des chemins relatifs ../webfonts/
            # (le CSS original utilise déjà ../webfonts/, mais au cas où)
            css_patched = css_content.replace(
                "/static/vendor/webfonts/", "../webfonts/"
            )

            with open(css_file, "w") as f:
                f.write(css_patched)

            print("  ✅ CSS patché pour utiliser des chemins relatifs")

        return True
    except Exception as e:
        print(f"  ❌ Impossible de copier les fichiers: {e}")
        return False


def main():
    """Télécharge toutes les ressources."""
    print("Téléchargement des ressources statiques pour Leviia Schedule\n")

    success_count = 0
    for _name, resource in RESOURCES.items():
        if download_file(resource["url"], resource["path"]):
            success_count += 1

    # Copier les polices Font Awesome dans vendor/webfonts/
    print("\nCopie des polices Font Awesome dans vendor/webfonts/...")
    if copy_webfonts_to_vendor():
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
