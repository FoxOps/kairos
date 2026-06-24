# Ressources statiques locales

Ce dossier contient les ressources CSS/JS nécessaires pour le bon fonctionnement de l'application **sans dépendre des CDN externes**.

## Structure

```
vendor/
├── bulma/
│   └── bulma.min.css          # Framework CSS Bulma
├── font-awesome/
│   └── all.min.css            # Icônes Font Awesome
└── fullcalendar/
    ├── index.global.min.css   # FullCalendar v7 - CSS principal
    └── index.global.min.js    # FullCalendar v7 - Core JS (tous plugins inclus)
```

## Pourquoi ces fichiers ?

L'application utilise plusieurs bibliothèques externes :
- **Bulma** : Framework CSS pour le design
- **Font Awesome** : Icônes
- **FullCalendar v7** : Calendrier interactif avec drag & drop (tous plugins inclus)

En production, surtout dans des environnements sans accès internet, il est **fortement recommandé** de servir ces fichiers localement plutôt que de dépendre des CDN.

## Comment générer ces fichiers ?

Exécutez le script de téléchargement :

```bash
python scripts/download_vendor_assets.py
```

Ce script télécharge automatiquement toutes les ressources nécessaires depuis les **releases GitHub officielles** (plus fiable que les CDN).

## Versions utilisées

- Bulma: 1.0.0 (via GitHub releases)
- Font Awesome: 6.4.0 (via GitHub releases)
- FullCalendar: 7.0.0 (via GitHub releases, tous les plugins inclus)

## Notes

- Le plugin **Interaction** est requis pour les fonctionnalités de drag & drop
- La locale française permet l'affichage en français du calendrier
- Ces fichiers sont référencés dans les templates via `url_for('static', filename='vendor/...')`
