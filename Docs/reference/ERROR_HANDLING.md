# Gestion des Erreurs dans Leviia Schedule

Ce document décrit la gestion des erreurs améliorée et le système de logging avancé dans l'application Leviia Schedule.

## 📋 Table des Matières

- [Architecture de la Gestion des Erreurs](#architecture-de-la-gestion-des-erreurs)
- [Pages d'Erreur Personnalisées](#pages-derreur-personnalisées)
- [Gestionnaires d'Erreurs HTTP](#gestionnaires-derreurs-http)
- [Gestion des Exceptions](#gestion-des-exceptions)
- [Système de Logging](#système-de-logging)
  - [Configuration du Logging](#configuration-du-logging)
  - [Niveaux de Log](#niveaux-de-log)
  - [Fichiers de Log](#fichiers-de-log)
  - [Filtres de Log](#filtres-de-log)
  - [Loggers Spécifiques](#loggers-spécifiques)
  - [Syslog](#syslog)
  - [Audit Logging](#audit-logging)
- [Configuration](#configuration)
- [Bonnes Pratiques](#bonnes-pratiques)
- [Tests](#tests)

---

## 🏗️ Architecture de la Gestion des Erreurs

L'application utilise une approche multi-couches pour la gestion des erreurs :

1. **Gestionnaires d'erreurs HTTP** : Capturent les erreurs HTTP standard (400, 401, 403, 404, 405, 500, 502, 503, 504)
2. **Gestionnaires d'exceptions** : Capturent les exceptions Python spécifiques (ValueError, TypeError, etc.)
3. **Gestionnaire générique** : Capture toutes les exceptions non gérées
4. **Système de logging** : Enregistre toutes les erreurs avec contexte
5. **Pages d'erreur personnalisées** : Affiche des pages utilisateur conviviales

### Localisation du Code

- **Fichier principal** : `app/__init__.py`
  - Contient tous les gestionnaires d'erreurs (`@app.errorhandler`)
  - Configuration du logging
  - Fonctions utilitaires pour le logging des erreurs

- **Templates** : `app/templates/`
  - `400.html` - Requête incorrecte
  - `401.html` - Non autorisé
  - `403.html` - Accès interdit
  - `404.html` - Page non trouvée
  - `405.html` - Méthode non autorisée
  - `500.html` - Erreur interne du serveur
  - `502.html` - Mauvaise passerelle
  - `503.html` - Service indisponible
  - `504.html` - Délai d'attente dépassé

- **Configuration** : `config.py`
  - Paramètres de gestion des erreurs
  - Configuration du logging

---

## 🎨 Pages d'Erreur Personnalisées

### Liste des Pages d'Erreur

| Code HTTP | Nom | Template | Description |
|-----------|-----|----------|-------------|
| 400 | Bad Request | `400.html` | Requête mal formée ou invalide |
| 401 | Unauthorized | `401.html` | Authentification requise |
| 403 | Forbidden | `403.html` | Accès interdit (autorisation insuffisante) |
| 404 | Not Found | `404.html` | Ressource non trouvée |
| 405 | Method Not Allowed | `405.html` | Méthode HTTP non supportée |
| 500 | Internal Server Error | `500.html` | Erreur interne du serveur |
| 502 | Bad Gateway | `502.html` | Réponse invalide du serveur en amont |
| 503 | Service Unavailable | `503.html` | Service temporairement indisponible |
| 504 | Gateway Timeout | `504.html` | Délai d'attente dépassé |

### Structure des Templates

Tous les templates d'erreur étendent `base.html` et suivent cette structure :

```html
{% extends "base.html" %}

{% block title %}Titre de l'erreur - Leviia{% endblock %}

{% block content %}
<div class="section">
    <div class="container">
        <div class="columns is-centered">
            <div class="column is-6">
                <div class="box has-text-centered">
                    <h1 class="title is-1 has-text-XXX">CODE</h1>
                    <h2 class="title is-3">Titre de l'erreur</h2>
                    <p class="subtitle is-5">Description courte</p>
                    <div class="content">
                        <p>Explication détaillée</p>
                        {% if error_message %}
                        <div class="notification is-warning mt-4">
                            <p><strong>Détails :</strong> {{ error_message }}</p>
                        </div>
                        {% endif %}
                    </div>
                    <div class="mt-5">
                        <!-- Boutons d'action -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Fonctionnalités Communes

- **Design cohérent** : Tous les templates utilisent Bulma CSS pour un rendu uniforme
- **Navigation** : Boutons pour retourner à l'accueil, se connecter/déconnecter
- **Messages contextuels** : Affichage des détails de l'erreur si disponibles
- **Accessibilité** : Respect des normes WCAG (contrastes, balises ARIA)
- **Responsive** : Adapté aux mobiles et tablettes

---

## 🛡️ Gestionnaires d'Erreurs HTTP

### Gestionnaires Implémentés

#### Erreurs Client (4xx)

```python
@app.errorhandler(400)
def bad_request_error(error):
    """Page d'erreur 400 - Requête incorrecte."""
    log_http_error(400, str(error))
    return render_template("400.html", **get_error_template_data(400, str(error))), 400

@app.errorhandler(401)
def unauthorized_error(error):
    """Page d'erreur 401 - Non autorisé."""
    log_http_error(401, str(error))
    return render_template("401.html", **get_error_template_data(401, "Accès non autorisé")), 401

@app.errorhandler(403)
def forbidden_error(error):
    """Page d'erreur 403 - Accès interdit."""
    log_http_error(403, str(error))
    return render_template("403.html", **get_error_template_data(403, str(error))), 403

@app.errorhandler(404)
def not_found_error(error):
    """Page d'erreur 404 - Page non trouvée."""
    log_http_error(404, str(error))
    return render_template("404.html", **get_error_template_data(404, str(error))), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Page d'erreur 405 - Méthode non autorisée."""
    log_http_error(405, str(error))
    return render_template("405.html", **get_error_template_data(405, str(error))), 405
```

#### Erreurs Serveur (5xx)

```python
@app.errorhandler(500)
def internal_server_error(error):
    """Page d'erreur 500 - Erreur interne du serveur."""
    # Extraction de la trace complète
    exc_type, exc_value, exc_traceback = None, None, None
    if hasattr(error, 'exc_info') and error.exc_info:
        exc_type, exc_value, exc_traceback = error.exc_info
    
    # Logging complet
    error_message = str(error) if str(error) else "Erreur interne du serveur"
    log_http_error(500, error_message, (exc_type, exc_value, exc_traceback) if exc_type else None)
    
    # Support AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur interne du serveur s\'est produite.',
            'code': 500
        }), 500
    
    return render_template("500.html", **get_error_template_data(500, error_message)), 500

@app.errorhandler(502)
def bad_gateway_error(error):
    """Page d'erreur 502 - Mauvaise passerelle."""
    log_http_error(502, str(error))
    return render_template("502.html", **get_error_template_data(502, "Le serveur a reçu une réponse invalide")), 502

@app.errorhandler(503)
def service_unavailable_error(error):
    """Page d'erreur 503 - Service indisponible."""
    retry_after = None
    if hasattr(error, 'retry_after'):
        retry_after = error.retry_after
    
    log_http_error(503, str(error))
    return render_template(
        "503.html", 
        retry_after=retry_after,
        **get_error_template_data(503, "Service temporairement indisponible")
    ), 503

@app.errorhandler(504)
def gateway_timeout_error(error):
    """Page d'erreur 504 - Délai d'attente dépassé."""
    log_http_error(504, str(error))
    return render_template("504.html", **get_error_template_data(504, "Le serveur n'a pas répondu à temps")), 504
```

### Gestionnaires d'Exceptions

```python
@app.errorhandler(Exception)
def handle_exception(error):
    """Gestionnaire d'exceptions générique."""
    # Ne pas interférer avec les erreurs HTTP déjà gérées
    if hasattr(error, 'code') and error.code in [400, 401, 403, 404, 405, 500, 502, 503, 504]:
        return error
    
    # Logging
    exc_type, exc_value, exc_traceback = type(error), error, error.__traceback__
    log_http_error(500, f"Unhandled exception: {str(error)}", (exc_type, exc_value, exc_traceback))
    
    # Support AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur inattendue s\'est produite.',
            'code': 500
        }), 500
    
    return render_template("500.html", **get_error_template_data(500, "Une erreur inattendue s'est produite")), 500

@app.errorhandler(sqlite3.OperationalError)
def handle_database_error(error):
    """Gestionnaire d'erreurs SQLite."""
    error_message = str(error)
    log_http_error(500, f"Database error: {error_message}")
    
    # Messages spécifiques
    if "locked" in error_message.lower():
        error_message = "La base de données est temporairement verrouillée. Veuillez réessayer dans quelques instants."
    else:
        error_message = "Une erreur de base de données s'est produite. Veuillez réessayer plus tard."
    
    # Support AJAX
    if request and request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Database Error', 'message': error_message, 'code': 500}), 500
    
    return render_template("500.html", **get_error_template_data(500, error_message)), 500

@app.errorhandler(ValueError)
def handle_value_error(error):
    """Gestionnaire d'erreurs de validation."""
    log_http_error(400, f"Validation error: {str(error)}")
    
    if request and request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Validation Error', 'message': str(error), 'code': 400}), 400
    
    return render_template("400.html", **get_error_template_data(400, str(error))), 400

@app.errorhandler(TypeError)
def handle_type_error(error):
    """Gestionnaire d'erreurs de type."""
    log_http_error(400, f"Type error: {str(error)}")
    
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Type Error',
            'message': 'Une erreur de type s\'est produite. Veuillez vérifier vos données.',
            'code': 400
        }), 400
    
    return render_template("400.html", **get_error_template_data(400, "Une erreur de type s'est produite")), 400
```

---

## 📝 Système de Logging

Le système de logging a été complètement repensé pour offrir une gestion plus granulaire, sécurisée et extensible. Il est configuré dans `app/__init__.py` avec la fonction `setup_logging()`.

### Configuration du Logging

La configuration centrale se trouve dans `config.py` avec les paramètres suivants :

```python
# Niveau de log principal
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Taille des fichiers et nombre de backups
LOG_FILE_SIZE = int(os.environ.get("LOG_FILE_SIZE", 5 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))

# Dossier des logs
LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')

# Noms des fichiers de log
LOG_FILE_APP = "leviia-app.log"
LOG_FILE_ERRORS = "leviia-errors.log"
LOG_FILE_HTTP = "leviia-http-errors.log"
LOG_FILE_DEBUG = "leviia-debug.log"
LOG_FILE_AUDIT = "leviia-audit.log"

# Niveaux de log par module
LOG_LEVEL_APP = os.environ.get("LOG_LEVEL_APP", LOG_LEVEL)
LOG_LEVEL_ERRORS = os.environ.get("LOG_LEVEL_ERRORS", "ERROR")
LOG_LEVEL_HTTP = os.environ.get("LOG_LEVEL_HTTP", "WARNING")
LOG_LEVEL_DEBUG = os.environ.get("LOG_LEVEL_DEBUG", "DEBUG")
LOG_LEVEL_AUDIT = os.environ.get("LOG_LEVEL_AUDIT", "INFO")

# Syslog pour la production
SYSLOG_ENABLED = os.environ.get("SYSLOG_ENABLED", "false").lower() == "true"
SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS", "/dev/log")
SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY", "local0")

# Filtres de sécurité
LOG_FILTER_SENSITIVE = os.environ.get("LOG_FILTER_SENSITIVE", "true").lower() == "true"
```

### Niveaux de Log

Le système supporte tous les niveaux de log standard de Python :

| Niveau | Description | Utilisation |
|--------|-------------|-------------|
| **DEBUG** | Informations détaillées pour le débogage | Développement uniquement |
| **INFO** | Informations générales sur le fonctionnement | Développement et production |
| **WARNING** | Avertissements pour des situations potentiellement problématiques | Production |
| **ERROR** | Erreurs qui doivent être investiguées | Production |
| **CRITICAL** | Erreurs critiques nécessitant une intervention immédiate | Production |

**Recommandations par environnement :**
- **Développement** : `LOG_LEVEL=DEBUG` pour voir tous les détails
- **Test** : `LOG_LEVEL=INFO` pour un bon équilibre
- **Production** : `LOG_LEVEL=WARNING` ou `ERROR` pour réduire le volume

### Fichiers de Log

Le système génère plusieurs fichiers de log avec rotation automatique :

| Fichier | Niveau | Description | Rotation |
|---------|--------|-------------|----------|
| `logs/leviia-app.log` | INFO | Logs généraux de l'application | 5 Mo, 10 backups |
| `logs/leviia-errors.log` | ERROR | Toutes les erreurs avec traces | 5 Mo, 10 backups |
| `logs/leviia-http-errors.log` | WARNING | Erreurs HTTP avec contexte | 5 Mo, 10 backups |
| `logs/leviia-debug.log` | DEBUG | Logs de débogage détaillés | 5 Mo, 10 backups |
| `logs/leviia-audit.log` | INFO | Actions utilisateur pour l'audit | 5 Mo, 10 backups |
| `logs/leviia-sql.log` | DEBUG | Requêtes SQL (si SQLALCHEMY_ECHO=True) | 5 Mo, 10 backups |
| `logs/leviia-auth.log` | INFO | Logs d'authentification | 5 Mo, 10 backups |
| `logs/leviia-automation.log` | INFO | Logs des tâches automatisées | 5 Mo, 10 backups |

### Filtres de Log

Un filtre spécial (`SensitiveDataFilter`) est appliqué pour masquer automatiquement les informations sensibles dans les logs :

- Mots de passe (`password=...`)
- Secrets (`secret=...`)
- Tokens (`token=...`)
- Clés API (`api_key=...`, `apikey=...`)
- Informations d'authentification (`auth=...`)

**Exemple :**
```
# Avant filtrage
"User login: email=user@example.com, password=secret123"

# Après filtrage
"User login: email=user@example.com, password=***"
```

Le filtrage peut être désactivé avec `LOG_FILTER_SENSITIVE=false`.

### Loggers Spécifiques

En plus du logger principal, plusieurs loggers spécialisés sont disponibles :

| Logger | Nom | Description |
|--------|-----|-------------|
| Logger principal | `app.logger` | Logs généraux de l'application |
| Erreurs HTTP | `http_errors` | Erreurs HTTP avec contexte IP/user |
| Audit | `audit` | Actions utilisateur pour le suivi |
| SQL | `sqlalchemy.engine` | Requêtes SQL (si activé) |
| Authentification | `flask_login` | Événements de login/logout |
| Automation | `automation` | Tâches planifiées et automatisées |

**Utilisation des loggers spécifiques :**
```python
# Logger HTTP
from app import http_error_logger
http_error_logger.error("Erreur 500", extra={'ip': '192.168.1.1', 'user': 'admin'})

# Logger Audit
import logging
audit_logger = logging.getLogger('audit')
audit_logger.info("User admin deleted user 123")

# Logger personnalisé
from app import get_logger
custom_logger = get_logger('my_module')
custom_logger.info("Message spécifique au module")
```

### Syslog

Pour les environnements de production, le système peut envoyer les logs vers syslog :

```bash
# Activation
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log  # ou une adresse réseau
export SYSLOG_FACILITY=local0
```

Les logs sont formatés pour syslog avec le préfixe `LeviiaSchedule`.

### Audit Logging

Un système d'audit permet de tracer les actions utilisateur importantes :

```python
from app import log_audit_action

# Logger une action réussie
log_audit_action("user_login", user=current_user, path="/login", status="success")

# Logger une action échouée
log_audit_action("delete_user", user=current_user, path="/admin/users/123", 
                 status="failure", details="User not found")
```

**Format des logs d'audit :**
```
2024-01-15 10:30:45 - audit - INFO - AUDIT: user_login - User: admin - Status: success - Path: /login
```

### Format des Logs

#### Logs Généraux
```
2024-01-15 10:30:45 - app - INFO - Application started
```

#### Logs d'Erreurs HTTP
```
2024-01-15 10:31:23 - ERROR - IP: 192.168.1.100 - Path: /admin/users - User: John Doe - Error: HTTP 403 - Forbidden
```

#### Logs d'Erreurs Complètes
```
2024-01-15 10:32:15 - app - ERROR - HTTP 500 - Internal Server Error

Traceback (most recent call last):
  File "/path/to/app/__init__.py", line 100, in internal_server_error
    return render_template("500.html")
  File "/path/to/flask/template.py", line 123, in render_template
    ...
ValueError: Invalid template name
```

#### Logs d'Audit
```
2024-01-15 10:35:00 - audit - INFO - AUDIT: delete_user - User: admin - Status: success - Path: /admin/users/456
```

### Fonctions Utilitaires

```python
def log_http_error(error_code, error_message=None, exc_info=None):
    """Log une erreur HTTP avec des informations contextuelles."""
    ip = request.remote_addr if request else 'unknown'
    path = request.path if request else 'unknown'
    user = current_user.name if hasattr(current_user, 'name') and current_user.is_authenticated else 'anonymous'
    
    error_msg = f"HTTP {error_code} - {error_message or error_code}"
    
    # Ajouter la trace complète si disponible
    if exc_info:
        error_msg += f"\n{traceback.format_exception(*exc_info)}"
    
    # Logger dans le logger dédié aux erreurs HTTP
    http_error_logger.error(
        error_msg,
        extra={'ip': ip, 'path': path, 'user': user}
    )
    
    # Logger aussi dans le logger principal selon le niveau
    if error_code >= 500:
        app.logger.error(f"Erreur serveur {error_code}: {error_message or error_code} - Path: {path}")
    elif error_code >= 400:
        app.logger.warning(f"Erreur client {error_code}: {error_message or error_code} - Path: {path}")


def log_audit_action(action, user=None, path=None, status="success", details=None):
    """Log une action utilisateur pour l'audit."""
    audit_logger = logging.getLogger('audit')
    user_name = user.name if user and hasattr(user, 'name') else 'anonymous'
    
    message = f"AUDIT: {action} - User: {user_name} - Status: {status}"
    if path:
        message += f" - Path: {path}"
    if details:
        message += f" - Details: {details}"
    
    if status == "success":
        audit_logger.info(message)
    elif status == "failure":
        audit_logger.warning(message)
    else:
        audit_logger.info(message)


def get_logger(name):
    """Obtient un logger spécifique avec la configuration par défaut."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Ajoute un handler par défaut si aucun n'existe
        handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, f'leviia-{name}.log'),
            Config.LOG_FILE_SIZE,
            Config.LOG_BACKUP_COUNT,
            logging.INFO,
            logging.Formatter(Config.LOG_FORMAT, datefmt=Config.LOG_DATE_FORMAT)
        )
        if Config.LOG_FILTER_SENSITIVE:
            handler.addFilter(SensitiveDataFilter(Config.LOG_FILTER_PATTERNS))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

---

## ⚙️ Configuration

### Paramètres de Configuration

Dans `config.py`, plusieurs paramètres sont disponibles pour configurer la gestion des erreurs :

```python
# Configuration de la gestion des erreurs
DEBUG_ERRORS = os.environ.get("DEBUG_ERRORS", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo
LOG_BACKUP_COUNT = 10
LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')

# Afficher les pages d'erreur personnalisées
SHOW_CUSTOM_ERROR_PAGES = True

# Messages par défaut
ERROR_500_MESSAGE = "Une erreur interne du serveur s'est produite. Veuillez réessayer plus tard."
ERROR_503_MESSAGE = "Service temporairement indisponible. Veuillez réessayer dans quelques instants."
ERROR_503_RETRY_AFTER = 300  # 5 minutes
```

### Variables d'Environnement

#### Configuration Générale

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `DEBUG_ERRORS` | `false` | Afficher les détails des erreurs en développement |
| `LOG_LEVEL` | `INFO` | Niveau de logging principal (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_DIR` | `./logs` | Dossier pour les fichiers de log |
| `FLASK_ENV` | `default` | Environnement (development, production, testing) |

#### Configuration des Fichiers de Log

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `LOG_FILE_SIZE` | `5242880` (5 Mo) | Taille maximale des fichiers de log |
| `LOG_BACKUP_COUNT` | `10` | Nombre de fichiers de backup |
| `LOG_FILE_APP` | `leviia-app.log` | Nom du fichier de log principal |
| `LOG_FILE_ERRORS` | `leviia-errors.log` | Nom du fichier des erreurs |
| `LOG_FILE_HTTP` | `leviia-http-errors.log` | Nom du fichier des erreurs HTTP |
| `LOG_FILE_DEBUG` | `leviia-debug.log` | Nom du fichier de debug |
| `LOG_FILE_AUDIT` | `leviia-audit.log` | Nom du fichier d'audit |

#### Niveaux de Log par Module

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `LOG_LEVEL_APP` | `LOG_LEVEL` | Niveau de log pour l'application |
| `LOG_LEVEL_ERRORS` | `ERROR` | Niveau de log pour les erreurs |
| `LOG_LEVEL_HTTP` | `WARNING` | Niveau de log pour les erreurs HTTP |
| `LOG_LEVEL_DEBUG` | `DEBUG` | Niveau de log pour le debug |
| `LOG_LEVEL_AUDIT` | `INFO` | Niveau de log pour l'audit |

#### Syslog

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `SYSLOG_ENABLED` | `false` | Activer l'envoi vers syslog |
| `SYSLOG_ADDRESS` | `/dev/log` | Adresse syslog (fichier ou réseau) |
| `SYSLOG_FACILITY` | `local0` | Facility syslog |

#### Sécurité

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `LOG_FILTER_SENSITIVE` | `true` | Filtrer les données sensibles dans les logs |

### Environnements

#### Développement
```bash
# Configuration de base
export FLASK_ENV=development
export DEBUG_ERRORS=true
export LOG_LEVEL=DEBUG

# Configuration avancée
export LOG_LEVEL_APP=DEBUG
export LOG_LEVEL_DEBUG=DEBUG
export LOG_FILTER_SENSITIVE=true

# Désactiver syslog en développement
export SYSLOG_ENABLED=false
```

#### Production
```bash
# Configuration de base
export FLASK_ENV=production
export DEBUG_ERRORS=false
export LOG_LEVEL=WARNING

# Configuration avancée
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_LEVEL_HTTP=WARNING
export LOG_LEVEL_AUDIT=INFO

# Activer syslog en production
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export SYSLOG_FACILITY=local0

# Sécurité
export LOG_FILTER_SENSITIVE=true
```

#### Tests
```bash
export FLASK_ENV=testing
export FLASK_TESTING=true
export LOG_LEVEL=DEBUG

# Désactiver syslog et filtrage pour les tests
export SYSLOG_ENABLED=false
export LOG_FILTER_SENSITIVE=false
```

#### Exemple Complet pour Production avec Syslog distant
```bash
# Configuration Flask
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here

# Configuration du logging
export LOG_LEVEL=WARNING
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_DIR=/var/log/leviia

# Syslog vers un serveur distant
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=192.168.1.100:514
export SYSLOG_FACILITY=local0

# Sécurité
export LOG_FILTER_SENSITIVE=true

# Base de données
export DATABASE_URL=postgresql://user:password@localhost/leviia
```

---

## ✅ Bonnes Pratiques

### Pour les Développeurs

1. **Toujours utiliser les gestionnaires d'erreurs**
   - Ne pas retourner directement des codes d'erreur sans passer par les handlers
   - Utiliser `abort(404)` ou `abort(403)` pour les erreurs standard

2. **Logging systématique**
   - Toujours logger les erreurs avec `log_http_error()` ou `app.logger.error()`
   - Inclure le contexte (utilisateur, IP, chemin, etc.)
   - Utiliser les niveaux de log appropriés (DEBUG, INFO, WARNING, ERROR)

3. **Messages d'erreur clairs**
   - Utiliser des messages compréhensibles pour les utilisateurs finaux
   - Éviter d'afficher des détails techniques en production
   - Les données sensibles sont automatiquement filtrées

4. **Gestion des exceptions**
   - Capturer les exceptions spécifiques avec des handlers dédiés
   - Utiliser le handler générique comme filet de sécurité

5. **Support AJAX**
   - Toujours vérifier si la requête est AJAX et retourner JSON si nécessaire
   - Utiliser `request.accept_mimetypes.accept_json`

6. **Audit Logging**
   - Logger les actions utilisateur importantes avec `log_audit_action()`
   - Inclure l'utilisateur, le chemin et le statut (success/failure)

7. **Loggers Spécifiques**
   - Utiliser `get_logger(name)` pour créer des loggers module-spécifiques
   - Utiliser les loggers dédiés pour SQL, auth, automation

8. **Sécurité**
   - Ne jamais logger de données sensibles (mots de passe, tokens, etc.)
   - Le filtre `SensitiveDataFilter` le fait automatiquement

### Exemple de Code

```python
from flask import abort, jsonify, request
from app import db, log_http_error, log_audit_action, get_logger
from app.models import User

# Logger spécifique pour ce module
user_logger = get_logger('users')

@app.route('/users/<int:user_id>')
def get_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            log_http_error(404, f"User {user_id} not found")
            log_audit_action("get_user", user=current_user, path=request.path, 
                           status="failure", details=f"User {user_id} not found")
            abort(404, description="Utilisateur non trouvé")
        
        # Logger l'action réussie
        log_audit_action("get_user", user=current_user, path=request.path, 
                       status="success", details=f"User {user_id}")
        
        user_logger.info(f"User {user_id} retrieved by {current_user.name}")
        return jsonify(user.to_dict())
    except ValueError as e:
        log_http_error(400, f"Invalid user ID: {str(e)}")
        user_logger.warning(f"Invalid user ID: {user_id} - {str(e)}")
        abort(400, description="ID d'utilisateur invalide")
    except Exception as e:
        log_http_error(500, f"Error fetching user: {str(e)}")
        user_logger.error(f"Unexpected error fetching user {user_id}: {str(e)}", exc_info=True)
        abort(500, description="Erreur lors de la récupération de l'utilisateur")


@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            log_http_error(404, f"User {user_id} not found")
            log_audit_action("delete_user", user=current_user, path=request.path, 
                           status="failure", details=f"User {user_id} not found")
            abort(404, description="Utilisateur non trouvé")
        
        db.session.delete(user)
        db.session.commit()
        
        # Logger l'action d'audit
        log_audit_action("delete_user", user=current_user, path=request.path, 
                       status="success", details=f"Deleted user {user_id}")
        
        user_logger.info(f"User {user_id} deleted by {current_user.name}")
        return jsonify({"message": "Utilisateur supprimé avec succès"}), 200
        
    except Exception as e:
        log_http_error(500, f"Error deleting user: {str(e)}")
        log_audit_action("delete_user", user=current_user, path=request.path, 
                       status="failure", details=f"Error: {str(e)}")
        user_logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        abort(500, description="Erreur lors de la suppression de l'utilisateur")
```

### Pour les Administrateurs

1. **Surveillance des logs**
   - Vérifier régulièrement `logs/leviia-errors.log` pour les erreurs critiques
   - Vérifier `logs/leviia-http-errors.log` pour les erreurs HTTP
   - Vérifier `logs/leviia-audit.log` pour les actions utilisateur suspectes

2. **Rotation des logs**
   - Les fichiers sont automatiquement rotés à la taille configurée (5 Mo par défaut)
   - 10 fichiers de backup sont conservés par défaut
   - Configurer `LOG_FILE_SIZE` et `LOG_BACKUP_COUNT` selon vos besoins

3. **Sauvegarde des logs**
   - Archiver les anciens logs avant suppression
   - Conserver les logs pendant une période suffisante (recommandé: 30-90 jours)

4. **Configuration de la production**
   - Désactiver `DEBUG_ERRORS` en production
   - Utiliser `LOG_LEVEL=WARNING` ou `ERROR` pour réduire le volume
   - Configurer syslog pour une centralisation des logs
   - Activer `LOG_FILTER_SENSITIVE=true` pour la sécurité

5. **Monitoring**
   - Configurer des alertes pour les erreurs critiques (niveau ERROR et CRITICAL)
   - Surveiller la taille des fichiers de log
   - Configurer des outils de monitoring externe (Prometheus, ELK, etc.)

6. **Analyse des logs**
   - Utiliser des outils comme `grep`, `awk`, ou des solutions SIEM
   - Analyser les patterns d'erreurs pour identifier les problèmes récurrents
   - Surveiller les temps de réponse et les erreurs 5xx

### Exemple de Configuration Avancée

```python
# Dans votre code d'application

# Configuration personnalisée du logging
import logging
from app import get_logger

# Créer un logger pour un module spécifique
payment_logger = get_logger('payments')
payment_logger.setLevel(logging.INFO)

# Logger avec des informations supplémentaires
payment_logger.info(
    "Payment processed",
    extra={
        'user_id': current_user.id,
        'amount': 100.00,
        'currency': 'EUR',
        'transaction_id': 'txn_12345'
    }
)

# Utilisation du logger d'audit pour les actions sensibles
from app import log_audit_action

# Logger une action sensible
log_audit_action(
    "change_password",
    user=current_user,
    path="/account/change-password",
    status="success",
    details="Password changed successfully"
)
```

### Pour les Administrateurs

1. **Surveillance des logs**
   - Vérifier régulièrement `logs/leviia-errors.log`
   - Configurer des alertes pour les erreurs critiques

2. **Rotation des logs**
   - Les fichiers sont automatiquement rotés à 5 Mo
   - 10 fichiers de backup sont conservés

3. **Sauvegarde des logs**
   - Archiver les anciens logs avant suppression
   - Conserver les logs pendant une période suffisante

4. **Configuration de la production**
   - Désactiver `DEBUG_ERRORS` en production
   - Utiliser `LOG_LEVEL=WARNING` ou `ERROR`
   - Configurer un système de monitoring externe

---

## 🧪 Tests

### Exécution des Tests

```bash
# Exécuter tous les tests des gestionnaires d'erreurs
pytest tests/test_error_handlers.py -v

# Exécuter un test spécifique
pytest tests/test_error_handlers.py::TestCustomErrorPages::test_500_template_exists -v
```

### Structure des Tests

Les tests sont organisés dans `tests/test_error_handlers.py` :

- **TestErrorHandlers** : Tests des gestionnaires d'erreurs HTTP
- **TestCustomErrorPages** : Tests des templates d'erreur
- **TestErrorHandlerFunctions** : Tests des fonctions utilitaires
- **TestErrorHandlerRoutes** : Tests des routes qui déclenchent des erreurs
- **TestDatabaseErrorHandler** : Tests du gestionnaire d'erreurs de base de données
- **TestExceptionHandlers** : Tests des gestionnaires d'exceptions
- **TestLoggingConfiguration** : Tests de la configuration du logging
- **TestSensitiveDataFilter** : Tests du filtre de données sensibles
- **TestAuditLogging** : Tests du système d'audit

### Exemple de Test

```python
def test_404_error_handler(self, client):
    """Test le gestionnaire d'erreur 404."""
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    assert b"404" in response.data or b"Not Found" in response.data

def test_500_template_content(self, app):
    """Test le contenu du template 500.html."""
    with app.app_context():
        from flask import render_template
        html = render_template("500.html")
        assert b"500" in html.encode()
        assert b"Erreur interne" in html.encode()

# Test du filtre de données sensibles
def test_sensitive_data_filter(self, app):
    """Test que le filtre masque les données sensibles."""
    with app.app_context():
        from app import SensitiveDataFilter
        import logging
        
        # Créer un filtre
        filter = SensitiveDataFilter()
        
        # Créer un record de log avec des données sensibles
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="User login: password=secret123, token=abc123",
            args=(),
            exc_info=None
        )
        
        # Appliquer le filtre
        filter.filter(record)
        
        # Vérifier que les données sensibles sont masquées
        assert "password=***" in record.msg
        assert "token=***" in record.msg
        assert "secret123" not in record.msg
        assert "abc123" not in record.msg

# Test du système d'audit
def test_audit_logging(self, app):
    """Test que l'audit logging fonctionne."""
    with app.app_context():
        from app import log_audit_action
        import logging
        
        # Capturer les logs
        with app.app_context():
            # Créer un utilisateur mock
            class MockUser:
                name = "test_user"
            
            # Logger une action
            log_audit_action(
                "test_action",
                user=MockUser(),
                path="/test",
                status="success",
                details="Test details"
            )
            
            # Vérifier que le log a été enregistré
            audit_logger = logging.getLogger('audit')
            assert len(audit_logger.handlers) > 0
```

### Exécution des Tests de Logging

```bash
# Exécuter tous les tests de logging
pytest tests/test_error_handlers.py::TestLoggingConfiguration -v

# Exécuter les tests du filtre de données sensibles
pytest tests/test_error_handlers.py::TestSensitiveDataFilter -v

# Exécuter les tests d'audit
pytest tests/test_error_handlers.py::TestAuditLogging -v

# Exécuter un test spécifique
pytest tests/test_error_handlers.py::TestLoggingConfiguration::test_logging_setup -v
```

---

## 📚 Ressources Additionnelles

- [Flask Error Handling Documentation](https://flask.palletsprojects.com/en/3.1.x/errorhandling/)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [WCAG Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 📝 Historique des Changements

### Version 1.0 (Juin 2026)
- Ajout des pages d'erreur personnalisées pour tous les codes HTTP principaux
- Implémentation du système de logging avec rotation des fichiers
- Ajout des gestionnaires d'erreurs HTTP et d'exceptions
- Configuration centralisée dans `config.py`
- Tests complets pour tous les gestionnaires d'erreurs

---

*Documentation générée pour Leviia Schedule - Gestion des Erreurs Améliorée*
