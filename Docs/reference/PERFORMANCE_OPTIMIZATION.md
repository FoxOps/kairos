# Optimisation des performances

> Réécrit intégralement en Phase 5 (2026-07). La version précédente
> (1397 lignes) documentait en détail trois systèmes qui n'existent plus
> dans le code : pagination avancée (`app/utils/pagination/`), lazy
> loading (`app/utils/lazy_loading.py`, 785 lignes), et un module de
> monitoring de performance (`PerformanceMonitor`) qui — d'après l'audit
> mené en Phase 4 — **n'a en réalité jamais existé** : le décorateur
> `measure_time` qui prétendait s'en servir importait un module
> (`app.utils.performance_monitor`) introuvable, preuve qu'il n'avait
> jamais tourné. Les trois ont été supprimés comme code mort confirmé en
> Phase 4 (voir `report/Phase 4: AMÉLIORATION DES TESTS.md`). Ce qui
> suit ne documente que ce qui reste réellement dans le code.

## Cache

`app/utils/cache/` fournit un cache applicatif simple, initialisé
inconditionnellement au démarrage (`init_cache(app)` dans
`app/__init__.py`).

```bash
# .env
CACHE_TYPE=simple   # ou redis
CACHE_DEFAULT_TIMEOUT=300
CACHE_REDIS_URL=redis://localhost:6379/0   # si CACHE_TYPE=redis
```

- `simple` : `flask_caching.backends.SimpleCache` si `Flask-Caching` est
  installé, sinon repli automatique sur `SimpleDictCache`
  (`app/utils/cache/cache_manager.py`) — un cache dictionnaire en
  mémoire minimal, visible dans les logs
  (`Flask-Caching not available, using simple dictionary cache`).
- `redis` : `flask_caching.backends.RedisCache`, nécessite
  `Flask-Caching` installé et un serveur Redis joignable.

Le cache est initialisé mais **rien dans le code actuel ne l'utilise
activement** (aucune route ni service n'appelle `get_cache()` pour
lire/écrire une entrée) — les décorateurs qui l'exploitaient
(`cached_route`, `cache_result`) ont été supprimés en Phase 4 comme code
mort (zéro appelant, et leur import `from app.utils.cache import cache`
n'a d'ailleurs jamais correspondu à un export réel du module). C'est une
infrastructure prête à être rebranchée si un besoin de cache applicatif
réel se présente, pas une optimisation actuellement en service.

## Éviter le N+1 : `eager_load`

Seul décorateur de `app/utils/optimizations/__init__.py` (réduit de 14
décorateurs à 1 en Phase 4, voir le même rapport) — charge une ou
plusieurs relations SQLAlchemy en une requête plutôt qu'en N :

```python
from app.utils.optimizations import eager_load

@eager_load(Shift, ['user', 'shift_type'])
def get_shifts():
    return Shift.query...
```

Utilisé dans `app/routes/dashboard_routes.py` (page d'accueil) et dans
plusieurs routes admin (`admin_user_routes.py`, `admin_group_routes.py`,
`admin_shift_type_routes.py`).

Les repositories utilisent aussi directement `joinedload()` de
SQLAlchemy sans passer par ce décorateur — voir par exemple
`ShiftRepository.list_paginated()` dans `app/repositories/shift_repository.py`,
qui charge `user` et `shift_type` en une requête. Un test dédié
(`tests/integration/test_performance.py`) vérifie que le nombre de
requêtes SQL ne croît pas avec le nombre de shifts affichés — voir ce
fichier pour la méthode si vous voulez vérifier une autre route.

## Index de base de données

Index composites définis directement dans les modèles
(`app/models/*.py`), à préserver si vous modifiez les patterns de
requête dans `app/repositories/` :

| Table | Index |
|---|---|
| `Shift` | `(user_id, date)`, `(date, start_time)` |
| `OnCall` | `(user_id, start_time, end_time)` |
| `Leave` | `(user_id, start_date, end_date)` |

Voir [`architecture/ERD.md`](../architecture/ERD.md) pour le schéma
complet.

## Pagination

Pas de système de pagination avancée configurable par variables
d'environnement (contrairement à ce que documentait la version
précédente de ce fichier). Les listes paginées (`/schedule`, `/oncall`,
`/leave`) utilisent directement la pagination de Flask-SQLAlchemy
(`Query.paginate(page=, per_page=)`), avec un choix de taille de page
fixe côté route (`5, 10, 25, 50, 100` ou "tout afficher").

## Ce qui n'existe pas (encore)

Pas de mise en cache active des requêtes, pas de lazy loading côté
frontend (chargement par lots au scroll), pas de dashboard de monitoring
de performance intégré. Pour du monitoring en production, voir
[`app/utils/prometheus_metrics.py`](../../app/utils/prometheus_metrics.py)
(gated par `PROMETHEUS_ENABLED`, expose `/metrics` au format Prometheus)
et [`app/utils/health.py`](../../app/utils/health.py) (`/health`, `/ready`).
