# 🚀 Optimisation des Performances - Leviia Schedule

> **Documentation complète des optimisations de performance**
> Version: 1.0 | Dernière mise à jour: Juin 2025

---

## 📚 Table des Matières

1. [🎯 Introduction](#-introduction)
2. [📦 Architecture des Optimisations](#-architecture-des-optimisations)
3. [💾 Système de Cache](#-système-de-cache)
4. [📄 Pagination Avancée](#-pagination-avancée)
5. [🔄 Lazy Loading](#-lazy-loading)
6. [🔍 Monitoring des Performances](#-monitoring-des-performances)
7. [⚡ Optimisations SQLAlchemy](#-optimisations-sqlalchemy)
8. [🎨 Configuration](#-configuration)
9. [🚀 Bonnes Pratiques](#-bonnes-pratiques)
10. [📊 Exemples Complets](#-exemples-complets)
11. [🔧 Dépannage](#-dépannage)
12. [📝 Changelog](#-changelog)

---

## 🎯 Introduction

Ce document décrit les optimisations de performance implémentées dans **Leviia Schedule** pour améliorer l'efficacité, la scalabilité et l'expérience utilisateur de l'application.

### Objectifs

- ✅ **Réduire le temps de réponse** des pages et API
- ✅ **Minimiser la charge sur la base de données**
- ✅ **Optimiser l'utilisation de la mémoire**
- ✅ **Améliorer l'expérience utilisateur** avec du chargement progressif
- ✅ **Faciliter le scaling** avec des solutions de cache distribué
- ✅ **Surveiller et analyser** les performances

### Composants Implémentés

| Composant | Description | Statut |
|-----------|-------------|--------|
| **Cache** | Système de cache multi-backend (SimpleCache, Redis, Memcached) | ✅ Implémenté |
| **Pagination** | Pagination standard, par curseur et lazy loading | ✅ Implémenté |
| **Lazy Loading** | Chargement différé des données et relations | ✅ Implémenté |
| **Monitoring** | Surveillance des performances et détection des goulots | ✅ Implémenté |
| **Optimisations SQL** | Eager loading, batch loading, requêtes optimisées | ✅ Implémenté |

---

## 📦 Architecture des Optimisations

```
┌─────────────────────────────────────────────────────────────────┐
│                        Leviia Schedule                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Cache         │    │   Pagination     │    │ Lazy Loading │ │
│  │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────┐ │ │
│  │  │SimpleCache │  │    │  │ Standard  │  │    │  │Lazy   │ │ │
│  │  │Redis      │  │    │  │Cursor    │  │    │  │Loader │ │ │
│  │  │Memcached  │  │    │  │Infinite  │  │    │  │Query  │ │ │
│  │  └───────────┘  │    │  └───────────┘  │    │  └───────┘ │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Monitoring des Performances                 │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │ Requêtes    │  │ SQL         │  │ Cache               │  │ │
│  │  │ Lentes      │  │ Queries     │  │ Hits/Misses         │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Optimisations SQLAlchemy                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │ Eager Load  │  │ Batch Load  │  │ Optimized Queries   │  │ │
│  │  │ joinedload  │  │ selectinload│  │ Filters, Order, etc. │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💾 Système de Cache

### 📖 Aperçu

Le système de cache de Leviia Schedule permet de **mettre en cache les données fréquemment accédées** pour réduire le nombre de requêtes à la base de données et améliorer les temps de réponse.

### 🎯 Fonctionnalités

- ✅ **Multi-backend** : SimpleCache (mémoire), Redis, Memcached
- ✅ **Cache par route** : Mise en cache des réponses HTTP complètes
- ✅ **Cache par fonction** : Mise en cache des résultats de fonctions
- ✅ **Cache par modèle** : Mise en cache des objets de base de données
- ✅ **TTL configurable** : Durée de vie personnalisable pour chaque cache
- ✅ **Invalidation automatique** : Invalidation du cache lors des modifications
- ✅ **Préfixes de clés** : Organisation hiérarchique du cache
- ✅ **Statistiques** : Suivi des hits/misses et taux de succès

### 📦 Backends Disponibles

| Backend | Description | Utilisation Recommandée | Performance |
|---------|-------------|------------------------|-------------|
| **SimpleCache** | Cache en mémoire (dictionnaire Python) | Développement, petites applications | ⚡⚡⚡ |
| **Redis** | Cache distribué en mémoire | Production, applications multi-workers | ⚡⚡⚡⚡⚡ |
| **Memcached** | Cache distribué simple | Production, cache objet simple | ⚡⚡⚡⚡ |

### 🚀 Configuration

#### Variables d'Environnement

```bash
# Type de cache
CACHE_TYPE=simple          # simple, redis, memcached

# Activation
CACHE_ENABLED=true        # true/false

# SimpleCache
CACHE_DEFAULT_TIMEOUT=300 # 5 minutes en secondes
CACHE_MAX_ENTRIES=1000    # Nombre max d'entrées
CACHE_THRESHOLD=0.75      # Seuil de nettoyage (0.0-1.0)

# Redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_PASSWORD=your_password
CACHE_REDIS_DB=0
CACHE_REDIS_SOCKET_TIMEOUT=5

# Memcached
CACHE_MEMCACHED_SERVERS=[('localhost', 11211)]
CACHE_MEMCACHED_USERNAME=user
CACHE_MEMCACHED_PASSWORD=pass

# Préfixe des clés
CACHE_KEY_PREFIX=leviia:
```

#### Configuration dans config.py

```python
from config_performance import PerformanceConfig, CacheType

# Configuration personnalisée
config = PerformanceConfig(
    cache=CacheSettings(
        cache_type=CacheType.REDIS,
        enabled=True,
        default_timeout=300,
        max_entries=5000,
        redis_url='redis://localhost:6379/0',
        key_prefix='leviia:'
    )
)

# Appliquer à l'application
config.configure(app)
```

### 💡 Utilisation

#### Cache de Route

```python
from app.utils.optimizations import cached_route

@app.route('/users')
@cached_route(timeout=60, vary_on=['group_id'])
def list_users():
    group_id = request.args.get('group_id')
    users = User.query.filter_by(group_id=group_id).all()
    return render_template('users.html', users=users)
```

#### Cache de Fonction

```python
from app.utils.optimizations import cache_result

@cache_result(timeout=300, key_func=lambda user_id: f'user:{user_id}')
def get_user_data(user_id):
    user = User.query.get(user_id)
    shifts = Shift.query.filter_by(user_id=user_id).all()
    return {'user': user, 'shifts': shifts}
```

#### Cache Manuel

```python
from app.utils.cache import cache, CacheKeys

# Stocker une valeur
cache.set(CacheKeys.USER_BY_ID.format(user_id=user.id), user, timeout=300)

# Récupérer une valeur
user = cache.get(CacheKeys.USER_BY_ID.format(user_id=user_id))

# Supprimer une valeur
cache.delete(CacheKeys.USER_BY_ID.format(user_id=user_id))

# Effacer tout le cache
cache.clear()
```

#### Décorateur @cache.cached

```python
from app.utils.cache import cache

@cache.cached(timeout=60, key_prefix='user_data', vary_on=['user_id'])
def get_user_data(user_id):
    return User.query.get(user_id)
```

### 🎯 Clés de Cache Standardisées

Le module `CacheKeys` fournit des clés de cache standardisées pour une meilleure organisation :

```python
from app.utils.cache import CacheKeys

# Utilisateurs
CacheKeys.ALL_USERS           # 'all_users'
CacheKeys.USER_BY_ID           # 'user:{user_id}'
CacheKeys.USER_BY_EMAIL        # 'user:email:{email}'

# Groupes
CacheKeys.ALL_GROUPS          # 'all_groups'
CacheKeys.GROUP_BY_ID          # 'group:{group_id}'

# Shifts
CacheKeys.ALL_SHIFTS          # 'all_shifts'
CacheKeys.SHIFTS_BY_DATE       # 'shifts:date:{date}'
CacheKeys.SHIFTS_BY_USER       # 'shifts:user:{user_id}'

# Astreintes
CacheKeys.ALL_ONCALLS         # 'all_oncalls'
CacheKeys.ONCALL_BY_DATE       # 'oncall:date:{date}'

# Congés
CacheKeys.ALL_LEAVES          # 'all_leaves'
CacheKeys.LEAVES_BY_DATE       # 'leaves:date:{date}'

# Export ICS
CacheKeys.ICS_EXPORT_SHIFTS   # 'ics:export:shifts:{user_id}:{scope}'
CacheKeys.ICS_EXPORT_ONCALL   # 'ics:export:oncall:{user_id}:{scope}'
```

### 📊 Statistiques du Cache

```python
from app.utils.cache import cache

# Récupérer les statistiques (SimpleCache uniquement)
stats = cache.cache.stats()
# {'hits': 150, 'misses': 50, 'hit_rate': 0.75, 'size': 200, 'max_entries': 1000}
```

---

## 📄 Pagination Avancée

### 📖 Aperçu

La pagination permet de **diviser les grands ensembles de données en pages gérables**, améliorant ainsi les performances et l'expérience utilisateur.

### 🎯 Fonctionnalités

- ✅ **Pagination standard** : Offset/Limit classique
- ✅ **Pagination par curseur** : Plus efficace pour les grandes tables
- ✅ **Lazy loading** : Chargement progressif pour le scroll infini
- ✅ **Options configurables** : Taille de page, style, etc.
- ✅ **Intégration Bulma** : Liens de pagination prêts à l'emploi
- ✅ **Support API JSON** : Pagination pour les endpoints REST

### 🚀 Configuration

#### Variables d'Environnement

```bash
# Activation
PAGINATION_ENABLED=true

# Paramètres par défaut
PAGINATION_DEFAULT_PER_PAGE=20
PAGINATION_MAX_PER_PAGE=100
PAGINATION_PER_PAGE_OPTIONS=[5, 10, 20, 50, 100]

# Style
PAGINATION_STYLE=bulma  # bulma, bootstrap, simple, none
PAGINATION_WINDOW=2     # Nombre de pages autour de la page courante

# Pagination par curseur
PAGINATION_CURSOR_PAGE_SIZE=20
```

### 💡 Utilisation

#### Pagination Standard

```python
from app.utils.pagination import paginate_query, Pagination

@app.route('/users')
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query.order_by(User.name)
    paginated = paginate_query(query, page=page, per_page=per_page)
    
    return render_template('users.html', users=paginated)
```

#### Décorateur @paginated_route

```python
from app.utils.optimizations import paginated_route

@app.route('/shifts')
@paginated_route(per_page=20, max_per_page=100)
def list_shifts():
    return Shift.query.order_by(Shift.start_time)
```

#### Pagination par Curseur

```python
from app.utils.pagination import paginate_cursor

@app.route('/api/users')
def api_users():
    cursor = request.args.get('cursor', None)
    
    query = User.query.order_by(User.id)
    paginated = paginate_cursor(query, cursor=cursor, page_size=20)
    
    return jsonify({
        'items': [u.to_dict() for u in paginated.items],
        'next_cursor': paginated.next_cursor,
        'has_more': paginated.has_more
    })
```

#### Pagination pour API JSON

```python
from app.utils.optimizations import paginated_api

@app.route('/api/shifts')
@paginated_api(per_page=20, model_name='Shift')
def api_shifts():
    return Shift.query.order_by(Shift.start_time)
```

#### Dans les Templates

```html
<!-- Afficher les items -->
{% for user in users %}
    <tr>
        <td>{{ user.name }}</td>
        <td>{{ user.email }}</td>
    </tr>
{% endfor %}

<!-- Afficher la pagination (Bulma) -->
{{ users.pagination_links() }}

<!-- Afficher la pagination (Simple) -->
{{ users.pagination_links(style='simple') }}

<!-- Accéder aux propriétés -->
Page {{ users.page }} sur {{ users.pages }}
Total: {{ users.total }} utilisateurs
```

#### Propriétés de l'Objet Pagination

```python
paginated.page          # Page courante (1-indexed)
paginated.per_page      # Nombre d'items par page
paginated.total         # Nombre total d'items
paginated.pages         # Nombre total de pages
paginated.items         # Liste des items de la page courante
paginated.has_next      # True s'il y a une page suivante
paginated.has_previous  # True s'il y a une page précédente
paginated.next_page     # Numéro de la page suivante
paginated.previous_page # Numéro de la page précédente
paginated.first_item    # Index du premier item
paginated.last_item     # Index du dernier item
```

### 📊 Pagination par Curseur vs Offset/Limit

| Critère | Offset/Limit | Curseur |
|---------|-------------|---------|
| **Performance** | ⚡⚡ (lent sur grandes tables) | ⚡⚡⚡⚡⚡ (rapide) |
| **Stabilité** | ⚡⚡⚡ (stable) | ⚡⚡ (peut sauter des éléments) |
| **Implémentation** | ⚡⚡⚡⚡⚡ (simple) | ⚡⚡⚡ (plus complexe) |
| **Requêtes SQL** | `SELECT * FROM table LIMIT 20 OFFSET 40` | `SELECT * FROM table WHERE id > 40 LIMIT 20` |
| **Utilisation** | Pages numérotées | Scroll infini |

**Recommandation** : Utilisez la pagination par curseur pour les grandes tables (> 10 000 lignes) ou pour le scroll infini.

---

## 🔄 Lazy Loading

### 📖 Aperçu

Le **lazy loading** (chargement paresseux) permet de **charger les données uniquement lorsqu'elles sont nécessaires**, réduisant ainsi la charge initiale et améliorant les performances.

### 🎯 Fonctionnalités

- ✅ **Propriétés lazy** : Calculées à la première utilisation
- ✅ **Méthodes lazy** : Résultats mis en cache par arguments
- ✅ **Collections lazy** : Chargement par batches
- ✅ **LazyLoader** : Pour le scroll infini
- ✅ **LazyQuery** : Requêtes SQLAlchemy différées
- ✅ **Intégration avec le cache** : Combinaison lazy loading + cache

### 🚀 Configuration

#### Variables d'Environnement

```bash
# Activation
LAZY_LOADING_ENABLED=true

# Taille des batches
LAZY_LOAD_DEFAULT_BATCH_SIZE=20

# Scroll infini
LAZY_LOAD_SCROLL_THRESHOLD=100  # pixels
LAZY_LOAD_DEBOUNCE_DELAY=300    # ms

# Logging
LAZY_LOAD_LOG_OPERATIONS=false
```

### 💡 Utilisation

#### Propriété Lazy

```python
from app.utils.lazy_loading import lazy_property

class User:
    @lazy_property
    def full_name(self):
        # Calculé uniquement à la première utilisation
        return f"{self.first_name} {self.last_name}"

    @lazy_property
    def shift_count(self):
        # Requête exécutée uniquement à la première utilisation
        return Shift.query.filter_by(user_id=self.id).count()
```

#### Méthode Lazy

```python
from app.utils.lazy_loading import lazy_method

class User:
    @lazy_method
    def get_shifts(self, start_date, end_date):
        # Résultat mis en cache par arguments
        return Shift.query.filter(
            Shift.user_id == self.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
```

#### LazyLoader pour Scroll Infini

```python
from app.utils.lazy_loading import LazyLoader

@app.route('/api/users')
def api_users():
    query = User.query.order_by(User.name)
    loader = LazyLoader(query, batch_size=20)
    
    cursor = request.args.get('cursor', None)
    batch = loader.load_next_batch(cursor)
    
    return jsonify({
        'items': [u.to_dict() for u in batch['items']],
        'next_cursor': batch['next_cursor'],
        'has_more': batch['has_more']
    })
```

#### LazyCollection

```python
from app.utils.lazy_loading import LazyCollection

# Créer une collection lazy
users = LazyCollection(User.query.order_by(User.name).all(), batch_size=20)

# Charger le premier batch
first_batch = users.next_batch()

# Itérer (charge automatiquement les batches)
for user in users:
    print(user.name)

# Accéder par index (charge le batch nécessaire)
user = users[150]  # Charge le batch contenant l'index 150
```

#### LazyQuery

```python
from app.utils.lazy_loading import LazyQuery

# Créer une requête lazy
query = LazyQuery(User.query.filter_by(is_active=True))

# La requête n'est pas exécutée ici

# Exécuter la requête
users = query.all()  # Charge maintenant

# Ou itérer
for user in query:  # Charge maintenant
    print(user.name)
```

#### Décorateur @lazy_route

```python
from app.utils.optimizations import lazy_route

@app.route('/api/shifts')
@lazy_route(batch_size=20, cursor_field='id')
def api_shifts():
    return Shift.query.order_by(Shift.id)
```

### 🎯 Lazy Loading avec SQLAlchemy

#### Éviter le N+1 avec joinedload

```python
from sqlalchemy.orm import joinedload

# ❌ MAUVAIS - Problème N+1
users = User.query.all()
for user in users:
    print(user.group.name)  # Requête supplémentaire pour chaque utilisateur

# ✅ BON - Eager loading
users = User.query.options(joinedload(User.group)).all()
for user in users:
    print(user.group.name)  # Pas de requête supplémentaire
```

#### Configuration des Relations

```python
from app.utils.lazy_loading import configure_lazy_loading_for_model
from sqlalchemy.orm import joinedload, selectinload

# Configurer le lazy loading pour un modèle
configure_lazy_loading_for_model(User, {
    'group': joinedload,
    'shifts': selectinload,
    'on_calls': joinedload,
    'leaves': selectinload
})
```

### 📊 Comparaison des Stratégies de Chargement

| Stratégie | Description | Quand l'utiliser | Performance |
|-----------|-------------|-----------------|-------------|
| **lazy** (par défaut) | Charge à la première utilisation | Relations rarement utilisées | ⚡⚡ |
| **joinedload** | JOIN SQL | Relations 1:1 ou 1:few | ⚡⚡⚡⚡ |
| **selectinload** | Requête séparée avec IN | Collections (1:N) | ⚡⚡⚡⚡ |
| **subqueryload** | Sous-requête | Collections avec filtrage | ⚡⚡⚡ |
| **noload** | Ne charge jamais | Relations jamais utilisées | ⚡⚡⚡⚡⚡ |

---

## 🔍 Monitoring des Performances

### 📖 Aperçu

Le **monitoring des performances** permet de **surveiller, analyser et optimiser** les performances de l'application en temps réel.

### 🎯 Fonctionnalités

- ✅ **Mesure du temps d'exécution** des requêtes
- ✅ **Détection des requêtes lentes**
- ✅ **Statistiques d'utilisation du cache** (hits/misses)
- ✅ **Analyse des requêtes SQL**
- ✅ **Métriques agrégées** (moyennes, totaux, etc.)
- ✅ **Logging périodique** des statistiques
- ✅ **Middleware Flask** pour un suivi automatique
- ✅ **Routes de monitoring** pour accéder aux métriques

### 🚀 Configuration

#### Variables d'Environnement

```bash
# Activation
PERFORMANCE_MONITORING_ENABLED=true

# Seuils
SLOW_QUERY_THRESHOLD=1.0      # secondes
PERFORMANCE_WARNING_THRESHOLD=0.5  # secondes

# Stockage
PERFORMANCE_MAX_REQUESTS_STORED=1000
PERFORMANCE_STATS_RETENTION=3600    # secondes

# Logging
PERFORMANCE_LOG_SLOW_QUERIES=true
PERFORMANCE_LOG_STATISTICS=true
PERFORMANCE_STATS_LOG_INTERVAL=60  # secondes
```

### 💡 Utilisation

#### Initialisation

```python
from app.utils.performance_monitor import init_performance_monitoring

# Initialiser le monitoring
init_performance_monitoring(app)
```

#### Décorateurs de Monitoring

```python
from app.utils.performance_monitor import monitor_performance, monitor_sql_queries

# Monitorer une route
@app.route('/expensive-route')
@monitor_performance
def expensive_route():
    return expensive_operation()

# Monitorer les requêtes SQL
@app.route('/users')
@monitor_sql_queries
def list_users():
    return User.query.all()
```

#### Middleware Flask

```python
from app.utils.performance_monitor import PerformanceMiddleware

# Enregistrer le middleware
app.wsgi_app = PerformanceMiddleware(app.wsgi_app)
```

#### Accéder aux Métriques

```python
from app.utils.performance_monitor import (
    get_performance_metrics,
    get_performance_summary,
    reset_performance_metrics
)

# Récupérer toutes les métriques
metrics = get_performance_metrics()

# Récupérer un résumé
summary = get_performance_summary()
# {'requests_per_second': 5.2, 'avg_request_duration_ms': 45.5, ...}

# Réinitialiser les métriques
reset_performance_metrics()
```

#### Routes de Monitoring

Après l'initialisation, les routes suivantes sont disponibles :

| Route | Description | Méthode |
|-------|-------------|---------|
| `/_performance/stats` | Toutes les métriques détaillées | GET |
| `/_performance/summary` | Résumé des performances | GET |
| `/_performance/reset` | Réinitialiser les métriques | POST |

Exemple de réponse de `/_performance/summary` :

```json
{
    "requests_per_second": 5.2,
    "avg_request_duration_ms": 45.5,
    "avg_sql_query_duration_ms": 12.3,
    "cache_hit_rate": 0.85,
    "slow_requests_percentage": 2.5,
    "sql_queries_per_request": 3.2
}
```

#### Monitoring Manuel

```python
from app.utils.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor.get_instance()

# Débuter une requête
request_id = monitor.start_request('/users', 'GET')

# Ajouter des requêtes SQL
monitor.add_sql_query('SELECT * FROM users', 0.05)
monitor.add_sql_query('SELECT * FROM groups WHERE id = ?', 0.02, {'id': 1})

# Ajouter des accès au cache
monitor.add_cache_access(hit=True)   # Hit
monitor.add_cache_access(hit=False)  # Miss

# Terminer la requête
metrics = monitor.end_request(200)

# Récupérer les métriques de la requête
print(f"Duration: {metrics.duration:.3f}s")
print(f"SQL queries: {len(metrics.sql_queries)}")
print(f"Cache hit rate: {metrics.cache_hit_rate:.2%}")
```

### 📊 Métriques Disponibles

#### Métriques par Requête (RequestMetrics)

```python
metrics.request_id      # Identifiant unique
metrics.path           # Chemin de la requête
metrics.method         # Méthode HTTP
metrics.start_time     # Heure de début
metrics.end_time       # Heure de fin
metrics.duration       # Durée totale en secondes
metrics.status_code    # Code de statut HTTP
metrics.is_slow        # True si lente (> seuil)
metrics.is_warning     # True si avertissement (> seuil warning)
metrics.cache_hits     # Nombre de hits cache
metrics.cache_misses   # Nombre de misses cache
metrics.cache_hit_rate # Taux de succès cache (0.0-1.0)
metrics.sql_queries    # Liste des requêtes SQL exécutées
metrics.memory_usage   # Utilisation mémoire (optionnel)
```

#### Métriques Agrégées (AggregatedMetrics)

```python
metrics.request_count          # Nombre total de requêtes
metrics.total_duration          # Durée totale de toutes les requêtes
metrics.avg_request_duration    # Durée moyenne par requête
metrics.requests_per_second     # Requêtes par seconde
metrics.sql_query_count         # Nombre total de requêtes SQL
metrics.sql_total_duration      # Durée totale des requêtes SQL
metrics.avg_sql_query_duration  # Durée moyenne par requête SQL
metrics.cache_hits              # Nombre total de hits cache
metrics.cache_misses            # Nombre total de misses cache
metrics.cache_hit_rate          # Taux de succès cache global
metrics.slow_requests           # Nombre de requêtes lentes
metrics.warning_requests       # Nombre de requêtes avec avertissement
metrics.requests_by_path        # Métriques par chemin
metrics.sql_queries_by_type     # Métriques par type de requête SQL
```

### 🎯 Bonnes Pratiques de Monitoring

1. **Surveiller les routes critiques** : Appliquez `@monitor_performance` aux routes les plus utilisées
2. **Détecter les goulots** : Utilisez les métriques pour identifier les requêtes lentes
3. **Optimiser le cache** : Vérifiez le `cache_hit_rate` et ajustez les TTL
4. **Analyser les requêtes SQL** : Identifiez les requêtes les plus lentes avec `sql_queries_by_type`
5. **Configurer les seuils** : Ajustez `SLOW_QUERY_THRESHOLD` selon votre application
6. **Logging périodique** : Activez `PERFORMANCE_LOG_STATISTICS` pour un suivi continu

---

## ⚡ Optimisations SQLAlchemy

### 📖 Aperçu

Les **optimisations SQLAlchemy** permettent de **réduire le nombre de requêtes** et d'**améliorer leurs performances**.

### 🎯 Fonctionnalités

- ✅ **Eager loading** : Éviter le problème N+1
- ✅ **Batch loading** : Charger plusieurs objets en une requête
- ✅ **Requêtes optimisées** : Filtrage, tri, limite
- ✅ **Index automatiques** : Création d'index pour les requêtes fréquentes
- ✅ **Décorateurs** : Appliquer les optimisations facilement

### 💡 Utilisation

#### Éviter le N+1 avec @eager_load

```python
from app.utils.optimizations import eager_load

@app.route('/user/<int:user_id>')
@eager_load(User, ['group', 'shifts', 'on_calls'])
def user_profile(user_id):
    user = User.query.get(user_id)
    # Toutes les relations sont déjà chargées
    return render_template('profile.html', user=user)
```

#### Batch Loading

```python
from app.utils.optimizations import batch_load

# ❌ MAUVAIS - N requêtes
user_ids = [1, 2, 3, 4, 5]
users = [User.query.get(id) for id in user_ids]

# ✅ BON - 1 requête
users = batch_load(User, user_ids, relationships=['group'])
# users = {1: <User 1>, 2: <User 2>, ...}
```

#### Optimisation de Requête

```python
from app.utils.optimizations import optimize_query

@app.route('/active-users')
@optimize_query(
    User,
    relationships=['group'],
    filters={'is_active': True},
    order_by='name',
    limit=100
)
def list_active_users():
    return User.query
```

#### Requêtes SQL Optimisées

```python
# ❌ MAUVAIS - Plusieurs requêtes
users = User.query.all()
active_users = [u for u in users if u.is_active]
sorted_users = sorted(active_users, key=lambda u: u.name)

# ✅ BON - Une seule requête optimisée
users = User.query.filter_by(is_active=True).order_by(User.name).all()
```

#### Utilisation des Index

Les modèles sont déjà configurés avec des index pour les requêtes fréquentes :

```python
# Dans app/models.py
class Shift(db.Model):
    __tablename__ = "shift"
    
    # Index simples
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    shift_type_id = db.Column(db.Integer, db.ForeignKey("shift_types.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Index composites
    __table_args__ = (
        db.Index('idx_shift_user_date', 'user_id', 'date'),
        db.Index('idx_shift_date_start', 'date', 'start_time'),
    )
```

Pour ajouter des index supplémentaires :

```python
# Ajouter un index après la création du modèle
from sqlalchemy import Index

# Créer un index composite
index = Index('idx_user_group_active', User.group_id, User.is_active)
index.create(db.engine)
```

### 📊 Optimisations Recommandées

| Problème | Solution | Gain de Performance |
|----------|----------|---------------------|
| N+1 Query | `joinedload` ou `selectinload` | ⚡⚡⚡⚡ |
| Requêtes lentes | Ajouter des index | ⚡⚡⚡⚡ |
| Chargement de collections | `selectinload` | ⚡⚡⚡ |
| Filtrage complexe | Utiliser `filter` au lieu de filtrer en Python | ⚡⚡⚡⚡ |
| Tri en Python | Utiliser `order_by` | ⚡⚡⚡⚡ |
| Limite en Python | Utiliser `limit` | ⚡⚡⚡ |

---

## 🎨 Configuration

### 📖 Configuration Centralisée

Toutes les configurations de performance peuvent être centralisées dans `config_performance.py` :

```python
from config_performance import PerformanceConfig, get_production_config

# Charger la configuration de production
config = get_production_config()

# Ou créer une configuration personnalisée
config = PerformanceConfig(
    cache=CacheSettings(
        cache_type=CacheType.REDIS,
        enabled=True,
        default_timeout=300,
        redis_url='redis://localhost:6379/0'
    ),
    pagination=PaginationSettings(
        enabled=True,
        default_per_page=20,
        max_per_page=100
    ),
    lazy_loading=LazyLoadingSettings(
        enabled=True,
        default_batch_size=20
    ),
    performance_monitoring=True
)

# Appliquer à l'application
config.configure(app)
```

### 📄 Fichier .env.example

```bash
# ============================================================================
# CONFIGURATION DES PERFORMANCES
# ============================================================================

# Cache
CACHE_TYPE=simple
CACHE_ENABLED=true
CACHE_DEFAULT_TIMEOUT=300
CACHE_MAX_ENTRIES=1000
CACHE_THRESHOLD=0.75
CACHE_KEY_PREFIX=leviia:
# CACHE_REDIS_URL=redis://localhost:6379/0
# CACHE_REDIS_PASSWORD=
# CACHE_REDIS_DB=0

# Pagination
PAGINATION_ENABLED=true
PAGINATION_DEFAULT_PER_PAGE=20
PAGINATION_MAX_PER_PAGE=100
PAGINATION_PER_PAGE_OPTIONS=[5, 10, 20, 50, 100]
PAGINATION_STYLE=bootstrap
PAGINATION_WINDOW=2

# Lazy Loading
LAZY_LOADING_ENABLED=true
LAZY_LOAD_DEFAULT_BATCH_SIZE=20
LAZY_LOAD_SCROLL_THRESHOLD=100
LAZY_LOAD_DEBOUNCE_DELAY=300
LAZY_LOAD_LOG_OPERATIONS=false

# Monitoring des Performances
PERFORMANCE_MONITORING_ENABLED=true
SLOW_QUERY_THRESHOLD=1.0
PERFORMANCE_WARNING_THRESHOLD=0.5
PERFORMANCE_MAX_REQUESTS_STORED=1000
PERFORMANCE_STATS_RETENTION=3600
PERFORMANCE_LOG_SLOW_QUERIES=true
PERFORMANCE_LOG_STATISTICS=true
PERFORMANCE_STATS_LOG_INTERVAL=60
```

### 🎯 Configurations Prédfinies

Le module `config_performance.py` fournit des configurations prédfinies :

```python
from config_performance import (
    get_development_config,
    get_production_config,
    get_testing_config
)

# Développement (cache désactivé, logging activé)
development_config = get_development_config()

# Production (Redis si disponible, monitoring activé)
production_config = get_production_config()

# Tests (tout désactivé pour des tests prévisibles)
testing_config = get_testing_config()
```

---

## 🚀 Bonnes Pratiques

### ✅ Cache

1. **Cachez les données fréquemment accédées** : Pages d'accueil, listes, données statiques
2. **Utilisez des TTL appropriés** : 60s pour les données volatiles, 300s-3600s pour les données stables
3. **Invalidez le cache lors des modifications** : Après CREATE, UPDATE, DELETE
4. **Utilisez des clés spécifiques** : Évitez les clés trop générales
5. **Choisissez le bon backend** : SimpleCache pour le dev, Redis pour la production
6. **Surveillez le cache hit rate** : Ajustez les TTL si le taux est trop bas

### ✅ Pagination

1. **Utilisez toujours la pagination** pour les listes de plus de 20 éléments
2. **Limitez le max_per_page** : 100 maximum pour éviter les requêtes trop lourdes
3. **Utilisez la pagination par curseur** pour les grandes tables (> 10 000 lignes)
4. **Affichez le nombre total** pour que l'utilisateur sache ce qu'il peut attendre
5. **Conservez les filtres** dans les liens de pagination
6. **Utilisez des tailles de page adaptatives** : 10 pour mobile, 20-50 pour desktop

### ✅ Lazy Loading

1. **Utilisez le lazy loading** pour les données rarement utilisées
2. **Chargez par batches** : 20-50 éléments par batch
3. **Implémentez le scroll infini** pour les longues listes
4. **Utilisez eager loading** pour éviter le N+1
5. **Évitez le lazy loading** pour les données toujours nécessaires
6. **Combinez avec le cache** pour de meilleures performances

### ✅ Requêtes SQLAlchemy

1. **Évitez le N+1** : Utilisez `joinedload` ou `selectinload`
2. **Utilisez des index** : Pour les colonnes fréquemment filtrées
3. **Limitez les résultats** : Toujours utiliser `limit` pour les listes
4. **Triez en base de données** : Utilisez `order_by` au lieu de trier en Python
5. **Filtrez en base de données** : Utilisez `filter` au lieu de filtrer en Python
6. **Utilisez batch loading** : Pour charger plusieurs objets
7. **Évitez les requêtes dans les boucles** : Préchargez les données nécessaires

### ✅ Monitoring

1. **Activez le monitoring** en production
2. **Surveillez les requêtes lentes** : Identifiez et optimisez les goulots
3. **Vérifiez le cache hit rate** : Ajustez les TTL si nécessaire
4. **Analysez les requêtes SQL** : Identifiez les requêtes les plus lentes
5. **Configurez des alertes** : Pour les requêtes trop lentes
6. **Loggez périodiquement** : Pour un suivi continu

---

## 📊 Exemples Complets

### Exemple 1 : Route avec Cache et Pagination

```python
from flask import render_template
from app.utils.optimizations import cached_route, paginated_route
from app.models import User

@app.route('/users')
@cached_route(timeout=60, vary_on=['group_id', 'is_active'])
@paginated_route(per_page=20)
def list_users():
    group_id = request.args.get('group_id', type=int)
    is_active = request.args.get('is_active', default=True, type=bool)
    
    query = User.query.order_by(User.name)
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    
    if is_active:
        query = query.filter_by(is_active=True)
    
    return query
```

### Exemple 2 : API JSON avec Lazy Loading

```python
from flask import jsonify
from app.utils.optimizations import lazy_route, paginated_api
from app.models import Shift

@app.route('/api/shifts')
@lazy_route(batch_size=20, cursor_field='id')
def api_shifts_lazy():
    """API avec lazy loading (scroll infini)"""
    return Shift.query.order_by(Shift.id)

@app.route('/api/shifts-paginated')
@paginated_api(per_page=20, model_name='Shift')
def api_shifts_paginated():
    """API avec pagination standard"""
    return Shift.query.order_by(Shift.start_time)
```

### Exemple 3 : Optimisation Complète d'une Route

```python
from flask import render_template
from app.utils.optimizations import (
    cached_route,
    paginated_route,
    eager_load,
    monitor_performance
)
from app.models import User, Shift, OnCall, Leave

@app.route('/user/<int:user_id>')
@monitor_performance
@cached_route(timeout=300)
@eager_load(User, ['group', 'shifts', 'on_calls', 'leaves'])
def user_profile(user_id):
    """
    Profile utilisateur avec :
    - Cache (300s)
    - Monitoring des performances
    - Eager loading des relations
    """
    user = User.query.get_or_404(user_id)
    
    # Toutes les relations sont déjà chargées grâce à @eager_load
    return render_template('profile.html', user=user)
```

### Exemple 4 : Fonction avec Cache et Lazy Loading

```python
from app.utils.optimizations import cache_result, lazy_property
from app.utils.lazy_loading import LazyLoader
from app.models import User, Shift

class UserService:
    @cache_result(timeout=300, key_func=lambda user_id: f'user_shifts:{user_id}')
    def get_user_shifts(self, user_id):
        """Récupère les shifts d'un utilisateur avec cache"""
        return Shift.query.filter_by(user_id=user_id).all()
    
    @lazy_property
    def expensive_calculation(self):
        """Calcul coûteux exécuté une seule fois"""
        # Simulation d'un calcul complexe
        return sum(1 for _ in range(1000000))
    
    def get_shifts_lazy(self, user_id):
        """Récupère les shifts avec lazy loading"""
        query = Shift.query.filter_by(user_id=user_id).order_by(Shift.start_time)
        loader = LazyLoader(query, batch_size=10)
        return loader
```

### Exemple 5 : Configuration Complète

```python
# Dans run.py ou app/__init__.py

from flask import Flask
from config_performance import PerformanceConfig, CacheType
from app.utils.cache import init_cache
from app.utils.performance_monitor import init_performance_monitoring

app = Flask(__name__)
app.config.from_object('config.Config')

# Configuration des performances
performance_config = PerformanceConfig(
    cache=CacheSettings(
        cache_type=CacheType.REDIS,
        enabled=True,
        default_timeout=300,
        redis_url='redis://localhost:6379/0'
    ),
    pagination=PaginationSettings(
        enabled=True,
        default_per_page=20,
        max_per_page=100,
        style='bootstrap'
    ),
    lazy_loading=LazyLoadingSettings(
        enabled=True,
        default_batch_size=20
    ),
    performance_monitoring=True
)

# Appliquer la configuration
performance_config.configure(app)

# Initialiser le cache
init_cache(app)

# Initialiser le monitoring
init_performance_monitoring(app)

# ... reste de l'initialisation
```

---

## 🔧 Dépannage

### ❌ Problèmes Courants et Solutions

#### Le cache ne fonctionne pas

**Symptômes** : Les données ne sont pas mises en cache ou ne sont pas récupérées depuis le cache.

**Solutions** :
1. Vérifiez que `CACHE_ENABLED=true`
2. Vérifiez que le backend de cache est correctement configuré
3. Vérifiez que les clés de cache sont correctes
4. Pour Redis/Memcached, vérifiez que le service est en cours d'exécution
5. Vérifiez les logs pour les erreurs de connexion

```bash
# Tester Redis
redis-cli ping
# Doit retourner "PONG"

# Tester Memcached
telnet localhost 11211
# Doit se connecter
```

#### La pagination ne fonctionne pas

**Symptômes** : Tous les éléments sont retournés sur une seule page.

**Solutions** :
1. Vérifiez que `PAGINATION_ENABLED=true`
2. Vérifiez que les paramètres `page` et `per_page` sont correctement passés
3. Vérifiez que la requête retourne un objet Query SQLAlchemy
4. Vérifiez que le template utilise `paginated.items` et non `paginated` directement

#### Le lazy loading ne fonctionne pas

**Symptômes** : Toutes les données sont chargées immédiatement.

**Solutions** :
1. Vérifiez que `LAZY_LOADING_ENABLED=true`
2. Vérifiez que vous utilisez `LazyLoader`, `LazyCollection` ou `LazyQuery`
3. Vérifiez que vous n'itérez pas sur toute la collection immédiatement
4. Pour le scroll infini, vérifiez que le curseur est correctement passé

#### Les requêtes sont toujours lentes

**Symptômes** : Les temps de réponse restent élevés malgré les optimisations.

**Solutions** :
1. Activez le monitoring : `PERFORMANCE_MONITORING_ENABLED=true`
2. Vérifiez les métriques : `/_performance/stats`
3. Identifiez les requêtes lentes avec `sql_queries_by_type`
4. Ajoutez des index sur les colonnes fréquemment filtrées
5. Utilisez `EXPLAIN ANALYZE` pour analyser les requêtes SQL
6. Vérifiez que vous utilisez `joinedload`/`selectinload` pour éviter le N+1

#### Problème N+1

**Symptômes** : Beaucoup de requêtes SQL similaires (ex: `SELECT * FROM group WHERE id = ?`).

**Solutions** :
1. Utilisez `@eager_load` sur la route
2. Utilisez `joinedload` ou `selectinload` dans les requêtes
3. Utilisez `batch_load` pour charger plusieurs objets
4. Vérifiez avec le monitoring que le nombre de requêtes SQL par requête HTTP est raisonnable

### 🐛 Débogage

#### Activer le Logging

```python
import logging

# Activer le logging pour les optimisations
logging.getLogger('cache').setLevel(logging.DEBUG)
logging.getLogger('pagination').setLevel(logging.DEBUG)
logging.getLogger('lazy_loading').setLevel(logging.DEBUG)
logging.getLogger('optimizations').setLevel(logging.DEBUG)
logging.getLogger('performance').setLevel(logging.DEBUG)
```

#### Vérifier les Requêtes SQL

```python
# Dans config.py
SQLALCHEMY_ECHO = True  # Affiche toutes les requêtes SQL
```

#### Utiliser le Monitoring

```python
from app.utils.performance_monitor import get_performance_summary

# Récupérer un résumé
summary = get_performance_summary()
print(f"Requêtes par seconde: {summary['requests_per_second']}")
print(f"Temps moyen: {summary['avg_request_duration_ms']}ms")
print(f"Taux de cache: {summary['cache_hit_rate']:.2%}")
```

#### Tester les Optimisations

```python
# Tester le cache
from app.utils.cache import cache

cache.set('test_key', 'test_value', timeout=60)
value = cache.get('test_key')
assert value == 'test_value'

# Tester la pagination
from app.utils.pagination import paginate_query
from app.models import User

query = User.query.order_by(User.name)
paginated = paginate_query(query, page=1, per_page=10)
assert len(paginated.items) <= 10

# Tester le lazy loading
from app.utils.lazy_loading import LazyCollection

items = list(range(100))
lazy_items = LazyCollection(items, batch_size=10)
first_batch = lazy_items.next_batch()
assert len(first_batch) == 10
```

---

## 📝 Changelog

### Version 1.0 (Juin 2025)

**Nouveautés** :
- ✅ Système de cache multi-backend (SimpleCache, Redis, Memcached)
- ✅ Pagination avancée (standard, curseur, lazy loading)
- ✅ Lazy loading pour les collections et requêtes
- ✅ Monitoring complet des performances
- ✅ Optimisations SQLAlchemy (eager loading, batch loading)
- ✅ Configuration centralisée dans `config_performance.py`
- ✅ Décorateurs pour une utilisation facile
- ✅ Documentation complète

**Améliorations** :
- Optimisation des requêtes existantes avec `joinedload`
- Ajout d'index composites sur les modèles
- Configuration via variables d'environnement

**Corrections** :
- Fix des problèmes de N+1 dans les routes existantes
- Optimisation des requêtes de pagination

---

## 📚 Ressources Supplémentaires

- [Documentation Flask-Caching](https://pythonhosted.org/Flask-Caching/)
- [Documentation SQLAlchemy ORM](https://docs.sqlalchemy.org/en/14/orm/)
- [Optimisation des Performances Web](https://web.dev/performance/)
- [Redis Documentation](https://redis.io/documentation)
- [Memcached Documentation](https://github.com/memcached/memcached/wiki)

---

## 🙏 Contribution

Les contributions sont les bienvenues ! Pour contribuer aux optimisations de performance :

1. **Identifiez un goulot** : Utilisez le monitoring pour trouver les problèmes
2. **Proposez une solution** : Créez une issue avec vos idées
3. **Implémentez la solution** : Fork, codez, testez
4. **Soumettez une PR** : Avec des tests et de la documentation

---

## 📜 Licence

Ce document fait partie de **Leviia Schedule** et est sous licence **CeCILL v2.1**. Voir le fichier [LICENSE](../LICENSE) pour plus de détails.

---

> **⚠️ Note** : Les optimisations de performance doivent être testées dans votre environnement spécifique. Les valeurs par défaut peuvent ne pas être optimales pour toutes les configurations.

> **💡 Conseil** : Commencez par activer le monitoring et analyser les métriques avant d'appliquer des optimisations. Cela vous aidera à identifier les vrais goulots d'étranglement.
