# Ressources statiques locales

Ce dossier contient les ressources CSS/JS nécessaires pour le bon fonctionnement de l'application **sans dépendre des CDN externes**.

## Structure

```
vendor/
├── bulma/
│   └── bulma.css              # Framework CSS Bulma
├── font-awesome/
│   └── all.min.css            # Icônes Font Awesome
└── fullcalendar/
    ├── index.global.min.js    # FullCalendar v6.1.21 - Core JS (inclut CSS)
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

Ce script télécharge automatiquement toutes les ressources nécessaires depuis les CDN (jsdelivr, cdnjs).

## Versions utilisées

- Bulma: 1.0.4
- Font Awesome: 6.4.0
- FullCalendar: 6.1.21 (JS principal + plugin interaction) avec locale française depuis @fullcalendar/core 6.1.21

> **Note**: FullCalendar v6 n'a pas de fichier CSS séparé. Le CSS est inclus directement dans le fichier JS principal.

## Notes

- Le plugin **Interaction** est requis pour les fonctionnalités de drag & drop
- La locale française permet l'affichage en français du calendrier
- Ces fichiers sont référencés dans les templates via `url_for('static', filename='vendor/...')`
