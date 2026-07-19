# Error Handling in Kairos

This document describes the improved error handling and the advanced logging system in the Kairos application.

## 📋 Table of Contents

- [Error Handling Architecture](#️-error-handling-architecture)
- [Custom Error Pages](#-custom-error-pages)
- [HTTP Error Handlers](#️-http-error-handlers)
- [Exception Handlers](#exception-handlers)
- [Logging System](#-logging-system)
  - [Logging Configuration](#logging-configuration)
  - [Log Levels](#log-levels)
  - [Log Files](#log-files)
  - [Log Filters](#log-filters)
  - [Specific Loggers](#specific-loggers)
  - [Syslog](#syslog)
  - [Audit Logging](#audit-logging)
- [Configuration](#️-configuration)
- [Best Practices](#-best-practices)
- [Tests](#-tests)

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
  - Registers every handler via `app.register_error_handler(...)` at
    the end of `create_app()` — not the `@app.errorhandler` decorator
    form (that requires the app instance to already exist at import
    time, which the factory pattern here doesn't allow)
  - Calls `configure_logging()` (see below)

- **Handler/logging utilities**: `app/utils/logging/logger.py`
  (`configure_logging`, `get_logger`, `log_http_error`,
  `log_audit_action`, `get_error_template_data`, `SensitiveDataFilter`)
  — re-exported from `app/__init__.py` for backward-compatible
  `from app import ...` imports.

- **Templates**: `app/templates/`, all extending `base.html` and
  rendering through the shared `macros/errors.html::error_page` macro
  (see below)
  - `400.html` - Bad Request
  - `401.html` - Unauthorized
  - `403.html` - Forbidden
  - `404.html` - Not Found
  - `405.html` - Method Not Allowed
  - `500.html` - Internal Server Error
  - `502.html` - Bad Gateway
  - `503.html` - Service Unavailable
  - `504.html` - Gateway Timeout

- **Configuration**: `app/config/base.py` (`LOG_LEVEL`, `LOG_FORMAT`) —
  see [`reference/ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md#-logging-configuration)
  for every logging-related environment variable actually read by the
  application.

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

Every error template extends `base.html` and delegates its markup to
the shared `macros/errors.html::error_page` macro — there is no
per-page duplicated layout to keep in sync across the 9 codes:

```html
{# app/templates/404.html #}
{% extends "base.html" %}
{% from "macros/errors.html" import error_page with context %}

{% block title %}{{ _("Page non trouvée") }} - Kairos{% endblock %}

{% block content %}
{% call error_page(code=404, title=_("Page non trouvée"), subtitle=_("La page que vous cherchez n'existe pas."), color="text-warning") %}
<p role="alert" aria-live="assertive">
    {{ _("Vérifiez l'URL ou retournez à la page d'accueil.") }}
</p>
{% endcall %}
{% endblock %}
```

The macro itself (`app/templates/macros/errors.html`) renders a
daisyUI `card`, a primary "back to home" button (overridable), any
`secondary` action buttons the caller passes in, and a
login/logout toggle based on `current_user.is_authenticated`. No
`error_message`/`error_code` template variable is involved — each
template's copy is a hardcoded, translated string via `_()`, not data
threaded through from the handler.

### Common Features

- **Consistent design**: every page renders through the same
  `error_page` macro (Tailwind CSS 4 + daisyUI 5, see
  `architecture/ARCHITECTURE.md`)
- **Navigation**: a "back to home" button plus a login/logout toggle
- **i18n**: every string goes through `_()` (Flask-Babel) — see
  "Multi-language support" in `CLAUDE.md`
- **Accessibility**: `role="alert"`/`aria-live`/`aria-labelledby` on the
  error region, `aria-label` on every action button

---

## 🛡️ HTTP Error Handlers

> Any POST/PUT/PATCH/DELETE request without a
> valid CSRF token (`Flask-WTF` `CSRFProtect`, active app-wide) receives
> a `400 Bad Request` before it even reaches the view — handled by
> Flask-WTF, not by the `@app.errorhandler` handlers below. See
> [`api/API.md`](../api/API.md#authentication).

### Implemented Handlers

All 9 standard HTTP codes share a single factory instead of one
hand-written function per code:

```python
def _make_http_error_handler(code: int):
    def _handler(error):
        log_http_error(code, getattr(error, "description", str(error)))
        return render_template(f"{code}.html"), code

    return _handler


def create_app(config_object: str | None = None):
    ...
    for error_code in (400, 401, 403, 404, 405, 500, 502, 503, 504):
        app.register_error_handler(error_code, _make_http_error_handler(error_code))
```

No JSON/AJAX branch, no `retry_after` handling for 503, no
`get_error_template_data()` call — the templates carry their own
translated copy (see "Template Structure" above), so nothing needs to
be threaded through `render_template()`. `error.description` (set by
Werkzeug/`abort(code, description=...)`) is only ever used for the log
line, never shown to the user.

### Exception Handlers

Only `ValueError`/`TypeError` are registered as exception handlers —
anything else propagates as an unhandled exception, which Werkzeug
converts to a 500 that the `500` handler above already catches:

```python
def handle_value_error(error):
    """Handler for ValueError not caught by the routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


def handle_type_error(error):
    """Handler for TypeError not caught by the routes."""
    log_http_error(400, str(error))
    return render_template("400.html"), 400


app.register_error_handler(ValueError, handle_value_error)
app.register_error_handler(TypeError, handle_type_error)
```

`handle_database_error` (for `sqlite3.OperationalError`) and
`handle_exception` (a generic `Exception` catch-all) are also defined
in `app/__init__.py` and covered by their own tests
(`TestDatabaseErrorHandler`, `TestExceptionHandlers`), but **are not
registered** via `register_error_handler()` — calling either directly
still works (used that way by their tests), but neither fires
automatically for a real request. The generic 500 handler above is
what actually catches an uncaught database error or exception in
production.

---

## 📝 Logging System

Defined in `app/utils/logging/logger.py` (function `configure_logging()`),
called once from `app/__init__.py::create_app()`.

### Logging Configuration

Only two environment variables control level/format globally — see
[`reference/ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md#-logging-configuration)
for the complete, verified list:

```python
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = os.environ.get(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10 MiB
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))
LOG_FILE = os.environ.get("LOG_FILE")  # optional, additional file on the root logger
```

There is no per-module log level (`LOG_LEVEL_APP`/`LOG_LEVEL_ERRORS`/...),
no configurable log directory (always `logs/` under the working
directory, not overridable), and no syslog support — an earlier
version of this document described both, neither exists in the code.

### Log Levels

Standard Python log levels — `DEBUG`, `INFO`, `WARNING`, `ERROR`,
`CRITICAL` — controlled by the single `LOG_LEVEL` variable above (no
per-module override).

### Log Files

`configure_logging()` creates exactly 5 rotating files under `logs/`
(`RotatingFileHandler`, `LOG_MAX_BYTES`/`LOG_BACKUP_COUNT` from above
applied to every one of them) — no `sql.log`, `auth.log`, or syslog
output exists:

| File | Logger | Minimum level | Written by |
|---------|--------|--------|-------------|
| `logs/app.log` | `app.logger` (Flask's own) | `LOG_LEVEL` | every `app.logger.*()` call |
| `logs/error.log` | `app.logger` | `ERROR` | same logger, `ERROR`+ only |
| `logs/debug.log` | `app.logger` | `DEBUG` | same logger, everything |
| `logs/http_errors.log` | `http_errors` | `WARNING` | `log_http_error()` |
| `logs/audit.log` | `audit` | `INFO` | `log_audit_action()`, via `AuditService.log()` |

### Log Filters

`SensitiveDataFilter` (`app/utils/logging/logger.py`) masks
`password=`/`token=`/`api_key=` (case-insensitive) in every message
and argument before it's written, on every handler above. It is
**always active** — there is no environment variable to disable it.

```python
_PATTERN = re.compile(r"(password|token|api_key)=\S+", re.IGNORECASE)
```

**Example:**
```
# Before filtering
"User login: email=user@example.com, password=secret123"

# After filtering
"User login: email=user@example.com, password=***"
```

Only this exact `key=value` shape is masked — a positional secret
embedded in a URL (e.g. an Apprise webhook URL, see "External
notifications (Apprise)" in `CLAUDE.md`) would **not** be caught by
this regex. The mitigation there is discipline at the call site (never
log the value), not a regex extension.

### Specific Loggers

| Logger | Name | Written by |
|--------|-----|-------------|
| Main logger | `app.logger` (Flask's own) | anywhere via `current_app.logger`/`app.logger` |
| HTTP errors | `http_errors` | `log_http_error(code, message)` |
| Audit | `audit` | `log_audit_action(...)`, called by `AuditService.log()` |

`get_logger(name)` (`app/utils/logging/logger.py`) returns
`logging.getLogger(name)`, adding a single `StreamHandler` +
`SensitiveDataFilter` only if that logger has no handler yet — mainly
useful for ad-hoc scripts/tests, not a module-per-file convention used
throughout `app/`.

### Audit Logging

**`AuditService.log()`** (`app/services/audit_service.py`) is the
single write point for the audit trail — not `log_audit_action()`
directly. It resolves the acting user, captures
`flask.request.remote_addr`, writes an `AuditLog` database row
(queryable at `/admin/audit-log`), and *then* calls
`log_audit_action()` as a defense-in-depth file copy — wrapped in a
bare `try/except` so a logging failure can never break the business
action it's recording. See "Audit trail" in `CLAUDE.md` for the full
design (namespaced `action` strings, call-site placement rule, retention).

```python
def log_audit_action(
    action: str, user: Any = None, path: str | None = None,
    status: str = "success", details: str | None = None,
) -> None:
    logger = logging.getLogger("audit")
    username = getattr(user, "name", None) or "anonymous"
    logger.info(
        f"action={action} user={username} path={path} status={status} details={details}"
    )
```

### Utility Functions

```python
def log_http_error(code: int, message: str) -> None:
    """Log an HTTP error on the dedicated 'http_errors' logger."""
    logger = logging.getLogger("http_errors")
    logger.error(f"HTTP {code}: {message}")


def get_error_template_data(code: int, message: str) -> dict:
    """Build {'error_code': ..., 'error_message': ...} - defined for
    tests/backward compatibility, not called by the current handlers
    (see "HTTP Error Handlers" above)."""
    return {"error_code": code, "error_message": message}
```

---

## ⚙️ Configuration

Error handling itself has no dedicated settings — the only knobs are
the logging ones already covered above (`LOG_LEVEL`, `LOG_FORMAT`,
`LOG_FILE`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`), read directly by
`app/config/base.py::Config` and `app/utils/logging/logger.py`. There
is no `DEBUG_ERRORS`, no per-module `LOG_LEVEL_*`, no `LOG_DIR`
override, and no syslog support — an earlier version of this document
described all of these; none of them exist in the code. `FLASK_DEBUG`
(not `FLASK_ENV`) is what actually toggles Werkzeug's interactive
debugger — see
[`reference/ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md#-flask-configuration).

### Example: production

```bash
LOG_LEVEL=WARNING
LOG_FILE=/var/log/kairos/kairos.log   # optional, in addition to logs/*.log
LOG_MAX_BYTES=10485760                 # 10 MiB, the default
LOG_BACKUP_COUNT=5                     # the default
```

### Example: development

```bash
LOG_LEVEL=DEBUG
```

---

## ✅ Best Practices

### For Developers

1. **Let the registered handlers do the work** — `abort(404)`/
   `abort(403)`/etc. for standard errors, rather than hand-building a
   response; the 9 codes in "Implemented Handlers" above already log
   and render the right template.
2. **`log_http_error(code, message)`** for anything not already
   covered by a registered handler — it only writes to the
   `http_errors` logger, nothing else.
3. **`AuditService.log(...)`** (not `log_audit_action()` directly) for
   business-significant actions — see "Audit trail" in `CLAUDE.md` for
   the call-site placement rule (after the triggering action's own
   commit) and the full list of `action` namespaces in use.
4. **Never log secrets directly** — `SensitiveDataFilter` only masks
   the `key=value` shape (`password=`/`token=`/`api_key=`); a secret
   embedded any other way (e.g. positionally in a URL) is not caught,
   so don't rely on it as the only safeguard.

### For Administrators

1. **Log monitoring** — `logs/error.log` for application errors,
   `logs/http_errors.log` for HTTP-level errors, `logs/audit.log` for
   user actions (also queryable in the DB at `/admin/audit-log`).
2. **Log rotation** — every file rotates at `LOG_MAX_BYTES` (10 MiB
   default), keeping `LOG_BACKUP_COUNT` backups (5 default); both are
   the only two variables controlling this, set once for every log
   file, not per-file.
3. **Production configuration** — `LOG_LEVEL=WARNING` or `ERROR` to
   reduce volume; there is no debug-mode toggle specific to error
   pages (`FLASK_DEBUG` controls Werkzeug's interactive debugger
   instead, and must stay `false` in production regardless of log
   level — see `reference/ENVIRONMENT_VARIABLES.md`).
4. **External monitoring** — `PROMETHEUS_ENABLED` exposes `/metrics`;
   `/health`/`/ready` are always on for Kubernetes-style probes. There
   is no built-in alerting; wire log files or `/metrics` into whatever
   monitoring stack you already run.

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
- **TestGetLogger**: Tests for `get_logger()`

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
