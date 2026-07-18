# Error Handling in Kairos

This document describes the improved error handling and the advanced logging system in the Kairos application.

## 📋 Table of Contents

- [Error Handling Architecture](#error-handling-architecture)
- [Custom Error Pages](#custom-error-pages)
- [HTTP Error Handlers](#http-error-handlers)
- [Exception Handling](#exception-handling)
- [Logging System](#logging-system)
  - [Logging Configuration](#logging-configuration)
  - [Log Levels](#log-levels)
  - [Log Files](#log-files)
  - [Log Filters](#log-filters)
  - [Specific Loggers](#specific-loggers)
  - [Syslog](#syslog)
  - [Audit Logging](#audit-logging)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Tests](#tests)

---

## 🏗️ Error Handling Architecture

The application uses a multi-layered approach to error handling:

1. **HTTP error handlers**: Catch standard HTTP errors (400, 401, 403, 404, 405, 500, 502, 503, 504)
2. **Exception handlers**: Catch specific Python exceptions (ValueError, TypeError, etc.)
3. **Generic handler**: Catches every unhandled exception
4. **Logging system**: Records every error with context
5. **Custom error pages**: Displays user-friendly pages

### Code Location

- **Main file**: `app/__init__.py`
  - Contains all the error handlers (`@app.errorhandler`)
  - Logging configuration
  - Utility functions for error logging

- **Templates**: `app/templates/`
  - `400.html` - Bad Request
  - `401.html` - Unauthorized
  - `403.html` - Forbidden
  - `404.html` - Not Found
  - `405.html` - Method Not Allowed
  - `500.html` - Internal Server Error
  - `502.html` - Bad Gateway
  - `503.html` - Service Unavailable
  - `504.html` - Gateway Timeout

- **Configuration**: `app/config/` (active settings) — see
  [`reference/ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md)
  for the error handling and logging variables

---

## 🎨 Custom Error Pages

### List of Error Pages

| HTTP Code | Name | Template | Description |
|-----------|-----|----------|-------------|
| 400 | Bad Request | `400.html` | Malformed or invalid request |
| 401 | Unauthorized | `401.html` | Authentication required |
| 403 | Forbidden | `403.html` | Access forbidden (insufficient authorization) |
| 404 | Not Found | `404.html` | Resource not found |
| 405 | Method Not Allowed | `405.html` | Unsupported HTTP method |
| 500 | Internal Server Error | `500.html` | Internal server error |
| 502 | Bad Gateway | `502.html` | Invalid response from an upstream server |
| 503 | Service Unavailable | `503.html` | Service temporarily unavailable |
| 504 | Gateway Timeout | `504.html` | Timeout exceeded |

### Template Structure

All error templates extend `base.html` and follow this structure:

```html
{% extends "base.html" %}

{% block title %}Error Title - Kairos{% endblock %}

{% block content %}
<div class="section">
    <div class="container">
        <div class="columns is-centered">
            <div class="column is-6">
                <div class="box has-text-centered">
                    <h1 class="title is-1 has-text-XXX">CODE</h1>
                    <h2 class="title is-3">Error Title</h2>
                    <p class="subtitle is-5">Short description</p>
                    <div class="content">
                        <p>Detailed explanation</p>
                        {% if error_message %}
                        <div class="notification is-warning mt-4">
                            <p><strong>Details:</strong> {{ error_message }}</p>
                        </div>
                        {% endif %}
                    </div>
                    <div class="mt-5">
                        <!-- Action buttons -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Common Features

- **Consistent design**: All templates use Bulma CSS for uniform rendering
- **Navigation**: Buttons to return home, log in/log out
- **Contextual messages**: Displays error details when available
- **Accessibility**: Complies with WCAG standards (contrast, ARIA tags)
- **Responsive**: Adapted for mobile and tablet

---

## 🛡️ HTTP Error Handlers

> Any POST/PUT/PATCH/DELETE request without a
> valid CSRF token (`Flask-WTF` `CSRFProtect`, active app-wide) receives
> a `400 Bad Request` before it even reaches the view — handled by
> Flask-WTF, not by the `@app.errorhandler` handlers below. See
> [`api/API.md`](../api/API.md#authentication).

### Implemented Handlers

#### Client Errors (4xx)

```python
@app.errorhandler(400)
def bad_request_error(error):
    """400 error page - Bad request."""
    log_http_error(400, str(error))
    return render_template("400.html", **get_error_template_data(400, str(error))), 400

@app.errorhandler(401)
def unauthorized_error(error):
    """401 error page - Unauthorized."""
    log_http_error(401, str(error))
    return render_template("401.html", **get_error_template_data(401, "Accès non autorisé")), 401

@app.errorhandler(403)
def forbidden_error(error):
    """403 error page - Forbidden."""
    log_http_error(403, str(error))
    return render_template("403.html", **get_error_template_data(403, str(error))), 403

@app.errorhandler(404)
def not_found_error(error):
    """404 error page - Not found."""
    log_http_error(404, str(error))
    return render_template("404.html", **get_error_template_data(404, str(error))), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    """405 error page - Method not allowed."""
    log_http_error(405, str(error))
    return render_template("405.html", **get_error_template_data(405, str(error))), 405
```

#### Server Errors (5xx)

```python
@app.errorhandler(500)
def internal_server_error(error):
    """500 error page - Internal server error."""
    # Extract the full trace
    exc_type, exc_value, exc_traceback = None, None, None
    if hasattr(error, 'exc_info') and error.exc_info:
        exc_type, exc_value, exc_traceback = error.exc_info
    
    # Full logging
    error_message = str(error) if str(error) else "Erreur interne du serveur"
    log_http_error(500, error_message, (exc_type, exc_value, exc_traceback) if exc_type else None)
    
    # AJAX support
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur interne du serveur s\'est produite.',
            'code': 500
        }), 500
    
    return render_template("500.html", **get_error_template_data(500, error_message)), 500

@app.errorhandler(502)
def bad_gateway_error(error):
    """502 error page - Bad gateway."""
    log_http_error(502, str(error))
    return render_template("502.html", **get_error_template_data(502, "Le serveur a reçu une réponse invalide")), 502

@app.errorhandler(503)
def service_unavailable_error(error):
    """503 error page - Service unavailable."""
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
    """504 error page - Gateway timeout."""
    log_http_error(504, str(error))
    return render_template("504.html", **get_error_template_data(504, "Le serveur n'a pas répondu à temps")), 504
```

### Exception Handlers

```python
@app.errorhandler(Exception)
def handle_exception(error):
    """Generic exception handler."""
    # Don't interfere with HTTP errors already handled
    if hasattr(error, 'code') and error.code in [400, 401, 403, 404, 405, 500, 502, 503, 504]:
        return error
    
    # Logging
    exc_type, exc_value, exc_traceback = type(error), error, error.__traceback__
    log_http_error(500, f"Unhandled exception: {str(error)}", (exc_type, exc_value, exc_traceback))
    
    # AJAX support
    if request and request.accept_mimetypes.accept_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Une erreur inattendue s\'est produite.',
            'code': 500
        }), 500
    
    return render_template("500.html", **get_error_template_data(500, "Une erreur inattendue s'est produite")), 500

@app.errorhandler(sqlite3.OperationalError)
def handle_database_error(error):
    """SQLite error handler."""
    error_message = str(error)
    log_http_error(500, f"Database error: {error_message}")
    
    # Specific messages
    if "locked" in error_message.lower():
        error_message = "La base de données est temporairement verrouillée. Veuillez réessayer dans quelques instants."
    else:
        error_message = "Une erreur de base de données s'est produite. Veuillez réessayer plus tard."
    
    # AJAX support
    if request and request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Database Error', 'message': error_message, 'code': 500}), 500
    
    return render_template("500.html", **get_error_template_data(500, error_message)), 500

@app.errorhandler(ValueError)
def handle_value_error(error):
    """Validation error handler."""
    log_http_error(400, f"Validation error: {str(error)}")
    
    if request and request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Validation Error', 'message': str(error), 'code': 400}), 400
    
    return render_template("400.html", **get_error_template_data(400, str(error))), 400

@app.errorhandler(TypeError)
def handle_type_error(error):
    """Type error handler."""
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

## 📝 Logging System

The logging system provides granular, secure, and extensible
management. Defined in `app/utils/logging/logger.py`
(function `configure_logging()`), called from `app/__init__.py` when
the application is created.

### Logging Configuration

The default values are read from environment variables
(see [`reference/ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md)):

```python
# Main log level
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# File size and number of backups
LOG_FILE_SIZE = int(os.environ.get("LOG_FILE_SIZE", 5 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))

# Log directory
LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')

# Log file names
LOG_FILE_APP = "kairos-app.log"
LOG_FILE_ERRORS = "kairos-errors.log"
LOG_FILE_HTTP = "kairos-http-errors.log"
LOG_FILE_DEBUG = "kairos-debug.log"
LOG_FILE_AUDIT = "kairos-audit.log"

# Log levels per module
LOG_LEVEL_APP = os.environ.get("LOG_LEVEL_APP", LOG_LEVEL)
LOG_LEVEL_ERRORS = os.environ.get("LOG_LEVEL_ERRORS", "ERROR")
LOG_LEVEL_HTTP = os.environ.get("LOG_LEVEL_HTTP", "WARNING")
LOG_LEVEL_DEBUG = os.environ.get("LOG_LEVEL_DEBUG", "DEBUG")
LOG_LEVEL_AUDIT = os.environ.get("LOG_LEVEL_AUDIT", "INFO")

# Syslog for production
SYSLOG_ENABLED = os.environ.get("SYSLOG_ENABLED", "false").lower() == "true"
SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS", "/dev/log")
SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY", "local0")

# Security filters
LOG_FILTER_SENSITIVE = os.environ.get("LOG_FILTER_SENSITIVE", "true").lower() == "true"
```

### Log Levels

The system supports every standard Python log level:

| Level | Description | Usage |
|--------|-------------|-------------|
| **DEBUG** | Detailed information for debugging | Development only |
| **INFO** | General information about operation | Development and production |
| **WARNING** | Warnings for potentially problematic situations | Production |
| **ERROR** | Errors that must be investigated | Production |
| **CRITICAL** | Critical errors requiring immediate action | Production |

**Recommendations by environment:**
- **Development**: `LOG_LEVEL=DEBUG` to see every detail
- **Testing**: `LOG_LEVEL=INFO` for a good balance
- **Production**: `LOG_LEVEL=WARNING` or `ERROR` to reduce volume

### Log Files

The system generates several log files with automatic rotation:

| File | Level | Description | Rotation |
|---------|--------|-------------|----------|
| `logs/kairos-app.log` | INFO | General application logs | 5 MB, 10 backups |
| `logs/kairos-errors.log` | ERROR | All errors with traces | 5 MB, 10 backups |
| `logs/kairos-http-errors.log` | WARNING | HTTP errors with context | 5 MB, 10 backups |
| `logs/kairos-debug.log` | DEBUG | Detailed debug logs | 5 MB, 10 backups |
| `logs/kairos-audit.log` | INFO | User actions for auditing | 5 MB, 10 backups |
| `logs/kairos-sql.log` | DEBUG | SQL queries (if SQLALCHEMY_ECHO=True) | 5 MB, 10 backups |
| `logs/kairos-auth.log` | INFO | Authentication logs | 5 MB, 10 backups |
| `logs/kairos-automation.log` | INFO | Automated task logs | 5 MB, 10 backups |

### Log Filters

A special filter (`SensitiveDataFilter`) is applied to automatically mask sensitive information in the logs:

- Passwords (`password=...`)
- Secrets (`secret=...`)
- Tokens (`token=...`)
- API keys (`api_key=...`, `apikey=...`)
- Authentication information (`auth=...`)

**Example:**
```
# Before filtering
"User login: email=user@example.com, password=secret123"

# After filtering
"User login: email=user@example.com, password=***"
```

Filtering can be disabled with `LOG_FILTER_SENSITIVE=false`.

### Specific Loggers

In addition to the main logger, several specialized loggers are available:

| Logger | Name | Description |
|--------|-----|-------------|
| Main logger | `app.logger` | General application logs |
| HTTP errors | `http_errors` | HTTP errors with IP/user context |
| Audit | `audit` | User actions for tracking |
| SQL | `sqlalchemy.engine` | SQL queries (if enabled) |
| Authentication | `flask_login` | Login/logout events |
| Automation | `automation` | Scheduled and automated tasks |

**Using specific loggers:**
```python
# HTTP logger
from app import http_error_logger
http_error_logger.error("Erreur 500", extra={'ip': '192.168.1.1', 'user': 'admin'})

# Audit logger
import logging
audit_logger = logging.getLogger('audit')
audit_logger.info("User admin deleted user 123")

# Custom logger
from app import get_logger
custom_logger = get_logger('my_module')
custom_logger.info("Message spécifique au module")
```

### Syslog

For production environments, the system can send logs to syslog:

```bash
# Enable
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log  # or a network address
export SYSLOG_FACILITY=local0
```

Logs are formatted for syslog with the `Kairos` prefix.

### Audit Logging

An audit system makes it possible to trace important user actions:

```python
from app import log_audit_action

# Log a successful action
log_audit_action("user_login", user=current_user, path="/login", status="success")

# Log a failed action
log_audit_action("delete_user", user=current_user, path="/admin/users/123", 
                 status="failure", details="User not found")
```

**Audit log format:**
```
2024-01-15 10:30:45 - audit - INFO - AUDIT: user_login - User: admin - Status: success - Path: /login
```

### Log Format

#### General Logs
```
2024-01-15 10:30:45 - app - INFO - Application started
```

#### HTTP Error Logs
```
2024-01-15 10:31:23 - ERROR - IP: 192.168.1.100 - Path: /admin/users - User: John Doe - Error: HTTP 403 - Forbidden
```

#### Full Error Logs
```
2024-01-15 10:32:15 - app - ERROR - HTTP 500 - Internal Server Error

Traceback (most recent call last):
  File "/path/to/app/__init__.py", line 100, in internal_server_error
    return render_template("500.html")
  File "/path/to/flask/template.py", line 123, in render_template
    ...
ValueError: Invalid template name
```

#### Audit Logs
```
2024-01-15 10:35:00 - audit - INFO - AUDIT: delete_user - User: admin - Status: success - Path: /admin/users/456
```

### Utility Functions

```python
def log_http_error(error_code, error_message=None, exc_info=None):
    """Log an HTTP error with contextual information."""
    ip = request.remote_addr if request else 'unknown'
    path = request.path if request else 'unknown'
    user = current_user.name if hasattr(current_user, 'name') and current_user.is_authenticated else 'anonymous'
    
    error_msg = f"HTTP {error_code} - {error_message or error_code}"
    
    # Add the full trace if available
    if exc_info:
        error_msg += f"\n{traceback.format_exception(*exc_info)}"
    
    # Log to the dedicated HTTP errors logger
    http_error_logger.error(
        error_msg,
        extra={'ip': ip, 'path': path, 'user': user}
    )
    
    # Also log to the main logger depending on the level
    if error_code >= 500:
        app.logger.error(f"Erreur serveur {error_code}: {error_message or error_code} - Path: {path}")
    elif error_code >= 400:
        app.logger.warning(f"Erreur client {error_code}: {error_message or error_code} - Path: {path}")


def log_audit_action(action, user=None, path=None, status="success", details=None):
    """Log a user action for auditing."""
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
    """Get a specific logger with the default configuration."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Add a default handler if none exists
        handler = RotatingFileHandler(
            os.path.join(Config.LOG_DIR, f'kairos-{name}.log'),
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

### Configuration Settings

Via environment variables (`app/config/`), several settings are available to configure error handling:

```python
# Error handling configuration
DEBUG_ERRORS = os.environ.get("DEBUG_ERRORS", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 10
LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')

# Show custom error pages
SHOW_CUSTOM_ERROR_PAGES = True

# Default messages
ERROR_500_MESSAGE = "Une erreur interne du serveur s'est produite. Veuillez réessayer plus tard."
ERROR_503_MESSAGE = "Service temporairement indisponible. Veuillez réessayer dans quelques instants."
ERROR_503_RETRY_AFTER = 300  # 5 minutes
```

### Environment Variables

#### General Configuration

| Variable | Default value | Description |
|----------|-------------------|-------------|
| `DEBUG_ERRORS` | `false` | Show error details in development |
| `LOG_LEVEL` | `INFO` | Main logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_DIR` | `./logs` | Directory for log files |
| `FLASK_ENV` | `default` | Environment (development, production, testing) |

#### Log File Configuration

| Variable | Default value | Description |
|----------|-------------------|-------------|
| `LOG_FILE_SIZE` | `5242880` (5 MB) | Maximum size of log files |
| `LOG_BACKUP_COUNT` | `10` | Number of backup files |
| `LOG_FILE_APP` | `kairos-app.log` | Name of the main log file |
| `LOG_FILE_ERRORS` | `kairos-errors.log` | Name of the errors file |
| `LOG_FILE_HTTP` | `kairos-http-errors.log` | Name of the HTTP errors file |
| `LOG_FILE_DEBUG` | `kairos-debug.log` | Name of the debug file |
| `LOG_FILE_AUDIT` | `kairos-audit.log` | Name of the audit file |

#### Log Levels per Module

| Variable | Default value | Description |
|----------|-------------------|-------------|
| `LOG_LEVEL_APP` | `LOG_LEVEL` | Log level for the application |
| `LOG_LEVEL_ERRORS` | `ERROR` | Log level for errors |
| `LOG_LEVEL_HTTP` | `WARNING` | Log level for HTTP errors |
| `LOG_LEVEL_DEBUG` | `DEBUG` | Log level for debugging |
| `LOG_LEVEL_AUDIT` | `INFO` | Log level for auditing |

#### Syslog

| Variable | Default value | Description |
|----------|-------------------|-------------|
| `SYSLOG_ENABLED` | `false` | Enable sending to syslog |
| `SYSLOG_ADDRESS` | `/dev/log` | Syslog address (file or network) |
| `SYSLOG_FACILITY` | `local0` | Syslog facility |

#### Security

| Variable | Default value | Description |
|----------|-------------------|-------------|
| `LOG_FILTER_SENSITIVE` | `true` | Filter sensitive data in the logs |

### Environments

#### Development
```bash
# Base configuration
export FLASK_ENV=development
export DEBUG_ERRORS=true
export LOG_LEVEL=DEBUG

# Advanced configuration
export LOG_LEVEL_APP=DEBUG
export LOG_LEVEL_DEBUG=DEBUG
export LOG_FILTER_SENSITIVE=true

# Disable syslog in development
export SYSLOG_ENABLED=false
```

#### Production
```bash
# Base configuration
export FLASK_ENV=production
export DEBUG_ERRORS=false
export LOG_LEVEL=WARNING

# Advanced configuration
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_LEVEL_HTTP=WARNING
export LOG_LEVEL_AUDIT=INFO

# Enable syslog in production
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export SYSLOG_FACILITY=local0

# Security
export LOG_FILTER_SENSITIVE=true
```

#### Tests
```bash
export FLASK_ENV=testing
export FLASK_TESTING=true
export LOG_LEVEL=DEBUG

# Disable syslog and filtering for tests
export SYSLOG_ENABLED=false
export LOG_FILTER_SENSITIVE=false
```

#### Full Example for Production with Remote Syslog
```bash
# Flask configuration
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here

# Logging configuration
export LOG_LEVEL=WARNING
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_DIR=/var/log/kairos

# Syslog to a remote server
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=192.168.1.100:514
export SYSLOG_FACILITY=local0

# Security
export LOG_FILTER_SENSITIVE=true

# Database
export DATABASE_URL=postgresql://user:password@localhost/kairos
```

---

## ✅ Best Practices

### For Developers

1. **Always use the error handlers**
   - Don't return error codes directly without going through the handlers
   - Use `abort(404)` or `abort(403)` for standard errors

2. **Systematic logging**
   - Always log errors with `log_http_error()` or `app.logger.error()`
   - Include context (user, IP, path, etc.)
   - Use the appropriate log levels (DEBUG, INFO, WARNING, ERROR)

3. **Clear error messages**
   - Use messages that are understandable for end users
   - Avoid displaying technical details in production
   - Sensitive data is automatically filtered

4. **Exception handling**
   - Catch specific exceptions with dedicated handlers
   - Use the generic handler as a safety net

5. **AJAX support**
   - Always check whether the request is AJAX and return JSON if needed
   - Use `request.accept_mimetypes.accept_json`

6. **Audit Logging**
   - Log important user actions with `log_audit_action()`
   - Include the user, the path, and the status (success/failure)

7. **Specific Loggers**
   - Use `get_logger(name)` to create module-specific loggers
   - Use dedicated loggers for SQL, auth, automation

8. **Security**
   - Never log sensitive data (passwords, tokens, etc.)
   - The `SensitiveDataFilter` filter handles this automatically

### Code Example

```python
from flask import abort, jsonify, request
from app import db, log_http_error, log_audit_action, get_logger
from app.models import User

# Logger specific to this module
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
        
        # Log the successful action
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
        
        # Log the audit action
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

### For Administrators

1. **Log monitoring**
   - Regularly check `logs/kairos-errors.log` for critical errors
   - Check `logs/kairos-http-errors.log` for HTTP errors
   - Check `logs/kairos-audit.log` for suspicious user actions

2. **Log rotation**
   - Files are automatically rotated at the configured size (5 MB by default)
   - 10 backup files are kept by default
   - Configure `LOG_FILE_SIZE` and `LOG_BACKUP_COUNT` according to your needs

3. **Log backups**
   - Archive old logs before deletion
   - Keep logs for a sufficient period (recommended: 30-90 days)

4. **Production configuration**
   - Disable `DEBUG_ERRORS` in production
   - Use `LOG_LEVEL=WARNING` or `ERROR` to reduce volume
   - Configure syslog for centralized logging
   - Enable `LOG_FILTER_SENSITIVE=true` for security

5. **Monitoring**
   - Configure alerts for critical errors (ERROR and CRITICAL levels)
   - Monitor the size of log files
   - Configure external monitoring tools (Prometheus, ELK, etc.)

6. **Log analysis**
   - Use tools like `grep`, `awk`, or SIEM solutions
   - Analyze error patterns to identify recurring issues
   - Monitor response times and 5xx errors

### Advanced Configuration Example

```python
# In your application code

# Custom logging configuration
import logging
from app import get_logger

# Create a logger for a specific module
payment_logger = get_logger('payments')
payment_logger.setLevel(logging.INFO)

# Log with additional information
payment_logger.info(
    "Payment processed",
    extra={
        'user_id': current_user.id,
        'amount': 100.00,
        'currency': 'EUR',
        'transaction_id': 'txn_12345'
    }
)

# Using the audit logger for sensitive actions
from app import log_audit_action

# Log a sensitive action
log_audit_action(
    "change_password",
    user=current_user,
    path="/account/change-password",
    status="success",
    details="Password changed successfully"
)
```

### For Administrators

1. **Log monitoring**
   - Regularly check `logs/kairos-errors.log`
   - Configure alerts for critical errors

2. **Log rotation**
   - Files are automatically rotated at 5 MB
   - 10 backup files are kept

3. **Log backups**
   - Archive old logs before deletion
   - Keep logs for a sufficient period

4. **Production configuration**
   - Disable `DEBUG_ERRORS` in production
   - Use `LOG_LEVEL=WARNING` or `ERROR`
   - Configure an external monitoring system

---

## 🧪 Tests

### Running the Tests

```bash
# Run all error handler tests
pytest tests/integration/test_error_handlers.py -v

# Run a specific test
pytest tests/integration/test_error_handlers.py::TestCustomErrorPages::test_500_template_exists -v
```

### Test Structure

The tests are organized in `tests/integration/test_error_handlers.py`:

- **TestErrorHandlers**: Tests for the HTTP error handlers
- **TestCustomErrorPages**: Tests for the error templates
- **TestErrorHandlerFunctions**: Tests for the utility functions
- **TestErrorHandlerRoutes**: Tests for the routes that trigger errors
- **TestDatabaseErrorHandler**: Tests for the database error handler
- **TestExceptionHandlers**: Tests for the exception handlers
- **TestLoggingConfiguration**: Tests for the logging configuration
- **TestSensitiveDataFilter**: Tests for the sensitive data filter
- **TestAuditLogging**: Tests for the audit system

### Test Example

```python
def test_404_error_handler(self, client):
    """Test the 404 error handler."""
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    assert b"404" in response.data or b"Not Found" in response.data

def test_500_template_content(self, app):
    """Test the content of the 500.html template."""
    with app.app_context():
        from flask import render_template
        html = render_template("500.html")
        assert b"500" in html.encode()
        assert b"Erreur interne" in html.encode()

# Test the sensitive data filter
def test_sensitive_data_filter(self, app):
    """Test that the filter masks sensitive data."""
    with app.app_context():
        from app import SensitiveDataFilter
        import logging
        
        # Create a filter
        filter = SensitiveDataFilter()
        
        # Create a log record with sensitive data
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="User login: password=secret123, token=abc123",
            args=(),
            exc_info=None
        )
        
        # Apply the filter
        filter.filter(record)
        
        # Check that the sensitive data is masked
        assert "password=***" in record.msg
        assert "token=***" in record.msg
        assert "secret123" not in record.msg
        assert "abc123" not in record.msg

# Test the audit system
def test_audit_logging(self, app):
    """Test that audit logging works."""
    with app.app_context():
        from app import log_audit_action
        import logging
        
        # Capture the logs
        with app.app_context():
            # Create a mock user
            class MockUser:
                name = "test_user"
            
            # Log an action
            log_audit_action(
                "test_action",
                user=MockUser(),
                path="/test",
                status="success",
                details="Test details"
            )
            
            # Check that the log was recorded
            audit_logger = logging.getLogger('audit')
            assert len(audit_logger.handlers) > 0
```

### Running the Logging Tests

```bash
# Run all logging tests
pytest tests/integration/test_error_handlers.py::TestLoggingConfiguration -v

# Run the sensitive data filter tests
pytest tests/integration/test_error_handlers.py::TestSensitiveDataFilter -v

# Run the audit tests
pytest tests/integration/test_error_handlers.py::TestAuditLogging -v

# Run a specific test
pytest tests/integration/test_error_handlers.py::TestLoggingConfiguration::test_logging_setup -v
```

---

## 📚 Additional Resources

- [Flask Error Handling Documentation](https://flask.palletsprojects.com/en/3.1.x/errorhandling/)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [WCAG Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 📝 Changelog

### Version 1.0 (June 2026)
- Added custom error pages for all the main HTTP codes
- Implemented the logging system with file rotation
- Added HTTP error and exception handlers
- Centralized configuration in `app/config/`
- Comprehensive tests for all the error handlers

---

*Documentation generated for Kairos - Improved Error Handling*
