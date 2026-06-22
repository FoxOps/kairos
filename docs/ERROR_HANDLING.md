# Gestion des Erreurs dans Leviia Schedule

Ce document décrit la gestion des erreurs améliorée dans l'application Leviia Schedule.

## 📋 Table des Matières

- [Architecture de la Gestion des Erreurs](#architecture-de-la-gestion-des-erreurs)
- [Pages d'Erreur Personnalisées](#pages-derreur-personnalisées)
- [Gestionnaires d'Erreurs HTTP](#gestionnaires-derreurs-http)
- [Gestion des Exceptions](#gestion-des-exceptions)
- [Système de Logging](#système-de-logging)
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

### Configuration du Logging

Le système de logging est configuré dans `app/__init__.py` avec la fonction `setup_logging()` :

```python
def setup_logging():
    """Configure le logging pour l'application avec rotation des fichiers."""
    # Créer le dossier de logs
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Logger principal
    app.logger.setLevel(logging.INFO)
    
    # Handler pour les fichiers (rotation)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'leviia-app.log'),
        maxBytes=1024 * 1024 * 5,  # 5 Mo
        backupCount=10,
        encoding='utf-8'
    )
    
    # Handler pour les erreurs
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'leviia-errors.log'),
        maxBytes=1024 * 1024 * 5,
        backupCount=10,
        encoding='utf-8'
    )
    
    # Handler console
    console_handler = logging.StreamHandler()
    
    # Logger dédié aux erreurs HTTP
    http_error_logger = logging.getLogger('http_errors')
```

### Fichiers de Log

| Fichier | Niveau | Description |
|---------|--------|-------------|
| `logs/leviia-app.log` | INFO | Logs généraux de l'application |
| `logs/leviia-errors.log` | ERROR | Toutes les erreurs |
| `logs/leviia-http-errors.log` | WARNING | Erreurs HTTP avec contexte |

### Format des Logs

#### Logs Généraux
```
2024-01-15 10:30:45,123 - app - INFO - Application started
```

#### Logs d'Erreurs HTTP
```
2024-01-15 10:31:23,456 - ERROR - IP: 192.168.1.100 - Path: /admin/users - User: John Doe - Error: HTTP 403 - Forbidden
```

#### Logs d'Erreurs Complètes
```
2024-01-15 10:32:15,789 - app - ERROR - HTTP 500 - Internal Server Error

Traceback (most recent call last):
  File "/path/to/app/__init__.py", line 100, in internal_server_error
    return render_template("500.html")
  File "/path/to/flask/template.py", line 123, in render_template
    ...
ValueError: Invalid template name
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
    
    http_error_logger.error(
        error_msg,
        extra={'ip': ip, 'path': path, 'user': user}
    )
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

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `DEBUG_ERRORS` | `false` | Afficher les détails des erreurs en développement |
| `LOG_LEVEL` | `INFO` | Niveau de logging (DEBUG, INFO, WARNING, ERROR) |
| `LOG_DIR` | `./logs` | Dossier pour les fichiers de log |
| `FLASK_ENV` | `default` | Environnement (development, production, testing) |

### Environnements

#### Développement
```bash
export FLASK_ENV=development
export DEBUG_ERRORS=true
export LOG_LEVEL=DEBUG
```

#### Production
```bash
export FLASK_ENV=production
export DEBUG_ERRORS=false
export LOG_LEVEL=WARNING
```

#### Tests
```bash
export FLASK_ENV=testing
export FLASK_TESTING=true
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

3. **Messages d'erreur clairs**
   - Utiliser des messages compréhensibles pour les utilisateurs finaux
   - Éviter d'afficher des détails techniques en production

4. **Gestion des exceptions**
   - Capturer les exceptions spécifiques avec des handlers dédiés
   - Utiliser le handler générique comme filet de sécurité

5. **Support AJAX**
   - Toujours vérifier si la requête est AJAX et retourner JSON si nécessaire
   - Utiliser `request.accept_mimetypes.accept_json`

### Exemple de Code

```python
from flask import abort, jsonify
from app import db, log_http_error
from app.models import User

@app.route('/users/<int:user_id>')
def get_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            log_http_error(404, f"User {user_id} not found")
            abort(404, description="Utilisateur non trouvé")
        return jsonify(user.to_dict())
    except ValueError as e:
        log_http_error(400, f"Invalid user ID: {str(e)}")
        abort(400, description="ID d'utilisateur invalide")
    except Exception as e:
        log_http_error(500, f"Error fetching user: {str(e)}")
        abort(500, description="Erreur lors de la récupération de l'utilisateur")
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
```

---

## 📚 Ressources Additionnelles

- [Flask Error Handling Documentation](https://flask.palletsprojects.com/en/3.1.x/errorhandling/)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [WCAG Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 📝 Historique des Changements

### Version 1.0 (2024)
- Ajout des pages d'erreur personnalisées pour tous les codes HTTP principaux
- Implémentation du système de logging avec rotation des fichiers
- Ajout des gestionnaires d'erreurs HTTP et d'exceptions
- Configuration centralisée dans `config.py`
- Tests complets pour tous les gestionnaires d'erreurs

---

*Documentation générée pour Leviia Schedule - Gestion des Erreurs Améliorée*
