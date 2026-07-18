# Environment Variables - Kairos

> **Complete documentation of every environment variable available to configure Kairos**

---

## 📋 Table of Contents

- [🔐 Basic Flask Configuration](#-basic-flask-configuration)
- [🗄️ Database Configuration](#️-database-configuration)
- [🔒 Authentication Configuration](#-authentication-configuration)
- [⚠️ Error Configuration](#️-error-configuration)
- [📝 Logging Configuration](#-logging-configuration)
- [🔒 Security Configuration](#-security-configuration)
- [📊 Default Data Configuration](#-default-data-configuration)
- [📅 Shift Type Configuration](#-shift-type-configuration)
- [📤 ICS Export Configuration](#-ics-export-configuration)
- [📧 Notification Configuration](#-notification-configuration)
- [💾 Backup Configuration](#-backup-configuration)
- [🧹 Automatic Cleanup Configuration](#-automatic-cleanup-configuration)
- [📈 Monitoring Configuration](#-monitoring-configuration)
- [🎯 Configuration by Environment](#-configuration-by-environment)
- [📝 Configuration Examples](#-configuration-examples)
- [⚠️ Best Practices](#️-best-practices)

---

## 🔐 Basic Flask Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `SECRET_KEY` | string | `ta-cle-secrete-ici` | Secret key for Flask. **Must be long, random, and kept secret in production**. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` | ✅ Yes |
| `FLASK_ENV` | string | `development` | Flask environment. Possible values: `development`, `production`, `testing` | ❌ No |
| `FLASK_TESTING` | boolean | `false` | Test mode enabled. Used for unit tests | ❌ No |
| `PUBLIC_BASE_URL` | string | (empty) | Public URL of the app behind a reverse proxy (e.g. `https://schedule.example.com`). Used as a fallback for absolute links (ICS export) when the proxy doesn't correctly pass `X-Forwarded-Host` to `ProxyFix` — otherwise these links leak the backend's internal IP/hostname instead of the correct domain. Leave empty to use `request.host_url` (default behavior) | ❌ No |

**Example:**
```bash
SECRET_KEY=my_secret_key_generated_with_python_secrets
FLASK_ENV=production
FLASK_TESTING=false
PUBLIC_BASE_URL=https://schedule.example.com
```

---

## 🗄️ Database Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DATABASE_URL` | string | `sqlite:///app.db` | Database URI. Supported formats: SQLite, PostgreSQL, MySQL | ✅ Yes |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | boolean | `false` | Disables SQLAlchemy modification tracking (recommended: `false`) | ❌ No |
| `SQLALCHEMY_ECHO` | boolean | `false` | Prints SQL queries to the logs (useful for debugging) | ❌ No |
| `SQLALCHEMY_ENGINE_OPTIONS` | JSON | `{}` | SQLAlchemy engine options in JSON format. Example: `{"connect_args": {"timeout": 30}, "pool_pre_ping": true, "pool_recycle": 3600}` | ❌ No |
| `DATABASE_POOL_SIZE` | integer | `5` | Database connection pool size | ❌ No |
| `DATABASE_MAX_OVERFLOW` | integer | `10` | Maximum number of extra connections | ❌ No |
| `DATABASE_CONNECT_TIMEOUT` | integer | `30` | Timeout for the database connection (in seconds) | ❌ No |
| `DATABASE_POOL_RECYCLE` | integer | `3600` | Recycles connections after this many seconds | ❌ No |

**DATABASE_URL formats:**
```bash
# SQLite (default)
DATABASE_URL=sqlite:///path/to/app.db

# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://user:password@host:port/database

# MySQL / MariaDB
DATABASE_URL=mysql://user:password@host:port/database
DATABASE_URL=mariadb://user:password@host:port/database

# In-memory SQLite (for tests)
DATABASE_URL=sqlite:///:memory:
```

**Required drivers (already included by default in `requirements.txt`, nothing to install):**
- SQLite: built into Python (`sqlite3` module, standard library)
- PostgreSQL: `psycopg[binary]` (psycopg 3)
- MySQL / MariaDB: `PyMySQL` — a 100% pure-Python driver, no system library
  required (`libmariadb-dev`/`libmysqlclient-dev`), neither at install time
  nor at runtime, neither on the host nor in the Docker image

The formats above (without an explicit `+driver` suffix) are automatically
routed to the correct driver — the app rewrites `mysql://`/`mariadb://` to
`mysql+pymysql://`/`mariadb+pymysql://` and `postgres(ql)://` to
`postgresql+psycopg://` internally (see
`app/config/base.py::normalize_database_uri()`), because SQLAlchemy's bare
prefixes default to the classic drivers (`mysqlclient`, `psycopg2`), which
are deliberately not installed here. `SQLALCHEMY_ENGINE_OPTIONS` (above) is
particularly useful with an external MySQL/PostgreSQL server:
`pool_pre_ping`/`pool_recycle` avoid a stale-connection error when the
server closes idle connections (MySQL's `wait_timeout`, often reduced on
managed offerings).

---

## 🔒 Authentication Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `LOGIN_DISABLED` | boolean | `false` | **DANGER**: Completely disables authentication. Never enable in production! | ❌ No |
| `REMEMBER_COOKIE_DURATION` | integer | `86400` | Duration of the "remember me" cookie in seconds (default: 1 day = 86400) | ❌ No |
| `SESSION_PROTECTION` | string | `strong` | Session protection level. Possible values: `none`, `basic`, `strong` | ❌ No |
| `WTF_CSRF_ENABLED` | boolean | `true` | Enables CSRF protection for forms | ❌ No |
| `WTF_CSRF_TIME_LIMIT` | integer | `3600` | Validity duration of the CSRF token in seconds (default: 1 hour) | ❌ No |
| `SESSION_COOKIE_SECURE` | boolean | `false` | Enables the Secure flag for session cookies (recommended: `true` in production with HTTPS) | ❌ No |
| `SESSION_COOKIE_HTTPONLY` | boolean | `true` | Enables the HttpOnly flag for session cookies | ❌ No |
| `SESSION_COOKIE_SAMESITE` | string | `Lax` | SameSite policy for cookies. Possible values: `Lax`, `Strict`, `None` | ❌ No |
| `REMEMBER_COOKIE_SECURE` | boolean | `false` | Enables the Secure flag for the "remember me" cookie | ❌ No |
| `PREFERRED_URL_SCHEME` | string | `http` | Preferred URL scheme. Possible values: `http`, `https` | ❌ No |

### SSO/OIDC (optional)

| Variable | Description | Required |
|----------|-------------|-------------|
| `OIDC_ENABLED` | Enables OIDC authentication (`true`/`false`) | ❌ No |
| `OIDC_ISSUER` | URL of the OIDC provider (e.g. Keycloak realm) | ✅ If `OIDC_ENABLED=true` |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | OIDC client credentials | ✅ If `OIDC_ENABLED=true` |
| `OIDC_REDIRECT_URI` | Callback URL, must be registered on the provider side | ✅ If `OIDC_ENABLED=true` |
| `OIDC_POST_LOGOUT_REDIRECT_URI` | Redirect URL after RP-initiated logout | ❌ No |
| `OIDC_DISABLE_BASIC_AUTH` | Hides the email/password form (`true`/`false`) | ❌ No |
| `OIDC_EMAIL_CLAIM` / `OIDC_NAME_CLAIM` / `OIDC_USERNAME_CLAIM` | Token claim mapping (defaults: `email`, `name`, `preferred_username`) | ❌ No |
| `OIDC_GROUPS_CLAIM` / `OIDC_ROLES_CLAIM` | Optional sync of local groups/roles | ❌ No |
| `OIDC_SIGNATURE_ALGORITHMS` | Token signature algorithm (default `RS256`) | ❌ No |
| `OIDC_SCOPE` | Requested scope (default `openid profile email`) | ❌ No |
| `OIDC_INTERNAL_ISSUER` | Issuer URL reachable by the container, if different from `OIDC_ISSUER` (Docker deployment with the IdP on the same network) | ❌ No |

Full configuration guide:
[`guides/ADMIN_GUIDE.md`](../guides/ADMIN_GUIDE.md#ssooidc-configuration).

---

## ⚠️ Error Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DEBUG_ERRORS` | boolean | `false` | **DANGER**: Shows error details (stack traces). Never enable in production! | ❌ No |
| `SHOW_CUSTOM_ERROR_PAGES` | boolean | `true` | Shows custom error pages | ❌ No |
| `ERROR_500_MESSAGE` | string | `"Une erreur interne du serveur s'est produite. Veuillez reessayer plus tard."` | Custom message for 500 errors | ❌ No |
| `ERROR_503_MESSAGE` | string | `"Service temporairement indisponible. Veuillez reessayer dans quelques instants."` | Custom message for 503 errors | ❌ No |
| `ERROR_503_RETRY_AFTER` | integer | `300` | Retry delay for 503 errors (in seconds) | ❌ No |

---

## 📝 Logging Configuration

> Only the 4 variables below are actually read by
> `app/utils/logging/logger.py`. There is no `LOG_DIR`, `SYSLOG_*`, or
> per-file `LOG_LEVEL_*`/`LOG_FORMAT` setting - logs always go to fixed
> files under `logs/`.

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `LOG_LEVEL` | string | `INFO` | Main log level. Possible values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | ❌ No |
| `LOG_FILE` | string | *(none)* | Path to an optional root log file, in addition to the `app.log`/`error.log`/`debug.log`/`http_errors.log`/`audit.log` files always created under `logs/` (fixed directory, not configurable) | ❌ No |
| `LOG_MAX_BYTES` | integer | `10485760` (10 MB) | Maximum size of each log file before rotation (`RotatingFileHandler`, applies to every file under `logs/`, including `audit.log`) | ❌ No |
| `LOG_BACKUP_COUNT` | integer | `5` | Number of backup files kept after rotation (`app.log.1`, `app.log.2`, ...) | ❌ No |

Sensitive-data filtering (masking `password=`/`token=`/`api_key=` in log
messages, `SensitiveDataFilter`) is always active and cannot be disabled
via an environment variable. `audit.log` (under `logs/`) is written to by
`AuditService.log()`, alongside a database copy browsable via
`/admin/audit-log`.

---

## 🔒 Security Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `SEND_FILE_MAX_AGE_DEFAULT` | integer | `0` | Disables caching for error pages (recommended: `0`) | ❌ No |
| `CORS_ENABLED` | boolean | `false` | Enables CORS (Cross-Origin Resource Sharing) | ❌ No |
| `RATE_LIMIT_ENABLED` | boolean | `true` | Enables rate limiting | ❌ No |
| `RATE_LIMIT_DEFAULT` | string | `"200 per day, 50 per hour"` | Default rate limits in Flask-Limiter format | ❌ No |
| `COMPRESS_ENABLED` | boolean | `true` | Enables Gzip compression of responses | ❌ No |
| `COMPRESS_MIMETYPES` | list | See code | MIME types to compress. Default: `['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']` | ❌ No |

---

## 📊 Default Data Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DEFAULT_ADMIN_EMAIL` | string | `admin@kairos.local` | Email of the default admin user | ❌ No |
| `DEFAULT_ADMIN_PASSWORD` | string | `admin123` | **DANGER**: Password of the default admin user. **Change this value after the first login!** | ❌ No |
| `DEFAULT_GROUP_NAME` | string | `Defaut` | Name of the default group | ❌ No |
| `DEFAULT_GROUP_IN_SCHEDULE` | boolean | `true` | The default group is part of the schedule | ❌ No |
| `DEFAULT_GROUP_IN_ONCALL` | boolean | `true` | The default group is part of the on-call rotation | ❌ No |

---

## 📅 Shift Type Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DEFAULT_SHIFT_TYPES` | JSON | See code | Default shift types in JSON format. Example: `[{"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15}, {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17}]` | ❌ No |

**Default value:**
```json
[
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21}
]
```

---

## 📤 ICS Export Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `ICS_TOKEN_EXPIRY_DAYS` | integer | `365` | Validity duration of the ICS token in days | ❌ No |

The ICS subscription URLs shown to the user (`/profile/ics-token` page)
use `PUBLIC_BASE_URL` if set (see
[🔐 Basic Flask Configuration](#-basic-flask-configuration)), otherwise
`request.host_url` — relevant behind a reverse proxy.

---

## 📧 Notification Configuration

Weekly email reminders (shifts + on-call), sent by the standalone scripts
`scripts/send_shift_notifications.py` (Sunday, 24h before Monday's shifts
start) and `scripts/send_oncall_notifications.py` (Thursday, 24h before
Friday's 9 PM on-call start) — to be triggered via cron, not by the Flask
application itself (see `scripts/cron_example.sh`). One email per week
per user (`notification_log` table in the database, prevents duplicates
if a script is rerun).

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `NOTIFICATIONS_ENABLED` | boolean | `false` | Enables sending email notifications | ❌ No |
| `NOTIFICATION_FROM_EMAIL` | string | `""` | Sender email address | ❌ No (required if enabled) |
| `SMTP_HOST` | string | `""` | SMTP server | ❌ No (required if enabled) |
| `SMTP_PORT` | integer | `587` | SMTP port | ❌ No |
| `SMTP_USERNAME` | string | `""` | SMTP username | ❌ No |
| `SMTP_PASSWORD` | string | `""` | SMTP password | ❌ No |
| `SMTP_USE_TLS` | boolean | `true` | Use TLS for the SMTP connection | ❌ No |
| `SMTP_TIMEOUT` | integer | `10` | SMTP connection timeout in seconds | ❌ No |
| `NOTIFICATION_APP_BASE_URL` | string | `""` | Base URL of the app, for the "view schedule"/"view on-call" link in emails (omitted if empty) | ❌ No |

If `NOTIFICATIONS_ENABLED=false`, or if `NOTIFICATION_FROM_EMAIL`/
`SMTP_HOST` are missing, both scripts exit silently without sending
anything (exit code 0).

---

## 💾 Backup Configuration

Database backup (local and/or S3/S3-compatible), managed by
`scripts/backup_database.py` — to be triggered via cron (see
`scripts/cron_example.sh`) or from the admin interface
(`/admin/backups`). See [`deployment/BACKUP_GUIDE.md`](../deployment/BACKUP_GUIDE.md)
for details.

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `BACKUP_ENABLED` | boolean | `false` | Enables backups (cron script *and* manual creation from the admin UI) | ❌ No |
| `BACKUP_LOCAL_ENABLED` | boolean | `true` | Enables local backups | ❌ No |
| `BACKUP_LOCAL_DIR` | string | `backups` | Local backup directory (in Docker, use a path under `/app/data` for persistence) | ❌ No |
| `BACKUP_S3_ENABLED` | boolean | `false` | Enables S3/S3-compatible backups (requires `boto3`) | ❌ No |
| `BACKUP_S3_BUCKET` | string | `""` | S3 bucket name | ❌ No (required if enabled) |
| `BACKUP_S3_ENDPOINT` | string | `""` | S3-compatible endpoint (MinIO, etc.) — empty for AWS S3 | ❌ No |
| `BACKUP_S3_REGION` | string | `eu-west-1` | S3 region | ❌ No |
| `BACKUP_S3_ACCESS_KEY` | string | `""` | S3 access key | ❌ No |
| `BACKUP_S3_SECRET_KEY` | string | `""` | S3 secret key | ❌ No |
| `BACKUP_S3_PREFIX` | string | `kairos` | S3 key prefix | ❌ No |
| `BACKUP_S3_USE_SSL` | boolean | `true` | Use SSL for the S3 connection | ❌ No |
| `BACKUP_RETENTION_DAYS` | integer | `30` | Number of days of retention | ❌ No |
| `BACKUP_MAX_BACKUPS` | integer | `30` | Maximum number of backups kept | ❌ No |
| `BACKUP_COMPRESS` | boolean | `true` | Compress local backups (gzip) | ❌ No |
| `BACKUP_VERIFY` | boolean | `true` | Verify integrity after creation | ❌ No |
| `BACKUP_NOTIFY_ON_SUCCESS` | boolean | `false` | Send an email on success (reuses the SMTP config above) | ❌ No |
| `BACKUP_NOTIFY_ON_FAILURE` | boolean | `true` | Send an email on failure | ❌ No |
| `BACKUP_NOTIFICATION_EMAIL` | string | `""` | Recipient of backup alerts | ❌ No (required if notify is enabled) |

If `BACKUP_ENABLED=false`, the cron script exits silently (exit code 0)
and the admin interface refuses to create new backups — existing backups
remain viewable/downloadable. Email alerts reuse the SMTP configuration
from the Notifications section above, so they're also subject to
`NOTIFICATIONS_ENABLED`.

---

## 🧹 Automatic Cleanup Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DATA_CLEANUP_ENABLED` | boolean | `false` | **Disabled by default for safety**. Enables automatic data cleanup | ❌ No |
| `DATA_CLEANUP_RETENTION` | string | `"365d"` | Data retention duration. Supported formats: `1y` (1 year), `6m` (6 months), `30d` (30 days), or a plain number of days | ❌ No |
| `DATA_CLEANUP_RETENTION_DAYS` | integer | `365` | Retention duration in days (alternative to DATA_CLEANUP_RETENTION) | ❌ No |
| `DATA_CLEANUP_BATCH_SIZE` | integer | `1000` | Batch size for deletion | ❌ No |
| `DATA_CLEANUP_SCHEDULE` | string | `"0 0 * * *"` | Cron schedule for cleanup (default: every day at midnight) | ❌ No |

**Cron schedule examples:**
```bash
# Every day at midnight
DATA_CLEANUP_SCHEDULE="0 0 * * *"

# Every Monday at 2 AM
DATA_CLEANUP_SCHEDULE="0 2 * * 1"

# The 1st of every month at midnight
DATA_CLEANUP_SCHEDULE="0 0 1 * *"
```

---

## 📈 Monitoring Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `PROMETHEUS_ENABLED` | boolean | `false` | Enables the `app/utils/prometheus_metrics.py` blueprint (`/metrics` endpoint in Prometheus format). Disabled by default | ❌ No |

> Liveness/readiness for Kubernetes: `/health` and `/ready` are always
> active (`app/utils/health.py`, registered unconditionally), regardless
> of `PROMETHEUS_ENABLED`.

### Removed variables

**Cache** (`CACHE_TYPE`, `CACHE_DEFAULT_TIMEOUT`, `CACHE_REDIS_URL`,
`CACHE_ENABLED`), **Pagination**, **Lazy Loading**, **Query
Optimization**, and **Performance Monitoring** (`PAGINATION_*`,
`LAZY_LOAD*`, `QUERY_OPTIMIZATION_*`, `PERFORMANCE_MONITORING_ENABLED`,
`SLOW_QUERY_THRESHOLD`, etc.) are not read anywhere in the code.
Setting them in `.env` today has **no effect**.

---

## 🎯 Configuration by Environment

`create_app()` (`app/__init__.py`) loads a single real configuration
class, `app.config.base.Config`, regardless of `FLASK_ENV` — this
variable is only used by `docker/entrypoint.sh` to choose between
Gunicorn (`FLASK_ENV=production`) and the Flask development server
(any other value); it does not select any configuration class. All
settings (`DEBUG`, `LOG_LEVEL`, `SQLALCHEMY_ECHO`, etc.) are therefore
controlled directly via their own respective environment variables (see
table above), not via a predefined development/production profile.

### Testing (`TestingConfig`)
- `TESTING = True`
- `SQLALCHEMY_DATABASE_URI = sqlite:///:memory:`
- `WTF_CSRF_ENABLED = False`
- `LOG_LEVEL = DEBUG`
- `DEBUG_ERRORS = True`
- `RATE_LIMIT_ENABLED = False`
- `COMPRESS_ENABLED = False`

**Activation:**
```bash
FLASK_ENV=testing
```

---

## 📝 Configuration Examples

### Production configuration with PostgreSQL

```bash
# Base configuration
FLASK_ENV=production
SECRET_KEY=your_random_secret_key_here

# PostgreSQL database
DATABASE_URL=postgresql://kairos_user:secure_password@localhost:5432/kairos_db

# Logging
LOG_LEVEL=WARNING
SYSLOG_ENABLED=true
SYSLOG_ADDRESS=/dev/log

# Security
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
CORS_ENABLED=false
DEBUG_ERRORS=false

# Cache
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0

# Automatic cleanup (optional)
DATA_CLEANUP_ENABLED=true
DATA_CLEANUP_RETENTION=1y
DATA_CLEANUP_SCHEDULE="0 0 * * *"
```

### Development configuration

```bash
FLASK_ENV=development
SECRET_KEY=dev_secret_key

# SQLite database
DATABASE_URL=sqlite:///app.db

# Verbose logging
LOG_LEVEL=DEBUG
SQLALCHEMY_ECHO=true
DEBUG_ERRORS=true

# Disable security for development
SESSION_COOKIE_SECURE=false
CORS_ENABLED=true

# Disable cache in development
CACHE_ENABLED=false
```

### Test configuration

```bash
FLASK_ENV=testing
FLASK_TESTING=true
SECRET_KEY=test_secret_key

# In-memory database
DATABASE_URL=sqlite:///:memory:

# Disable production features
WTF_CSRF_ENABLED=false
RATE_LIMIT_ENABLED=false
COMPRESS_ENABLED=false
CORS_ENABLED=true

# Logging
LOG_LEVEL=DEBUG
DEBUG_ERRORS=true
```

### Configuration with Redis

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TIMEOUT=300
```

---

## ⚠️ Best Practices

### 🔐 Security

1. **SECRET_KEY**: Always use a long, random key in production. Never commit this value to Git.
   ```bash
   # Generate a secure key
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **DEFAULT_ADMIN_PASSWORD**: Always change the admin password after the first login.

3. **Database**: In production, never use SQLite with multiple worker processes. Use PostgreSQL or MySQL.

4. **Sensitive variables**: Never store passwords or secret keys in a `.env` file committed to Git. Use system environment variables or a secrets management service.

5. **HTTPS**: In production, always use HTTPS and enable `SESSION_COOKIE_SECURE=true`.

### 📁 .env file

1. **Creation**: Copy the `.env.example` file to `.env` and edit the values:
   ```bash
   cp .env.example .env
   ```

2. **Git**: Add `.env` to your `.gitignore` file to avoid committing sensitive information.

3. **Production**: In production, it's recommended to set variables directly in the system environment rather than using a `.env` file.

### 🐳 Docker

For Docker environments, you can:

1. **Mount the .env file**:
   ```yaml
   # docker-compose.yml
   services:
     app:
       image: kairos
       env_file:
         - .env
   ```

2. **Pass the variables directly**:
   ```yaml
   # docker-compose.yml
   services:
     app:
       image: kairos
       environment:
         - SECRET_KEY=your_key
         - DATABASE_URL=postgresql://user:pass@db:5432/kairos
   ```

3. **Use Docker secrets** for sensitive information.

### 🔄 Boolean Variables

Boolean variables accept the following values (case-insensitive):
- True: `true`, `True`, `TRUE`, `1`, `yes`, `Yes`, `YES`, `y`, `on`
- False: `false`, `False`, `FALSE`, `0`, `no`, `No`, `NO`, `n`, `off`

### 📊 Data Types

| Type | Format | Example |
|------|--------|---------|
| Boolean | true/false, 1/0, yes/no | `true`, `false`, `1`, `0` |
| Integer | Whole number | `300`, `86400` |
| Float | Decimal number | `0.75`, `1.5` |
| String | Text | `"kairos:"`, `"INFO"` |
| JSON | JSON object or array | `{"key": "value"}`, `[1, 2, 3]` |
| List | Comma-separated values | `"password,secret,token"` |

---

## 📚 References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [python-dotenv Documentation](https://saurabh-kumar.com/python-dotenv/)
- [`app/config/`](../../app/config/) — active configuration, loaded by `create_app()`
- [`.env.example`](../../.env.example) — canonical reference, always up to date

---

*This file documents the environment variables actually read by the application. When in doubt, `.env.example` is authoritative.*
