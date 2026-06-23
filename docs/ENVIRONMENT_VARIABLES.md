# Variables d'Environnement

Ce document décrit toutes les variables d'environnement disponibles.

## Configuration de Base

| Variable | Type | Défaut | Description |
|----------|------|--------|-------------|
| FLASK_ENV | string | default | Environnement (development, production, testing) |
| SECRET_KEY | string | ta-cle-secrete-ici | Clé secrète pour Flask |

## Sécurité

| Variable | Type | Défaut | Description |
|----------|------|--------|-------------|
| RATE_LIMIT_ENABLED | bool | true | Active le rate limiting |
| WTF_CSRF_ENABLED | bool | true | Active la protection CSRF |
| COMPRESS_ENABLED | bool | true | Active la compression Gzip |
| SESSION_COOKIE_SECURE | bool | false | Active les cookies sécurisés |

## Nettoyage Automatique

| Variable | Type | Défaut | Description |
|----------|------|--------|-------------|
| DATA_CLEANUP_ENABLED | bool | false | Active le nettoyage automatique |
| DATA_CLEANUP_RETENTION | string | 365d | Durée de rétention (1y, 6m, 30d, etc.) |
| DATA_CLEANUP_BATCH_SIZE | int | 1000 | Taille des lots |
| DATA_CLEANUP_SCHEDULE | string | 0 0 * * * | Planification cron |
