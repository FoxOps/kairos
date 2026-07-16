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
- [💾 Configuration des Sauvegardes](#-configuration-des-sauvegardes)
- [🧹 Configuration du Nettoyage Automatique](#-configuration-du-nettoyage-automatique)
- [⚡ Configuration du Cache](#-configuration-du-cache)
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
| `PUBLIC_BASE_URL` | string | (vide) | URL publique de l'app derrière un reverse proxy (ex: `https://schedule.example.com`). Sert de repli pour les liens absolus (export ICS) quand le proxy ne transmet pas `X-Forwarded-Host` correctement à `ProxyFix` — sinon ces liens exposent l'IP/le nom interne du backend au lieu du bon domaine. Laisser vide pour utiliser `request.host_url` (comportement par défaut) | ❌ Non |

**Exemple :**
```bash
SECRET_KEY=ma_cle_secrete_generée_avec_python_secrets
FLASK_ENV=production
FLASK_TESTING=false
PUBLIC_BASE_URL=https://schedule.example.com
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

### SSO/OIDC (optionnel)

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `OIDC_ENABLED` | Active l'authentification OIDC (`true`/`false`) | ❌ Non |
| `OIDC_ISSUER` | URL du fournisseur OIDC (ex. Keycloak realm) | ✅ Si `OIDC_ENABLED=true` |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | Identifiants du client OIDC | ✅ Si `OIDC_ENABLED=true` |
| `OIDC_REDIRECT_URI` | URL de callback, doit être enregistrée côté fournisseur | ✅ Si `OIDC_ENABLED=true` |
| `OIDC_POST_LOGOUT_REDIRECT_URI` | URL de redirection après déconnexion RP-initiated | ❌ Non |
| `OIDC_DISABLE_BASIC_AUTH` | Masque le formulaire email/mot de passe (`true`/`false`) | ❌ Non |
| `OIDC_EMAIL_CLAIM` / `OIDC_NAME_CLAIM` / `OIDC_USERNAME_CLAIM` | Mapping des claims du token (défauts : `email`, `name`, `preferred_username`) | ❌ Non |
| `OIDC_GROUPS_CLAIM` / `OIDC_ROLES_CLAIM` | Synchronisation optionnelle des groupes/rôles locaux | ❌ Non |
| `OIDC_SIGNATURE_ALGORITHMS` | Algorithme de signature du token (défaut `RS256`) | ❌ Non |
| `OIDC_SCOPE` | Scope demandé (défaut `openid profile email`) | ❌ Non |
| `OIDC_INTERNAL_ISSUER` | URL de l'issuer joignable par le conteneur, si différente de `OIDC_ISSUER` (déploiement Docker avec IdP sur le même réseau) | ❌ Non |

Guide de configuration complet :
[`guides/ADMIN_GUIDE.md`](../guides/ADMIN_GUIDE.md#configuration-ssooidc).

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

> ⚠️ Cette section a été corrigée le 16 juillet 2026 (chantier audit trail, voir
> CLAUDE.md "Audit trail") : elle documentait un ensemble de variables
> (`LOG_DIR`, `LOG_FILE_SIZE`, `LOG_FILE_APP`/`LOG_FILE_ERRORS`/.../`LOG_LEVEL_*`,
> `LOG_FORMAT`, `SYSLOG_*`, `LOG_FILTER_*`) qui n'ont jamais existé dans le code
> (`app/utils/logging/logger.py`) — probablement un reliquat d'une conception
> antérieure jamais implémentée. Seules les 4 variables ci-dessous sont
> réellement lues.

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `LOG_LEVEL` | string | `INFO` | Niveau de log principal. Valeurs possibles : `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | ❌ Non |
| `LOG_FILE` | string | *(aucun)* | Chemin d'un fichier de log racine optionnel, en plus des fichiers `app.log`/`error.log`/`debug.log`/`http_errors.log`/`audit.log` toujours créés dans `logs/` (dossier fixe, non configurable) | ❌ Non |
| `LOG_MAX_BYTES` | entier | `10485760` (10 Mo) | Taille maximale de chaque fichier de log avant rotation (`RotatingFileHandler`, s'applique à tous les fichiers de `logs/`, y compris `audit.log`) | ❌ Non |
| `LOG_BACKUP_COUNT` | entier | `5` | Nombre de fichiers de backup conservés après rotation (`app.log.1`, `app.log.2`, ...) | ❌ Non |

Le filtrage des données sensibles (masquage de `password=`/`token=`/`api_key=` dans
les messages de log, `SensitiveDataFilter`) est toujours actif et n'est pas
désactivable par variable d'environnement. `audit.log` (dans `logs/`) est
alimenté par `AuditService.log()` — voir CLAUDE.md "Audit trail" pour la
double écriture DB + fichier et la consultation via `/admin/audit-log`.

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

Les URL d'abonnement ICS affichées à l'utilisateur (page `/profile/ics-token`)
utilisent `PUBLIC_BASE_URL` si définie (voir
[🔐 Configuration de Base Flask](#-configuration-de-base-flask)), sinon
`request.host_url` — pertinent derrière un reverse proxy.

---

## 📧 Configuration des Notifications

Rappels hebdomadaires par email (shifts + astreintes), envoyés par les
scripts autonomes `scripts/send_shift_notifications.py` (dimanche, 24h
avant le début des shifts du lundi) et
`scripts/send_oncall_notifications.py` (jeudi, 24h avant le début de
l'astreinte du vendredi 21h) - à déclencher via cron, pas par
l'application Flask elle-même (voir `scripts/cron_example.sh`). Un seul
email par semaine et par utilisateur (table `notification_log` en base,
empêche les doublons si un script est relancé).

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `NOTIFICATIONS_ENABLED` | booléen | `false` | Active l'envoi des notifications par email | ❌ Non |
| `NOTIFICATION_FROM_EMAIL` | string | `""` | Adresse email de l'expéditeur | ❌ Non (requis si activé) |
| `SMTP_HOST` | string | `""` | Serveur SMTP | ❌ Non (requis si activé) |
| `SMTP_PORT` | entier | `587` | Port SMTP | ❌ Non |
| `SMTP_USERNAME` | string | `""` | Nom d'utilisateur SMTP | ❌ Non |
| `SMTP_PASSWORD` | string | `""` | Mot de passe SMTP | ❌ Non |
| `SMTP_USE_TLS` | booléen | `true` | Utiliser TLS pour la connexion SMTP | ❌ Non |
| `SMTP_TIMEOUT` | entier | `10` | Délai d'attente de connexion SMTP en secondes | ❌ Non |
| `NOTIFICATION_APP_BASE_URL` | string | `""` | URL de base de l'app, pour le lien "voir le planning"/"voir les astreintes" dans les emails (omis si vide) | ❌ Non |

Si `NOTIFICATIONS_ENABLED=false`, ou si `NOTIFICATION_FROM_EMAIL`/
`SMTP_HOST` manquent, les deux scripts se terminent silencieusement
sans rien envoyer (code de sortie 0).

---

## 💾 Configuration des Sauvegardes

Sauvegarde de la base de données (locale et/ou S3/S3-compatible), gérée
par `scripts/backup_database.py` - à déclencher via cron (voir
`scripts/cron_example.sh`) ou depuis l'interface d'administration
(`/admin/backups`). Voir [`deployment/BACKUP_GUIDE.md`](../deployment/BACKUP_GUIDE.md)
pour le détail.

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `BACKUP_ENABLED` | booléen | `false` | Active les sauvegardes (script cron *et* création manuelle depuis l'admin) | ❌ Non |
| `BACKUP_LOCAL_ENABLED` | booléen | `true` | Active la sauvegarde locale | ❌ Non |
| `BACKUP_LOCAL_DIR` | string | `backups` | Dossier de sauvegarde locale (en Docker, utilisez un chemin sous `/app/data` pour la persistance) | ❌ Non |
| `BACKUP_S3_ENABLED` | booléen | `false` | Active la sauvegarde S3/S3-compatible (nécessite `boto3`) | ❌ Non |
| `BACKUP_S3_BUCKET` | string | `""` | Nom du bucket S3 | ❌ Non (requis si activé) |
| `BACKUP_S3_ENDPOINT` | string | `""` | Endpoint S3-compatible (MinIO, etc.) - vide pour AWS S3 | ❌ Non |
| `BACKUP_S3_REGION` | string | `eu-west-1` | Région S3 | ❌ Non |
| `BACKUP_S3_ACCESS_KEY` | string | `""` | Clé d'accès S3 | ❌ Non |
| `BACKUP_S3_SECRET_KEY` | string | `""` | Clé secrète S3 | ❌ Non |
| `BACKUP_S3_PREFIX` | string | `leviia-schedule` | Préfixe des clés S3 | ❌ Non |
| `BACKUP_S3_USE_SSL` | booléen | `true` | Utiliser SSL pour la connexion S3 | ❌ Non |
| `BACKUP_RETENTION_DAYS` | entier | `30` | Nombre de jours de rétention | ❌ Non |
| `BACKUP_MAX_BACKUPS` | entier | `30` | Nombre maximal de sauvegardes conservées | ❌ Non |
| `BACKUP_COMPRESS` | booléen | `true` | Compresser les sauvegardes locales (gzip) | ❌ Non |
| `BACKUP_VERIFY` | booléen | `true` | Vérifier l'intégrité après création | ❌ Non |
| `BACKUP_NOTIFY_ON_SUCCESS` | booléen | `false` | Envoyer un email en cas de succès (réutilise la config SMTP ci-dessus) | ❌ Non |
| `BACKUP_NOTIFY_ON_FAILURE` | booléen | `true` | Envoyer un email en cas d'échec | ❌ Non |
| `BACKUP_NOTIFICATION_EMAIL` | string | `""` | Destinataire des alertes de sauvegarde | ❌ Non (requis si notify activé) |

Si `BACKUP_ENABLED=false`, le script cron se termine silencieusement
(code de sortie 0) et l'interface d'administration refuse la création
de nouvelles sauvegardes - les sauvegardes déjà existantes restent
consultables/téléchargeables. Les alertes email réutilisent la
configuration SMTP de la section Notifications ci-dessus, donc aussi
soumises à `NOTIFICATIONS_ENABLED`.

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

## ⚡ Configuration du Cache

| Variable | Type | Défaut | Description | Obligatoire |
|----------|------|--------|-------------|-------------|
| `CACHE_TYPE` | string | `simple` | Type de cache. Valeurs possibles : `simple` (en mémoire), `redis`, `memcached` — lu par `app/config/base.py`, appliqué dans `cache_manager.init_cache()` | ❌ Non |
| `CACHE_DEFAULT_TIMEOUT` | entier | `300` | Durée de vie par défaut des entrées de cache (en secondes) | ❌ Non |
| `CACHE_REDIS_URL` | string | `redis://localhost:6379/0` | URL Redis, utilisée si `CACHE_TYPE=redis` | ❌ Non |
| `CACHE_ENABLED` | booléen | `true` | Lu par `CacheConfig` (`app/utils/cache/config.py`) mais plus consommé nulle part dans le code actuel depuis la suppression des décorateurs `cached_route`/`cache_result` en Phase 4 — actuellement sans effet | ❌ Non |

> Si `flask-caching` n'est pas installé (dépendance optionnelle), le cache
> retombe automatiquement sur une implémentation dictionnaire en mémoire
> (`SimpleDictCache`) — visible dans les logs au démarrage
> (`Flask-Caching not available, using simple dictionary cache`).

### Variables supprimées (code mort retiré en Phase 4)

Les versions précédentes de ce document listaient des sections
**Pagination**, **Lazy Loading**, **Optimisation des Requêtes** et
**Monitoring des Performances** (`PAGINATION_*`, `LAZY_LOAD*`,
`QUERY_OPTIMIZATION_*`, `PERFORMANCE_MONITORING_ENABLED`,
`SLOW_QUERY_THRESHOLD`, etc.). Ces variables sont **retirées de cette
documentation** : elles sont lues par `config_performance.py`, un module
qui n'est importé **nulle part** dans `app/` ou `run.py` (vérifié par
recherche exhaustive) — les fonctionnalités qu'elles configuraient
(`app/utils/pagination/`, `app/utils/lazy_loading.py`, un module de
monitoring de performance) ont été supprimées comme code mort en
Phase 4 (voir `report/Phase 4: AMÉLIORATION DES TESTS.md`). Les définir
dans `.env` n'a aujourd'hui **aucun effet**.

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

# Cache
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0

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

### Configuration avec Redis

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TIMEOUT=300
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
- [`app/config/`](../../app/config/) — configuration active, chargée par `create_app()`
- [`.env.example`](../../.env.example) — référence canonique, toujours à jour

---

*Dernière mise à jour : 2026-07 (Phase 5)*
*Ce fichier documente les variables d'environnement effectivement lues par l'application. En cas de doute, `.env.example` fait foi.*
