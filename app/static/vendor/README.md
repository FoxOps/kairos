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
    ├── index.global.min.css   # FullCalendar v6 - CSS principal
    ├── index.global.min.js    # FullCalendar v6 - Core JS
    ├── locales/
    │   └── fr.global.min.js    # Locale française
    └── interaction.global.min.js  # Plugin pour drag & drop
```

## Pourquoi ces fichiers ?

L'application utilise plusieurs bibliothèques externes :
- **Bulma** : Framework CSS pour le design
- **Font Awesome** : Icônes
- **FullCalendar v6** : Calendrier interactif avec drag & drop

En production, surtout dans des environnements sans accès internet, il est **fortement recommandé** de servir ces fichiers localement plutôt que de dépendre des CDN.

## Comment générer ces fichiers ?

Exécutez le script de téléchargement :

```bash
python scripts/download_vendor_assets.py
```

Ce script télécharge automatiquement toutes les ressources nécessaires depuis les CDN officiels.

## Versions utilisées

- Bulma: 1.0.5
- Font Awesome: 6.4.0
- FullCalendar: 7.0.1 (tous les plugins inclus)

## Notes

- Le plugin **Interaction** est requis pour les fonctionnalités de drag & drop
- La locale française permet l'affichage en français du calendrier
- Ces fichiers sont référencés dans les templates via `url_for('static', filename='vendor/...')`
