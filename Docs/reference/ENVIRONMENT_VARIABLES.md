# Environment Variables - Kairos

> Every variable below is verified against the code that actually reads
> it (`app/config/base.py`, `app/config/testing.py`, `run.py`,
> `config_oidc.py`, `app/utils/logging/logger.py`,
> `scripts/backup_config.py`, `scripts/notification_config.py`). When in
> doubt, [`.env.example`](../../.env.example) is authoritative.

---

## 📋 Table of Contents

- [🔐 Flask Configuration](#-flask-configuration)
- [🗄️ Database Configuration](#️-database-configuration)
- [🔒 Session & Login Configuration](#-session--login-configuration)
- [🚦 Rate Limiting](#-rate-limiting)
- [🛡️ HTTP Security (Talisman)](#️-http-security-talisman)
- [📄 Pagination](#-pagination)
- [📝 Logging Configuration](#-logging-configuration)
- [🔒 Authentication Configuration](#-authentication-configuration)
- [📊 Default Data Configuration](#-default-data-configuration)
- [📤 ICS Export Configuration](#-ics-export-configuration)
- [📧 Notification Configuration](#-notification-configuration)
- [💾 Backup Configuration](#-backup-configuration)
- [📈 Monitoring Configuration](#-monitoring-configuration)
- [🎯 Configuration Profiles](#-configuration-profiles)
- [⚠️ Best Practices](#️-best-practices)

---

## 🔐 Flask Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `SECRET_KEY` | string | *(random, regenerated on every restart)* | Secret key for Flask session signing. **Must be set to a fixed, long, random value in production** — without it, every restart invalidates all existing sessions. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` | ✅ Yes (production) |
| `FLASK_HOST` | string | `0.0.0.0` | Interface the dev server (`python run.py`) binds to. Ignored by Gunicorn (Docker) | ❌ No |
| `FLASK_PORT` | integer | `5000` | Port the dev server binds to. Ignored by Gunicorn (Docker) | ❌ No |
| `FLASK_DEBUG` | boolean | `false` | Enables Flask's debug mode. **Never enable in production** — exposes the interactive Werkzeug debugger, a real remote-code-execution surface on any unhandled exception | ❌ No |
| `FLASK_TESTING` | boolean | `false` | Flask's own `TESTING` flag | ❌ No |
| `PUBLIC_BASE_URL` | string | *(empty)* | Public URL of the app behind a reverse proxy (e.g. `https://schedule.example.com`). Used as a fallback for absolute links (ICS export) when the proxy doesn't correctly pass `X-Forwarded-Host` — otherwise these links leak the backend's internal IP/hostname. Leave empty to use `request.host_url`. **A value saved at `/admin/settings` always takes priority over this variable** | ❌ No |

**Example:**
```bash
SECRET_KEY=my_secret_key_generated_with_python_secrets
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
PUBLIC_BASE_URL=https://schedule.example.com
```

---

## 🗄️ Database Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DATABASE_URL` | string | `sqlite:///app.db` | Database URI. Supported: SQLite, PostgreSQL, MySQL/MariaDB | ✅ Yes (production) |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | boolean | `false` | SQLAlchemy's own modification-tracking flag (recommended: `false`, this is Flask-SQLAlchemy's own recommendation) | ❌ No |
| `SQLALCHEMY_ENGINE_OPTIONS` | JSON | `{}` | SQLAlchemy engine options, e.g. `{"pool_pre_ping": true, "pool_recycle": 3600}` — the recommended way to configure connection pooling (pool size, timeouts, recycling) against an external PostgreSQL/MySQL server; there is no separate `DATABASE_POOL_SIZE`-style variable | ❌ No |

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

## 🔒 Session & Login Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `SESSION_COOKIE_SECURE` | boolean | `false` | Sends the session cookie only over HTTPS. Set to `true` in production behind HTTPS | ❌ No |
| `SESSION_COOKIE_HTTPONLY` | boolean | `true` | Blocks JavaScript access to the session cookie | ❌ No |
| `SESSION_COOKIE_SAMESITE` | string | `Lax` | SameSite cookie policy. Possible values: `Lax`, `Strict`, `None` | ❌ No |
| `PERMANENT_SESSION_LIFETIME_DAYS` | integer | `30` | Session lifetime in days | ❌ No |
| `LOGIN_DISABLED` | boolean | `false` | **DANGER**: completely disables authentication. Never enable in production | ❌ No |
| `REMEMBER_COOKIE_DURATION` | integer | `86400` | Duration of the "remember me" cookie in seconds (default: 1 day) | ❌ No |
| `SESSION_PROTECTION` | string | `strong` | Flask-Login session protection level. Possible values: `none`, `basic`, `strong` | ❌ No |

---

## 🚦 Rate Limiting

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `RATE_LIMIT_ENABLED` | boolean | `true` | Enables Flask-Limiter | ❌ No |
| `RATE_LIMIT_DEFAULT` | string | `"200 per day, 50 per hour"` | Default limits, Flask-Limiter format | ❌ No |

---

## 🛡️ HTTP Security (Talisman)

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `TALISMAN_FORCE_HTTPS` | boolean | `false` | Redirects every request to HTTPS. **Only enable behind a reverse proxy that terminates TLS** — otherwise it loops on a redirect that serves no purpose | ❌ No |
| `TALISMAN_STRICT_TRANSPORT_SECURITY` | boolean | `false` | Sends the `Strict-Transport-Security` header | ❌ No |

CORS (`flask-cors`) and Gzip/Brotli response compression (`flask-compress`)
are both always active with their library defaults — there is no
`CORS_ENABLED`/`COMPRESS_ENABLED` variable, nothing to configure.

---

## 📄 Pagination

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `ITEMS_PER_PAGE` | integer | `20` | Default page size for paginated lists | ❌ No |
| `MAX_PER_PAGE` | integer | `100` | Maximum page size a user/API call can request | ❌ No |

Both are only the fallback used when no `Setting` row exists — an admin
can override them at runtime from `/admin/settings` without a restart.

---

## 📝 Logging Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `LOG_LEVEL` | string | `INFO` | Main log level. Possible values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | ❌ No |
| `LOG_FORMAT` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Log line format (Python `logging` format string) | ❌ No |
| `LOG_FILE` | string | *(none)* | Path to an optional additional log file, on top of the `app.log`/`error.log`/`debug.log`/`http_errors.log`/`audit.log` files always created under `logs/` (fixed directory, not configurable) | ❌ No |
| `LOG_MAX_BYTES` | integer | `10485760` (10 MB) | Maximum size of each log file before rotation (`RotatingFileHandler`, applies to every file under `logs/`, including `audit.log`) | ❌ No |
| `LOG_BACKUP_COUNT` | integer | `5` | Number of backup files kept after rotation (`app.log.1`, `app.log.2`, ...) | ❌ No |

Sensitive-data filtering (masking `password=`/`token=`/`api_key=` in log
messages, `SensitiveDataFilter`) is always active and cannot be disabled.
`audit.log` is written to by `AuditService.log()`, alongside a database
copy browsable via `/admin/audit-log`.

---

## 🔒 Authentication Configuration

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

## 📊 Default Data Configuration

Read once, when the database is first created (`run.py::create_default_data`).

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `DEFAULT_ADMIN_EMAIL` | string | `admin@kairos.local` | Email of the default admin user | ❌ No |
| `DEFAULT_ADMIN_PASSWORD` | string | *(random, printed to the log on first run — `admin123` in the Docker image specifically)* | **DANGER**: password of the default admin user. **Change this value after the first login!** | ❌ No |
| `DEFAULT_GROUP_NAME` | string | `Defaut` | Name of the default group | ❌ No |
| `DEFAULT_GROUP_IN_SCHEDULE` | boolean | `true` | The default group is part of the schedule | ❌ No |
| `DEFAULT_GROUP_IN_ONCALL` | boolean | `true` | The default group is part of the on-call rotation | ❌ No |

The default shift types (`07h-15h`/`09h-17h`/`13h-21h`) are a fixed list
in `run.py`, not configurable via an environment variable — edit them
after first run from `/admin/shift-types` instead.

---

## 📤 ICS Export Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `ICS_TOKEN_EXPIRY_DAYS` | integer | `365` | Intended validity duration of the ICS subscription token, in days. **Not currently enforced anywhere** — documented here because the setting exists and is admin-editable at `/admin/settings`, but no code path actually checks or expires a token based on it yet | ❌ No |

The ICS subscription URLs shown to the user (`/profile/ics-token` page)
use `PUBLIC_BASE_URL` if set (see [🔐 Flask Configuration](#-flask-configuration)), otherwise
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
anything (exit code 0). This same flag also gates the in-app
"Apprise" external-notification relay for weekly reminders (Slack/
Discord/Telegram/webhook), which reuses this SMTP-adjacent config only
for the enable/disable check, not for its own delivery.

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

## 📈 Monitoring Configuration

| Variable | Type | Default | Description | Required |
|----------|------|--------|-------------|-------------|
| `PROMETHEUS_ENABLED` | boolean | `false` | Enables the `app/utils/prometheus_metrics.py` blueprint (`/metrics` endpoint in Prometheus format) | ❌ No |

> Liveness/readiness for Kubernetes: `/health` and `/ready` are always
> active (`app/utils/health.py`, registered unconditionally), regardless
> of `PROMETHEUS_ENABLED`.

There is no cache, pagination-tuning (beyond the two variables above),
lazy-loading, query-optimization, or performance-monitoring system in
this application, and therefore no corresponding environment variable —
none of `CACHE_*`, `LAZY_LOAD*`, `QUERY_OPTIMIZATION_*`,
`PERFORMANCE_MONITORING_*`, `SLOW_QUERY_THRESHOLD` is read anywhere.
There is also no automatic data-retention/cleanup system (no
`DATA_CLEANUP_*` variable) — the only retention/purge mechanisms are the
admin-configurable ones already covered above (backups, audit log).

---

## 🎯 Configuration Profiles

`create_app()` (`app/__init__.py`) always loads the same configuration
class, `app.config.base.Config` — there is no separate development/
production profile selected by `FLASK_ENV`. `docker/entrypoint.sh` reads
`FLASK_ENV` only to decide whether to start Gunicorn
(`FLASK_ENV=production`) or the Flask dev server (any other value); it
never selects a different set of defaults. Every setting in this
document is controlled directly by its own environment variable
regardless of `FLASK_ENV`.

### Tests (`TestingConfig`)

Used automatically by the test suite (`create_app('app.config.TestingConfig')`),
not selectable via an environment variable:
- `TESTING = True`, `SQLALCHEMY_DATABASE_URI = sqlite:///:memory:`
- `WTF_CSRF_ENABLED = False`, `RATELIMIT_ENABLED = False`, `TALISMAN` disabled
- `LOG_LEVEL = DEBUG`

---

## 📝 Configuration Examples

### Production with PostgreSQL, behind a TLS-terminating reverse proxy

```bash
SECRET_KEY=your_random_secret_key_here
DATABASE_URL=postgresql://kairos_user:secure_password@localhost:5432/kairos_db

LOG_LEVEL=WARNING

SESSION_COOKIE_SECURE=true
TALISMAN_FORCE_HTTPS=true
TALISMAN_STRICT_TRANSPORT_SECURITY=true
```

### Local development

```bash
SECRET_KEY=dev_secret_key
DATABASE_URL=sqlite:///app.db
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
```

---

## ⚠️ Best Practices

### 🔐 Security

1. **SECRET_KEY**: Always set a fixed, long, random key in production — without it, sessions don't survive a restart. Never commit this value to Git.
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **DEFAULT_ADMIN_PASSWORD**: Always change the admin password after the first login.

3. **Database**: In production, never use SQLite with multiple worker processes. Use PostgreSQL or MySQL/MariaDB.

4. **Sensitive variables**: Never store passwords or secret keys in a `.env` file committed to Git. Use system environment variables or a secrets management service.

5. **HTTPS**: In production behind a TLS-terminating proxy, set both `SESSION_COOKIE_SECURE=true` and `TALISMAN_FORCE_HTTPS=true`.

### 📁 .env file

1. **Creation**: Copy the `.env.example` file to `.env` and edit the values:
   ```bash
   cp .env.example .env
   ```

2. **Git**: Add `.env` to your `.gitignore` file to avoid committing sensitive information.

3. **Production**: it's recommended to set variables directly in the system environment rather than using a `.env` file.

### 🔄 Boolean Variables

Boolean variables accept the following values (case-insensitive):
- True: `true`, `1`, `yes`, `y`, `on`
- False: `false`, `0`, `no`, `n`, `off`

---

## 📚 References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [`app/config/base.py`](../../app/config/base.py) — the actual source of truth
- [`.env.example`](../../.env.example) — canonical reference, always up to date
