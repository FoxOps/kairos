# Variables d'Environnement - Leviia Schedule

> **Documentation complète de toutes les variables d'environnement disponibles pour configurer Leviia Schedule**

---

## 📋 Table des Matières

- [🔐 Configuration de Base Flask](#-configuration-de-base-flask)
- [🗄️ Configuration de la Base de Données](#️-configuration-de-la-base-de-données)
- [🔒 Configuration d'Authentification](#-configuration-dauthentification)
- [⚠️ Configuration des Erreurs](#️-configuration-des-erreurs)
- [📝 Configuration du Logging](#-configuration-du-logging)
- [🔒 Configuration de Sécurité](#-configuration-de-sécurité)
- [📊 Configuration des Données par Défaut](#-configuration-des-données-par-défaut)
- [📅 Configuration des Types de Shifts](#-configuration-des-types-de-shifts)
- [📤 Configuration de l'Export ICS](#-configuration-de-lexport-ics)
- [📧 Configuration des Notifications](#-configuration-des-notifications)
- [🧹 Configuration du Nettoyage Automatique](#-configuration-du-nettoyage-automatique)
- [⚡ Configuration des Performances](#-configuration-des-performances)
  - [Cache](#cache)
  - [Pagination](#pagination)
  - [Lazy Loading](#lazy-loading)
  - [Optimisation des Requêtes](#optimisation-des-requêtes)
  - [Monitoring des Performances](#monitoring-des-performances)
- [🎯 Configuration par Environnement](#-configuration-par-environnement)
- [📝 Exemples de Configuration](#-exemples-de-configuration)
- [⚠️ Bonnes Pratiques](#️-bonnes-pratiques)

---

## 🔐 Configuration de Base Flask

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `SECRET_KEY` | string | `ta-cle-secrete-ici` | Clé secrète pour Flask. **Doit être longue, aléatoire et gardée secrète en production**. Générez avec : `python -c "import secrets; print(secrets.token_hex(32))"` | ✅ Oui |
| `FLASK_ENV` | string | `development` | Environnement Flask. Valeurs possibles : `development`, `production`, `testing` | ❌ Non |
| `FLASK_TESTING` | booléen | `false` | Mode test activé. Utilisé pour les tests unitaires | ❌ Non |

**Exemple :**
```bash
SECRET_KEY=ma_cle_secrete_generée_avec_python_secrets
FLASK_ENV=production
FLASK_TESTING=false
```

---

## 🗄️ Configuration de la Base de Données

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `DATABASE_URL` | string | `sqlite:///app.db` | URI de la base de données. Formats supportés : SQLite, PostgreSQL, MySQL | ✅ Oui |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | booléen | `false` | Désactive le suivi des modifications SQLAlchemy (recommandé : `false`) | ❌ Non |
| `SQLALCHEMY_ECHO` | booléen | `false` | Affiche les requêtes SQL dans les logs (utile pour le débogage) | ❌ Non |
| `SQLALCHEMY_ENGINE_OPTIONS` | JSON | `{}` | Options du moteur SQLAlchemy au format JSON. Exemple : `{"connect_args": {"timeout": 30}, "pool_pre_ping": true, "pool_recycle": 3600}` | ❌ Non |
| `DATABASE_POOL_SIZE` | entier | `5` | Taille du pool de connexions à la base de données | ❌ Non |
| `DATABASE_MAX_OVERFLOW` | entier | `10` | Nombre maximal de connexions supplémentaires | ❌ Non |
| `DATABASE_CONNECT_TIMEOUT` | entier | `30` | Délai d'attente pour la connexion à la base de données (en secondes) | ❌ Non |
| `DATABASE_POOL_RECYCLE` | entier | `3600` | Recycle les connexions après ce nombre de secondes | ❌ Non |

**Formats DATABASE_URL :**
```bash
# SQLite (par défaut)
DATABASE_URL=sqlite:///chemin/vers/app.db

# PostgreSQL (recommandé pour la production)
DATABASE_URL=postgresql://utilisateur:motdepasse@hote:port/base_de_donnees

# MySQL
DATABASE_URL=mysql://utilisateur:motdepasse@hote:port/base_de_donnees

# SQLite en mémoire (pour les tests)
DATABASE_URL=sqlite:///:memory:
```

---

## 🔒 Configuration d'Authentification

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `LOGIN_DISABLED` | booléen | `false` | **DANGER** : Désactive complètement l'authentification. Ne jamais activer en production ! | ❌ Non |
| `REMEMBER_COOKIE_DURATION` | entier | `86400` | Durée du cookie "se souvenir de moi" en secondes (par défaut : 1 jour = 86400) | ❌ Non |
| `SESSION_PROTECTION` | string | `strong` | Niveau de protection de session. Valeurs possibles : `none`, `basic`, `strong` | ❌ Non |
| `WTF_CSRF_ENABLED` | booléen | `true` | Active la protection CSRF pour les formulaires | ❌ Non |
| `WTF_CSRF_TIME_LIMIT` | entier | `3600` | Durée de validité du token CSRF en secondes (par défaut : 1 heure) | ❌ Non |
| `SESSION_COOKIE_SECURE` | booléen | `false` | Active le flag Secure pour les cookies de session (recommandé : `true` en production avec HTTPS) | ❌ Non |
| `SESSION_COOKIE_HTTPONLY` | booléen | `true` | Active le flag HttpOnly pour les cookies de session | ❌ Non |
| `SESSION_COOKIE_SAMESITE` | string | `Lax` | Politique SameSite pour les cookies. Valeurs possibles : `Lax`, `Strict`, `None` | ❌ Non |
| `REMEMBER_COOKIE_SECURE` | booléen | `false` | Active le flag Secure pour le cookie "se souvenir de moi" | ❌ Non |
| `PREFERRED_URL_SCHEME` | string | `http` | Schéma URL préféré. Valeurs possibles : `http`, `https` | ❌ Non |

---

## ⚠️ Configuration des Erreurs

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `DEBUG_ERRORS` | booléen | `false` | **DANGER** : Affiche les détails des erreurs (stack traces). Ne jamais activer en production ! | ❌ Non |
| `SHOW_CUSTOM_ERROR_PAGES` | booléen | `true` | Affiche les pages d'erreur personnalisées | ❌ Non |
| `ERROR_500_MESSAGE` | string | `"Une erreur interne du serveur s'est produite. Veuillez reessayer plus tard."` | Message personnalisé pour les erreurs 500 | ❌ Non |
| `ERROR_503_MESSAGE` | string | `"Service temporairement indisponible. Veuillez reessayer dans quelques instants."` | Message personnalisé pour les erreurs 503 | ❌ Non |
| `ERROR_503_RETRY_AFTER` | entier | `300` | Délai de réessai pour les erreurs 503 (en secondes) | ❌ Non |

---

## 📝 Configuration du Logging

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `LOG_LEVEL` | string | `INFO` | Niveau de log principal. Valeurs possibles : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | ❌ Non |
| `LOG_DIR` | string | `logs` | Dossier des logs (relatif au répertoire du projet ou chemin absolu) | ❌ Non |
| `LOG_FILE_SIZE` | entier | `5242880` | Taille maximale des fichiers de log en octets (par défaut : 5 Mo) | ❌ Non |
| `LOG_BACKUP_COUNT` | entier | `10` | Nombre de fichiers de backup à conserver | ❌ Non |
| `LOG_FILE_APP` | string | `leviia-app.log` | Nom du fichier de log pour l'application | ❌ Non |
| `LOG_FILE_ERRORS` | string | `leviia-errors.log` | Nom du fichier de log pour les erreurs | ❌ Non |
| `LOG_FILE_HTTP` | string | `leviia-http-errors.log` | Nom du fichier de log pour les erreurs HTTP | ❌ Non |
| `LOG_FILE_DEBUG` | string | `leviia-debug.log` | Nom du fichier de log pour le débogage | ❌ Non |
| `LOG_FILE_AUDIT` | string | `leviia-audit.log` | Nom du fichier de log pour l'audit | ❌ Non |
| `LOG_LEVEL_APP` | string | `LOG_LEVEL` | Niveau de log pour l'application | ❌ Non |
| `LOG_LEVEL_ERRORS` | string | `ERROR` | Niveau de log pour les erreurs | ❌ Non |
| `LOG_LEVEL_HTTP` | string | `WARNING` | Niveau de log pour les erreurs HTTP | ❌ Non |
| `LOG_LEVEL_DEBUG` | string | `DEBUG` | Niveau de log pour le débogage | ❌ Non |
| `LOG_LEVEL_AUDIT` | string | `INFO` | Niveau de log pour l'audit | ❌ Non |
| `LOG_FORMAT` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Format des logs | ❌ Non |
| `LOG_DATE_FORMAT` | string | `%Y-%m-%d %H:%M:%S` | Format de la date dans les logs | ❌ Non |
| `SYSLOG_ENABLED` | booléen | `false` | Active le syslog pour la production | ❌ Non |
| `SYSLOG_ADDRESS` | string | `/dev/log` | Adresse du syslog (pour Unix : `/dev/log`, pour réseau : `localhost:514`) | ❌ Non |
| `SYSLOG_FACILITY` | string | `local0` | Facility syslog. Valeurs possibles : `local0`, `local1`, ..., `local7`, `user`, `daemon`, etc. | ❌ Non |
| `LOG_FILTER_SENSITIVE` | booléen | `true` | Filtre les données sensibles dans les logs (recommandé : `true`) | ❌ Non |
| `LOG_FILTER_PATTERNS` | string | `"password,secret,token,api_key,auth"` | Patterns supplémentaires pour le filtrage des données sensibles (séparés par des virgules) | ❌ Non |

---

## 🔒 Configuration de Sécurité

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `SEND_FILE_MAX_AGE_DEFAULT` | entier | `0` | Désactive le cache pour les pages d'erreur (recommandé : `0`) | ❌ Non |
| `CORS_ENABLED` | booléen | `false` | Active CORS (Cross-Origin Resource Sharing) | ❌ Non |
| `RATE_LIMIT_ENABLED` | booléen | `true` | Active la limitation de débit (rate limiting) | ❌ Non |
| `RATE_LIMIT_DEFAULT` | string | `"200 per day, 50 per hour"` | Limites de débit par défaut au format Flask-Limiter | ❌ Non |
| `COMPRESS_ENABLED` | booléen | `true` | Active la compression Gzip des réponses | ❌ Non |
| `COMPRESS_MIMETYPES` | liste | Voir code | Types MIME à compresser. Par défaut : `['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']` | ❌ Non |

---

## 📊 Configuration des Données par Défaut

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `DEFAULT_ADMIN_EMAIL` | string | `admin@leviia.local` | Email de l'utilisateur admin par défaut | ❌ Non |
| `DEFAULT_ADMIN_PASSWORD` | string | `admin123` | **DANGER** : Mot de passe de l'utilisateur admin par défaut. **Changez cette valeur après la première connexion !** | ❌ Non |
| `DEFAULT_GROUP_NAME` | string | `Defaut` | Nom du groupe par défaut | ❌ Non |
| `DEFAULT_GROUP_IN_SCHEDULE` | booléen | `true` | Le groupe par défaut fait partie du planning | ❌ Non |
| `DEFAULT_GROUP_IN_ONCALL` | booléen | `true` | Le groupe par défaut fait partie des astreintes | ❌ Non |

---

## 📅 Configuration des Types de Shifts

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `DEFAULT_SHIFT_TYPES` | JSON | Voir code | Types de shifts par défaut au format JSON. Exemple : `[{"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15}, {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17}]` | ❌ Non |

**Valeur par défaut :**
```json
[
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21}
]
```

---

## 📤 Configuration de l'Export ICS

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `ICS_TOKEN_EXPIRY_DAYS` | entier | `365` | Durée de validité du token ICS en jours | ❌ Non |

---

## 📧 Configuration des Notifications

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `NOTIFICATIONS_ENABLED` | booléen | `false` | Active les notifications par email (non implémenté actuellement) | ❌ Non |
| `NOTIFICATION_FROM_EMAIL` | string | `""` | Adresse email de l'expéditeur | ❌ Non |
| `SMTP_HOST` | string | `""` | Serveur SMTP | ❌ Non |
| `SMTP_PORT` | entier | `587` | Port SMTP | ❌ Non |
| `SMTP_USERNAME` | string | `""` | Nom d'utilisateur SMTP | ❌ Non |
| `SMTP_PASSWORD` | string | `""` | Mot de passe SMTP | ❌ Non |
| `SMTP_USE_TLS` | booléen | `true` | Utiliser TLS pour la connexion SMTP | ❌ Non |

---

## 🧹 Configuration du Nettoyage Automatique

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `DATA_CLEANUP_ENABLED` | booléen | `false` | **Désactivé par défaut pour la sécurité**. Active le nettoyage automatique des données | ❌ Non |
| `DATA_CLEANUP_RETENTION` | string | `"365d"` | Durée de rétention des données. Formats supportés : `1y` (1 an), `6m` (6 mois), `30d` (30 jours), ou un nombre de jours | ❌ Non |
| `DATA_CLEANUP_RETENTION_DAYS` | entier | `365` | Durée de rétention en jours (alternative à DATA_CLEANUP_RETENTION) | ❌ Non |
| `DATA_CLEANUP_BATCH_SIZE` | entier | `1000` | Taille des lots pour la suppression | ❌ Non |
| `DATA_CLEANUP_SCHEDULE` | string | `"0 0 * * *"` | Planification cron pour le nettoyage (par défaut : tous les jours à minuit) | ❌ Non |

**Exemples de planification cron :**
```bash
# Tous les jours à minuit
DATA_CLEANUP_SCHEDULE="0 0 * * *"

# Tous les lundis à 2h
DATA_CLEANUP_SCHEDULE="0 2 * * 1"

# Tous les 1er du mois à minuit
DATA_CLEANUP_SCHEDULE="0 0 1 * *"
```

---

## ⚡ Configuration des Performances

### Cache

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `CACHE_TYPE` | string | `simple` | Type de cache. Valeurs possibles : `simple` (en mémoire), `redis`, `memcached` | ❌ Non |
| `CACHE_ENABLED` | booléen | `true` | Active/désactive le cache globalement | ❌ Non |
| `CACHE_DEFAULT_TIMEOUT` | entier | `300` | Durée de vie par défaut des entrées de cache (en secondes) | ❌ Non |
| `CACHE_MAX_ENTRIES` | entier | `1000` | Nombre maximal d'entrées pour SimpleCache | ❌ Non |
| `CACHE_THRESHOLD` | float | `0.75` | Seuil pour déclencher le nettoyage automatique du cache (0.0 à 1.0) | ❌ Non |
| `CACHE_KEY_PREFIX` | string | `leviia:` | Préfixe pour toutes les clés de cache | ❌ Non |
| `CACHE_REDIS_URL` | string | `None` | URL Redis au format `redis://hote:port/db`. Exemple : `redis://localhost:6379/0` | ❌ Non |
| `CACHE_REDIS_PASSWORD` | string | `None` | Mot de passe Redis | ❌ Non |
| `CACHE_REDIS_DB` | entier | `0` | Numéro de base de données Redis | ❌ Non |
| `CACHE_REDIS_SOCKET_TIMEOUT` | entier | `5` | Délai d'attente pour les opérations socket Redis (en secondes) | ❌ Non |
| `CACHE_REDIS_CONNECT_TIMEOUT` | entier | `5` | Délai d'attente pour la connexion Redis (en secondes) | ❌ Non |
| `CACHE_MEMCACHED_SERVERS` | JSON | `[]` | Liste des serveurs Memcached au format JSON. Exemple : `[['localhost', 11211]]` | ❌ Non |
| `CACHE_MEMCACHED_USERNAME` | string | `None` | Nom d'utilisateur Memcached | ❌ Non |
| `CACHE_MEMCACHED_PASSWORD` | string | `None` | Mot de passe Memcached | ❌ Non |

### Pagination

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `PAGINATION_ENABLED` | booléen | `true` | Active/désactive la pagination | ❌ Non |
| `PAGINATION_DEFAULT_PER_PAGE` | entier | `20` | Nombre d'éléments par page par défaut | ❌ Non |
| `PAGINATION_MAX_PER_PAGE` | entier | `100` | Nombre maximal d'éléments par page | ❌ Non |
| `PAGINATION_PER_PAGE_OPTIONS` | JSON | `[5, 10, 20, 50, 100]` | Options disponibles pour le nombre d'éléments par page | ❌ Non |
| `PAGINATION_STYLE` | string | `bulma` | Style des liens de pagination. Valeurs possibles : `bulma`, `simple`, `none` | ❌ Non |
| `PAGINATION_WINDOW` | entier | `2` | Nombre de pages à afficher autour de la page courante | ❌ Non |
| `PAGINATION_CURSOR_PAGE_SIZE` | entier | `20` | Taille de page pour la pagination par curseur | ❌ Non |

### Lazy Loading

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `LAZY_LOADING_ENABLED` | booléen | `true` | Active/désactive le lazy loading | ❌ Non |
| `LAZY_LOAD_DEFAULT_BATCH_SIZE` | entier | `20` | Taille des batches par défaut pour le lazy loading | ❌ Non |
| `LAZY_LOAD_SCROLL_THRESHOLD` | entier | `100` | Seuil en pixels pour déclencher le chargement lors du scroll | ❌ Non |
| `LAZY_LOAD_DEBOUNCE_DELAY` | entier | `300` | Délai de debounce en millisecondes pour éviter les chargements multiples | ❌ Non |
| `LAZY_LOAD_LOG_OPERATIONS` | booléen | `false` | Active le logging des opérations de lazy loading | ❌ Non |

### Optimisation des Requêtes

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `QUERY_OPTIMIZATION_USE_JOINEDLOAD` | booléen | `true` | Utilise joinedload pour éviter le problème N+1 | ❌ Non |
| `QUERY_OPTIMIZATION_USE_SELECTINLOAD` | booléen | `true` | Utilise selectinload pour les collections | ❌ Non |

### Monitoring des Performances

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `PERFORMANCE_MONITORING_ENABLED` | booléen | `false` | Active le monitoring des performances | ❌ Non |
| `SLOW_QUERY_THRESHOLD` | float | `1.0` | Seuil en secondes pour considérer une requête comme lente | ❌ Non |
| `PERFORMANCE_WARNING_THRESHOLD` | float | `0.5` | Seuil en secondes pour les avertissements de performance | ❌ Non |
| `PERFORMANCE_MAX_REQUESTS_STORED` | entier | `1000` | Nombre maximal de requêtes stockées en mémoire pour le monitoring | ❌ Non |
| `PERFORMANCE_STATS_RETENTION` | entier | `3600` | Durée de conservation des statistiques (en secondes) | ❌ Non |
| `PERFORMANCE_LOG_SLOW_QUERIES` | booléen | `true` | Active le logging des requêtes lentes | ❌ Non |
| `PERFORMANCE_LOG_STATISTICS` | booléen | `true` | Active le logging des statistiques de performance | ❌ Non |
| `PERFORMANCE_STATS_LOG_INTERVAL` | entier | `60` | Intervalle de logging des statistiques (en secondes) | ❌ Non |

---

## 🎯 Configuration par Environnement

Le projet fournit trois configurations prédéfinies :

### Développement (`DevelopmentConfig`)
- `DEBUG = True`
- `DEBUG_ERRORS = True`
- `LOG_LEVEL = DEBUG`
- `SQLALCHEMY_ECHO = True` (affiche les requêtes SQL)

**Activation :**
```bash
FLASK_ENV=development
```

### Production (`ProductionConfig`)
- `DEBUG = False`
- `DEBUG_ERRORS = False`
- `LOG_LEVEL = WARNING`
- `SQLALCHEMY_ECHO = False`

**Activation :**
```bash
FLASK_ENV=production
```

### Test (`TestingConfig`)
- `TESTING = True`
- `SQLALCHEMY_DATABASE_URI = sqlite:///:memory:`
- `WTF_CSRF_ENABLED = False`
- `LOG_LEVEL = DEBUG`
- `DEBUG_ERRORS = True`
- `RATE_LIMIT_ENABLED = False`
- `COMPRESS_ENABLED = False`

**Activation :**
```bash
FLASK_ENV=testing
```

---

## 📝 Exemples de Configuration

### Configuration pour la Production avec PostgreSQL

```bash
# Configuration de base
FLASK_ENV=production
SECRET_KEY=votre_cle_secrete_aleatoire_ici

# Base de données PostgreSQL
DATABASE_URL=postgresql://leviia_user:motdepasse_secure@localhost:5432/leviia_db

# Logging
LOG_LEVEL=WARNING
SYSLOG_ENABLED=true
SYSLOG_ADDRESS=/dev/log

# Sécurité
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
CORS_ENABLED=false
DEBUG_ERRORS=false

# Performances
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
PERFORMANCE_MONITORING_ENABLED=true

# Nettoyage automatique (optionnel)
DATA_CLEANUP_ENABLED=true
DATA_CLEANUP_RETENTION=1y
DATA_CLEANUP_SCHEDULE="0 0 * * *"
```

### Configuration pour le Développement

```bash
FLASK_ENV=development
SECRET_KEY=dev_secret_key

# Base de données SQLite
DATABASE_URL=sqlite:///app.db

# Logging détaillé
LOG_LEVEL=DEBUG
SQLALCHEMY_ECHO=true
DEBUG_ERRORS=true

# Désactiver la sécurité pour le développement
SESSION_COOKIE_SECURE=false
CORS_ENABLED=true

# Désactiver le cache en développement
CACHE_ENABLED=false
```

### Configuration pour les Tests

```bash
FLASK_ENV=testing
FLASK_TESTING=true
SECRET_KEY=test_secret_key

# Base de données en mémoire
DATABASE_URL=sqlite:///:memory:

# Désactiver les fonctionnalités de production
WTF_CSRF_ENABLED=false
RATE_LIMIT_ENABLED=false
COMPRESS_ENABLED=false
CORS_ENABLED=true

# Logging
LOG_LEVEL=DEBUG
DEBUG_ERRORS=true
```

### Configuration avec Redis et Cache

```bash
# Cache Redis
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_PASSWORD=votre_motdepasse_redis
CACHE_REDIS_DB=0
CACHE_DEFAULT_TIMEOUT=300
CACHE_ENABLED=true

# Pagination
PAGINATION_ENABLED=true
PAGINATION_DEFAULT_PER_PAGE=20
PAGINATION_MAX_PER_PAGE=100

# Lazy Loading
LAZY_LOADING_ENABLED=true
LAZY_LOAD_DEFAULT_BATCH_SIZE=20

# Monitoring
PERFORMANCE_MONITORING_ENABLED=true
SLOW_QUERY_THRESHOLD=1.0
```

---

## ⚠️ Bonnes Pratiques

### 🔐 Sécurité

1. **SECRET_KEY** : Toujours utiliser une clé longue et aléatoire en production. Ne jamais commiter cette valeur dans Git.
   ```bash
   # Générer une clé sécurisée
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **DEFAULT_ADMIN_PASSWORD** : Toujours changer le mot de passe admin après la première connexion.

3. **Base de données** : En production, ne jamais utiliser SQLite avec plusieurs processus workers. Utilisez PostgreSQL ou MySQL.

4. **Variables sensibles** : Ne jamais stocker de mots de passe ou clés secrètes dans le fichier `.env` commité dans Git. Utilisez les variables d'environnement du système ou un service de gestion des secrets.

5. **HTTPS** : En production, toujours utiliser HTTPS et activer `SESSION_COOKIE_SECURE=true`.

### 📁 Fichier .env

1. **Création** : Copiez le fichier `.env.example` en `.env` et modifiez les valeurs :
   ```bash
   cp .env.example .env
   ```

2. **Git** : Ajoutez `.env` à votre fichier `.gitignore` pour éviter de commiter des informations sensibles.

3. **Production** : En production, il est recommandé de définir les variables directement dans l'environnement du système plutôt que d'utiliser un fichier `.env`.

### 🐳 Docker

Pour les environnements Docker, vous pouvez :

1. **Monter le fichier .env** :
   ```yaml
   # docker-compose.yml
   services:
     app:
       image: leviia-schedule
       env_file:
         - .env
   ```

2. **Passer les variables directement** :
   ```yaml
   # docker-compose.yml
   services:
     app:
       image: leviia-schedule
       environment:
         - SECRET_KEY=votre_cle
         - DATABASE_URL=postgresql://user:pass@db:5432/leviia
   ```

3. **Utiliser Docker secrets** pour les informations sensibles.

### 🔄 Variables Booléennes

Les variables booléennes acceptent les valeurs suivantes (insensibles à la casse) :
- Vrai : `true`, `True`, `TRUE`, `1`, `yes`, `Yes`, `YES`, `y`, `on`
- Faux : `false`, `False`, `FALSE`, `0`, `no`, `No`, `NO`, `n`, `off`

### 📊 Types de Données

| Type | Format | Exemple |
|------|--------|---------|
| Booléen | true/false, 1/0, yes/no | `true`, `false`, `1`, `0` |
| Entier | Nombre entier | `300`, `86400` |
| Float | Nombre décimal | `0.75`, `1.5` |
| String | Texte | `"leviia:"`, `"INFO"` |
| JSON | Objet ou tableau JSON | `{"key": "value"}`, `[1, 2, 3]` |
| Liste | Valeurs séparées par des virgules | `"password,secret,token"` |

---

## 📚 Références

- [Documentation Flask](https://flask.palletsprojects.com/)
- [Documentation SQLAlchemy](https://www.sqlalchemy.org/)
- [Documentation python-dotenv](https://saurabh-kumar.com/python-dotenv/)
- [Configuration des performances](config_performance.py)
- [Configuration principale](config.py)

---

*Dernière mise à jour : 2024*
*Ce fichier documente toutes les variables d'environnement disponibles dans Leviia Schedule.*
