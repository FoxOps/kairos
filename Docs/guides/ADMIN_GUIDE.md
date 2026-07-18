# 🛡️ Administrator Guide - Kairos

> **Version**: 1.1.0 | **Last updated**: July 2026
> **Audience**: Kairos administrators only

---

## 📋 Table of Contents

1. [🎯 Administrator Role](#-administrator-role)
2. [🔐 Security Management](#-security-management)
3. [👥 Advanced User Management](#-advanced-user-management)
4. [🏢 Group Architecture](#-group-architecture)
5. [⚙️ Shift Type Configuration](#️-shift-type-configuration)
6. [📊 Dashboard and Statistics](#-dashboard-and-statistics)
7. [⚡ Full Automation](#-full-automation)
8. [🔧 Technical Configuration](#-technical-configuration)
9. [📤 Export and Integrations](#-export-and-integrations)
10. [🎨 Customization](#-customization)
11. [🔄 Maintenance and Backups](#-maintenance-and-backups)
12. [🚨 Error Handling](#-error-handling)

---

## 🎯 Administrator Role

### Responsibilities

As a Kairos administrator, you are responsible for:

- ✅ **User management**: Creation, modification, deletion
- ✅ **Group configuration**: Organization and permissions
- ✅ **Shift settings**: Shift types and business rules
- ✅ **Scheduling**: Shifts, on-call rotations, leave
- ✅ **Automation**: Configuration and supervision
- ✅ **Security**: Access and permission management
- ✅ **Maintenance**: Backups and updates

### Best Practices

1. **Security**: Always change the default password
2. **Backups**: Perform regular database backups
3. **Testing**: Test changes in a development environment
4. **Documentation**: Document specific configurations
5. **Audit**: Regularly review logs and activity

---

## 🔐 Security Management

### Account Security

#### Default password

**⚠️ CRITICAL**: The default administrator account has the following credentials:
- Email: `DEFAULT_ADMIN_EMAIL` (`.env`), defaults to `admin@kairos.local`
- Password: `DEFAULT_ADMIN_PASSWORD` (`.env`), defaults to `admin123`

**Immediate action**: Change this password as soon as you log in for the first time.
In production, set `DEFAULT_ADMIN_PASSWORD` to a strong value before the very first
startup rather than relying on a post-installation change.

#### Password policy

Recommendations:
- Minimum 12 characters
- Mix of uppercase, lowercase, digits, and symbols
- No dictionary words
- Unique for each user

#### Resetting passwords

To reset a user's password:

1. Go to **Admin** > **Users**
2. Click **Edit** for the relevant user
3. Enter a new password in the **Password** field
4. **Save**

> 💡 **Tip**: You can leave the field blank to keep the current password.

### Permission Management

#### Roles

| Role | Access |
|------|--------|
| **Administrator** | Full access to all features |
| **User** | Limited access to their own schedule and leave |

#### Permissions per group

| Permission | Description |
|------------|-------------|
| **Participates in scheduling** | Members can be assigned shifts |
| **Participates in on-call** | Members can be placed on on-call rotation |

### Application Security

#### Sensitive environment variables

| Variable | Sensitivity | Recommendation |
|----------|-------------|----------------|
| `SECRET_KEY` | ⭐⭐⭐⭐⭐ CRITICAL | Generate a random 32-byte key |
| `DATABASE_URL` | ⭐⭐⭐⭐ High | Use secure DB credentials |
| `LOGIN_DISABLED` | ⭐⭐⭐ Medium | NEVER enable in production |

#### Generate a secure secret key

```bash
# Method 1: Python
python -c "import secrets; print(secrets.token_hex(32))"

# Method 2: OpenSSL
openssl rand -hex 32
```

#### Disable authentication (DEVELOPMENT ONLY)

In `.env`:
```bash
LOGIN_DISABLED=true
```

> ⚠️ **DANGER**: Never use this option in production!

#### CSRF Protection

Active across the entire application (`Flask-WTF` `CSRFProtect`) —
nothing to configure on the admin side, but good to know if
you script calls to the application (bulk import, third-party integration):
any POST/PUT/PATCH/DELETE request without a valid CSRF token is rejected
with `400 Bad Request`. See [`api/API.md`](../api/API.md#authentification)
for the procedure to follow from a script.

#### HTTP security headers (Talisman)

`Flask-Talisman` (X-Content-Type-Options, X-Frame-Options, etc.) is only
enabled if `TALISMAN_FORCE_HTTPS=true` in `.env` — relevant only behind a
TLS reverse proxy (see
[`deployment/DEPLOYMENT_GUIDE.md`](../deployment/DEPLOYMENT_GUIDE.md)).
Left disabled by default so as not to break plain HTTP access in
development.

### SSO/OIDC Configuration

Kairos supports authentication via an OIDC provider (Keycloak, Okta,
Auth0, or any standard OpenID Connect provider), in addition to or
instead of password authentication.

#### Enable OIDC

In `.env`:

```bash
OIDC_ENABLED=true
OIDC_ISSUER=https://your-provider.com/realms/your-realm
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:5000/oidc/callback
```

On the OIDC provider side, register `OIDC_REDIRECT_URI` as an authorized
callback URL for the client.

#### Disable password authentication

To force all users through SSO (hides the email/password form, `/login`
redirects straight to `/oidc/login`):

```bash
OIDC_DISABLE_BASIC_AUTH=true
```

> ⚠️ Make sure OIDC login works before enabling this option — without a
> fallback basic authentication, an OIDC configuration issue would lock
> out all access, including your own.

#### Full logout (RP-initiated logout)

Without additional configuration, `/logout` only ends the local session:
the session on the OIDC provider's side remains active, so the next
visit to `/login` silently re-authenticates via SSO. For a full logout,
register a post-logout redirect URL on the provider side (e.g.
`PostLogoutRedirectUris` on Keycloak) and then:

```bash
OIDC_POST_LOGOUT_REDIRECT_URI=http://localhost:5000
```

#### Mapping token claims

If your provider's claim names differ from the standard names:

```bash
OIDC_EMAIL_CLAIM=email
OIDC_NAME_CLAIM=name
OIDC_USERNAME_CLAIM=preferred_username
OIDC_GROUPS_CLAIM=          # optional, syncs local groups
OIDC_ROLES_CLAIM=           # optional, syncs is_admin
```

#### Docker deployment: internal vs. external issuer

If the OIDC provider and the application both run in Docker (e.g.
Keycloak on the same network as the Kairos container), the URL reachable
by the container (`http://keycloak:8080/realms/...`) often differs from
the URL reachable by the user's browser
(`https://auth.example.com/realms/...`). In this case, set
`OIDC_INTERNAL_ISSUER` to the URL reachable by the container;
`OIDC_ISSUER` remains the public URL used for browser redirects
(authorization/logout endpoints).

Full list of OIDC variables:
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).
Login flow details:
[`architecture/SEQUENCE_DIAGRAMS.md`](../architecture/SEQUENCE_DIAGRAMS.md#connexion-oidcsso).

### Audit and Logging

#### Change history (audit trail)

Since version 0.9.0, `/admin/audit-log` (linked from the admin
dashboard) lists every significant business action: who, what, when, on
which resource. Coverage: CRUD on users/groups/shifts/on-call/leave/shift
types, the entire shift-swap lifecycle (request/cancellation/approval/
rejection/reverting an approved swap/purge), admin setting changes, and
login events (success, failure, logout, registration, password change).

The page allows filtering by actor, action domain (`shift`, `oncall`,
`leave`, `swap`, `user`, `group`, `shift_type`, `setting`, `auth`,
`profile`) and date range. Every entry is also written to
`logs/audit.log` (dual write, defense in depth: the database entry
powers this filterable page, the file copy survives even if the
database is unavailable).

**Purge**: the "Purge according to retention" button deletes entries
older than the duration configured in **Settings → Audit trail**
(`/admin/settings`). As long as no value has been saved there, no purge
is possible — the history is kept indefinitely by default, unlike backup
retention, which has a numeric fallback.

#### Enable advanced logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

#### Log files

`logs/app.log`, `logs/error.log`, `logs/debug.log`, `logs/http_errors.log`,
and `logs/audit.log` are created automatically on startup, with rotation
(`LOG_MAX_BYTES` / `LOG_BACKUP_COUNT`, see
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-du-logging)).
`LOG_FILE` additionally lets you redirect the root output to an extra
file:

```bash
LOG_FILE=kairos.log
```

---

## 👥 Advanced User Management

### User Import/Export

> 📌 **Upcoming feature**: CSV import/export for users will be available in a future version.

### Bulk Management

#### Delete all users in a group

1. Go to **Admin** > **Users**
2. Filter by group
3. For each user, click **Delete**

> ⚠️ **Warning**: You must first delete the associated shifts, on-call periods, and leave.

#### Change the group of multiple users

1. Go to **Admin** > **Users**
2. Click **Edit** for each user
3. Change the group
4. **Save**

### System Users

| User | Role | Description |
|-------------|------|-------------|
| `admin@kairos.local` | Administrator | Default account, should be renamed |

### Best Practices

1. **Naming**: Use professional emails
2. **Groups**: Organize users by team/department
3. **Permissions**: Grant only the necessary permissions
4. **Audit**: Regularly review the user list

---

## 🏢 Group Architecture

### Grouping Strategy

#### Example 1: By Department

```
Group: Development
├── Participates in scheduling: ✅
├── Participates in on-call: ✅
└── Users: Jean, Marie, Pierre

Group: Support
├── Participates in scheduling: ✅
├── Participates in on-call: ✅
└── Users: Sophie, Thomas

Group: Management
├── Participates in scheduling: ❌
├── Participates in on-call: ❌
└── Users: Mr. Dupont
```

#### Example 2: By Contract Type

```
Group: Full-Time
├── Participates in scheduling: ✅
├── Participates in on-call: ✅
└── Users: ...

Group: Part-Time
├── Participates in scheduling: ✅
├── Participates in on-call: ❌
└── Users: ...

Group: Interns
├── Participates in scheduling: ✅
├── Participates in on-call: ❌
└── Users: ...
```

### Moving Users

To move a user to another group:

1. Check that the new group has the right permissions
2. Go to **Admin** > **Users**
3. Click **Edit** for the user
4. Change the group
5. **Save**

> ⚠️ **Warning**: If the new group doesn't have the permission to participate in scheduling, the user will lose their shifts.

---

## ⚙️ Shift Type Configuration

### Default Shift Types

| Name | Label | Start Time | End Time | Duration |
|-----|---------|--------------|-----------|-------|
| `morning` | Morning | 8:00 AM | 12:00 PM | 4h |
| `afternoon` | Afternoon | 12:00 PM | 6:00 PM | 6h |
| `evening` | Evening | 6:00 PM | 10:00 PM | 4h |

### Creating a Custom Shift Type

#### Example 1: Night Shift

1. **Admin** > **Shift Types** > **Add**
2. Name: `night`
3. Label: `Night`
4. Start time: `22`
5. End time: `6`
6. **Save**

> ⚠️ **Warning**: A shift that crosses midnight must have an end time > start time (e.g., 22 to 6 = 22 to 30 for 8h).

#### Example 2: Short Shift

1. **Admin** > **Shift Types** > **Add**
2. Name: `short_morning`
3. Label: `Short Morning`
4. Start time: `9`
5. End time: `12`
6. **Save**

### Editing a Shift Type

1. **Admin** > **Shift Types**
2. Click **Edit** for the shift type
3. Modify the necessary fields
4. **Save**

> ⚠️ **Warning**: Editing a shift type affects all existing shifts that use it.

### Deleting a Shift Type

1. **Admin** > **Shift Types**
2. Click **Delete** for the shift type
3. Confirm

> ⚠️ **Warning**: You cannot delete a shift type that is used by existing shifts.

### Best Practices

1. **Naming**: Use short, descriptive names (no spaces)
2. **Labels**: Use clear labels for the interface
3. **Overlap**: Avoid overlapping time slots
4. **Coverage**: Make sure all required time slots are covered

---

## 📊 Dashboard and Statistics

### Overview

The administrator dashboard displays:

- **Users**: Total number of users
- **Groups**: Total number of groups
- **Shifts**: Total number of scheduled shifts
- **On-call**: Total number of on-call periods
- **Leave**: Total number of leave requests

### Advanced Statistics

> 📌 **Coming soon**: Detailed charts and reports will be added.

### Quick Access

From the dashboard, you can access:
- **Users**: Full user management
- **Groups**: Group configuration
- **Shift Types**: Shift type settings
- **Automation**: Automation configuration

---

## ⚡ Full Automation

### Automation Architecture

Kairos offers several levels of automation:

```
┌─────────────────────────────────────────────────┐
│                   AUTOMATION                      │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐          │
│  │   On-Call     │    │    Shifts     │          │
│  │               │    │              │          │
│  └──────────────┘    └──────────────┘          │
│         │                   │                 │
│         ▼                   ▼                 │
│  ┌─────────────────────────────────────────┐  │
│  │             Full Generation               │  │
│  │   (On-call + Shifts in a single pass)     │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Configuring Automatic On-Call

#### Step 1: Define the rotation order

1. Go to **Admin** > **Automation** > **Full generation**
2. For each eligible user:
   - ✅ **Include in rotation**: Check to include
   - **Position**: Set the order (1 = first)
3. Click **Save order**

Example rotation order:
```
Position 1: Jean Dupont
Position 2: Marie Martin
Position 3: Pierre Durand
Position 4: Sophie Leroy
```

#### Step 2: Configure the period

1. **Start date**: First Friday of the period
2. **End date**: Last day of the period
3. Click **Simulate** to preview

#### Step 3: Generate

1. Check the simulation result
2. Click **Generate** to create the on-call periods

### Configuring Automatic Shifts

#### Step 1: Define daily requirements

1. Go to **Admin** > **Automation** > **Shifts**
2. For each day (Monday to Friday):
   - **Morning**: Number of people needed
   - **Afternoon**: Number of people needed
   - **Evening**: Number of people needed

Example configuration:
```
Monday:
  - Morning: 2 people
  - Afternoon: 2 people
  - Evening: 1 person

Tuesday to Friday: Same configuration
```

#### Step 2: Configure the period

1. **Start date**: First day of the period
2. **End date**: Last day of the period
3. Click **Simulate** to preview

#### Step 3: Generate

1. Check the simulation result
2. Click **Generate** to create the shifts

### Full Generation (On-Call + Shifts)

To generate everything in a single operation:

1. Go to **Admin** > **Automation** > **Full generation**
2. Configure the on-call rotation order
3. Select the period
4. Click **Simulate**
5. Check that everything is correct
6. Click **Generate**

> 💡 **Tip**: Full generation takes on-call periods into account to avoid conflicts with shifts.

### Refreshing Shifts

If you have manually modified on-call periods:

1. Go to **Admin** > **Automation** > **Refresh shifts**
2. Select the period to recalculate
3. Click **Refresh**

> ⚠️ **Warning**: This action will delete all existing shifts for the selected period!

### Business Rules

#### Default rules for on-call

```python
{
    "rotation_order": [1, 2, 3, 4],  # User order
    "duration_days": 7,              # Duration in days
    "start_hour": 21,               # Start time (21h = 9 PM)
    "end_hour": 7,                 # End time (7h = 7 AM)
    "start_day": 4                 # Day of the week (4 = Friday)
}
```

#### Default rules for shifts

```python
{
    "daily_requirements": {
        "monday": {"morning": 2, "afternoon": 2, "evening": 1},
        "tuesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "wednesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "thursday": {"morning": 2, "afternoon": 2, "evening": 1},
        "friday": {"morning": 2, "afternoon": 2, "evening": 1}
    },
    "weekend_excluded": True
}
```

### Customizing Rules

You can customize the rules in the configuration file or via the automation interface.

---

## 🔧 Technical Configuration

### Settings configurable via the UI (`/admin/settings`)

Since versions 0.7.10 through 0.9.0, a growing set of settings —
previously environment variables only — is editable at runtime from
`/admin/settings` without a redeploy: default timezone, default language
(French/English), default date/time formats, public URL, pagination
(items per page), email notifications (global toggle), backup retention,
ICS token expiry duration, and audit trail retention. Each setting
follows the same rule: a value saved in the database always wins; as
long as no value has been saved, the application falls back live to the
corresponding environment variable/default value (so a deployment driven
solely by environment variables keeps behaving identically as long as no
one goes through this page). Each user can also individually override
their own timezone, language, and date/time formats from
`/profile/settings` (otherwise the organization's default value
applies).

Every change made on this page (like any business action) is recorded in
the change history — see "Audit and Logging" above.

### Configuration File

The active configuration lives in `app/config/` (`base.py`,
`testing.py`), read from environment variables (`.env`). `create_app()`
always loads `app.config.base.Config` in both production and development
(`FLASK_ENV` only selects between Gunicorn and the Flask development
server, not a configuration class); `TestingConfig` is only used by the
test suite.

```python
# app/config/base.py (excerpt)
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGIN_DISABLED = get_bool_from_env('LOGIN_DISABLED', False)
```

### Environment Variables

| Variable | Description | Default value | Recommendation |
|----------|-------------|------------------|----------------|
| `SECRET_KEY` | Secret key for security | Random if absent | ⭐⭐⭐⭐⭐ Generate a strong key and set it explicitly |
| `DATABASE_URL` | Database URI | `sqlite:///app.db` | Use PostgreSQL or MariaDB in production |
| `LOGIN_DISABLED` | Disables authentication | `false` | ❌ NEVER enable in production |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` for development |

Full list: [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

### Database Configuration

All variants are configured via `DATABASE_URL` in `.env` — no Python
file to edit.

#### SQLite (default)

```bash
DATABASE_URL=sqlite:///app.db
```

- **Advantages**: Simple, no server required
- **Disadvantages**: Not suited for production, no concurrency

#### PostgreSQL (recommended for production)

```bash
DATABASE_URL=postgresql://user:password@localhost/kairos
```

The driver (`psycopg[binary]`, psycopg 3) is already included by default
in `requirements.txt` — no extra installation needed. See
[`deployment/DEPLOYMENT_ADVANCED.md`](../deployment/DEPLOYMENT_ADVANCED.md)
for a complete setup.

- **Advantages**: Robust, scalable, concurrency support
- **Disadvantages**: Requires a PostgreSQL server

#### MariaDB / MySQL

```bash
DATABASE_URL=mariadb://user:password@localhost:3306/kairos
# or: DATABASE_URL=mysql://user:password@localhost:3306/kairos
```

Already supported (SQLAlchemy handles backend selection via the URI).
The `PyMySQL` driver — 100% pure Python, no system library required — is
already included by default in `requirements.txt`, no extra installation
needed. This is what lets you connect the app to an **external**
MySQL/MariaDB server without installing anything MySQL-related, either
on the host machine or in the Docker image. See
[`deployment/DEPLOYMENT_GUIDE.md`](../deployment/DEPLOYMENT_GUIDE.md#73-mysqlmariadb)
section 7.3 for a complete example.

### Server Configuration

#### Development (built-in Flask server)

```bash
python run.py
```

- **Port**: 5000
- **Host**: localhost
- **Debug**: Enabled

#### Production (Gunicorn + Nginx)

1. Install Gunicorn:
   ```bash
   pip install gunicorn
   ```

2. Create a `wsgi.py` file:
   ```python
   from app import app
   
   if __name__ == "__main__":
       app.run()
   ```

3. Run Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

4. Configure Nginx as a reverse proxy

---

## 📤 Export and Integrations

### ICS Export

#### Configuration

ICS export is available via the URL:
```
/export/shifts?scope={scope}&token={token}
```

**Parameters**:
- `scope`: `my` (personal schedule) or `all` (all schedules)
- `token`: The user's ICS token

#### Generating an ICS token

Token generation is **self-service** — each user generates their own
from their own profile (**Profile > ICS Token > Generate a new token**,
route `POST /profile/ics-token`). There is no admin workflow to generate
another user's token from the **Admin > Users** screen.

#### Integration with Google Calendar

1. In Google Calendar: **Settings** > **Add calendar** > **From URL**
2. Paste the URL: `http://your-server/export/shifts?scope=my&token=YOUR_TOKEN`
3. **Add calendar**

#### Integration with Outlook

1. In Outlook: **File** > **Account Settings** > **Account Settings**
2. **New** > **Internet Calendar**
3. Paste the URL
4. **Next**

### Advanced Export

Kairos offers three separate export endpoints:

#### Available endpoints

| Endpoint | Description | Parameters |
|----------|-------------|------------|
| `/export/shifts` | Exports shifts (work schedules) | `scope`, `token` |
| `/export/oncall` | Exports on-call periods | `scope`, `token` |
| `/export/leaves` | Exports leave | `scope`, `token` |

#### Common parameters

| Parameter | Possible values | Description |
|-----------|-------------------|-------------|
| `scope` | `my`, `all` | `my` = the user's own data, `all` = all data (admin only) |
| `token` | ICS token | Authentication token generated in the profile |

#### URL examples

```bash
# Personal export
/export/shifts?scope=my&token=YOUR_TOKEN
/export/oncall?scope=my&token=YOUR_TOKEN
/export/leaves?scope=my&token=YOUR_TOKEN

# Full export (admin)
/export/shifts?scope=all&token=ADMIN_TOKEN
/export/oncall?scope=all&token=ADMIN_TOKEN
/export/leaves?scope=all&token=ADMIN_TOKEN
```

### REST API (Coming soon)

> 📌 **Planned feature**: A public REST API will be available in version 0.8.

### Webhooks (Coming soon)

> 📌 **Planned feature**: Webhooks will be available in version 0.8.

---

## 🎨 Customization

### Interface Customization

#### Logo and Favicon

Replace the files in `app/templates/`:
- `favicon.ico`: The application's favicon
- (Coming soon): Logo in the header

#### Custom CSS

1. Create a file `app/static/css/custom.css`
2. Add your custom styles
3. The file will be loaded automatically

### Email Notifications

Kairos sends weekly reminder emails:
- A summary of the upcoming week's shifts, sent on **Sunday** (24h
  before Monday's shifts start).
- An on-call reminder, sent on **Thursday** (24h before Friday's 9 PM
  on-call period starts).

These emails are sent by two standalone scripts
(`scripts/send_shift_notifications.py` and
`scripts/send_oncall_notifications.py`), triggered by an external cron
job — **not** by the Flask application itself. Only one email per week
and per user is sent (anti-duplicate safeguard in the database).

#### Enabling notifications

1. Configure the SMTP variables in `.env` (see
   [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)):
   `NOTIFICATIONS_ENABLED=true`, `NOTIFICATION_FROM_EMAIL`, `SMTP_HOST`,
   `SMTP_PORT`, `SMTP_USERNAME`/`SMTP_PASSWORD` if your SMTP server
   requires authentication.
2. Add the two crontab entries (see `scripts/cron_example.sh` for a
   complete example):

```bash
# Sunday 9am: weekly shift reminder
0 9 * * 0 cd /path/to/kairos && venv/bin/python scripts/send_shift_notifications.py >> /var/log/kairos-notifications.log 2>&1

# Thursday 9am: Friday on-call reminder
0 9 * * 4 cd /path/to/kairos && venv/bin/python scripts/send_oncall_notifications.py >> /var/log/kairos-notifications.log 2>&1
```

If `NOTIFICATIONS_ENABLED` is not enabled (or if the SMTP configuration
is incomplete), the scripts terminate silently without sending anything
— no need to disable the cron job to turn off notifications, a single
environment variable is enough.

#### Customizing email content

The templates (HTML + text) are in `app/templates/emails/`:
`shift_weekly.html`/`.txt` and `oncall_weekly.html`/`.txt`. These are
standard Jinja2 templates — edit them directly to change the content,
formatting, or branding (logo, colors).

### Customizing Business Rules

You can customize business rules in:
- `app/utils/automation/`: automation rules
  (`advanced_shift_automation.py`, `oncall_automation.py`)
- `app/utils/helpers/common_helpers.py`: validation functions
  (`can_add_shift`, `can_add_leave`, `can_add_oncall`)
- `app/auth/decorators.py`: route guard decorators
  (`@admin_required`, `@user_owns_resource`, etc.)

See [`architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
for the full structure.

---

## 🔄 Maintenance and Backups

### Database Backup

The built-in backup system (`scripts/backup_database.py`) handles local
and/or S3/S3-compatible backups, compression, integrity verification,
retention, and email alerts — see the [Backup Guide](BACKUP_GUIDE.md)
for the full detail. Entirely driven by environment variables
(`BACKUP_ENABLED` first and foremost, see
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-sauvegardes))
— disabled by default.

Two ways to trigger a backup:

- **Admin interface** (`/admin/backups`): active configuration, list of
  local/S3 backups, on-demand creation, cleanup, download. Manual
  creation is refused if `BACKUP_ENABLED=false`.
- **Cron** (recommended for automation): see [Automation with
  Cron](BACKUP_GUIDE.md#-automatisation-avec-cron), or, in Docker,
  `BACKUP_ENABLED=true` is enough (same container as the application,
  schedule in `docker/crontabs/appuser`, see
  [`deployment/docker.md`](../deployment/docker.md)).

For a one-off manual backup without going through this system
(troubleshooting, before a risky operation):

```bash
# SQLite
cp instance/app.db instance/app.db.backup-$(date +%Y%m%d)

# PostgreSQL
pg_dump kairos > kairos-backup-$(date +%Y%m%d).sql
```

### Updating the Application

1. Back up the database
2. Back up your `.env` file (contains `SECRET_KEY` and other secrets,
   not version-controlled)
3. Update the code:
   ```bash
   git pull origin main
   ```
4. Install the new dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Restart the application

### Cleanup

#### Removing obsolete data

1. **Past shifts**: Delete old shifts to improve performance
2. **Past on-call periods**: Delete finished on-call periods
3. **Past leave**: Delete finished leave

#### Database Optimization

For SQLite:
```bash
# Reorganize the database
sqlite3 instance/app.db "VACUUM;"
```

For PostgreSQL:
```bash
# Reorganize and analyze
psql kairos -c "VACUUM ANALYZE;"
```

---

## 🚨 Error Handling

### Common Errors and Solutions

#### Error: "Cannot delete... data is associated"

**Cause**: You are trying to delete an item that has dependencies.

**Solution**: First delete the associated data (shifts, on-call periods, leave).

#### Error: "Invalid date format"

**Cause**: The date is not in `YYYY-MM-DD` format.

**Solution**: Use the format `2026-06-15`.

#### Error: "On-call must start on a Friday"

**Cause**: You are trying to create an on-call period that doesn't start on a Friday.

**Solution**: Select a Friday as the start date.

#### Error: "Incorrect email or password"

**Cause**: Invalid credentials.

**Solution**: Check your email and password. Use password reset if needed.

#### Error 500: Server error

**Cause**: Internal server issue.

**Solution**:
1. Check the application logs
2. Check that the database is accessible
3. Restart the application
4. Contact support if the problem persists

### Logs and Troubleshooting

#### Enabling debug mode

In `run.py`:
```python
app.run(debug=True)
```

#### Viewing logs

```bash
# Run the application with logs
python run.py
```

#### Database Issues

**Symptom**: The application won't start, connection errors.

**Solutions**:
1. Check that the `instance/app.db` file exists
2. Check the permissions: `chmod 666 instance/app.db`
3. Check that SQLite is installed
4. For PostgreSQL, check that the server is running

---

## 📚 Resources for Administrators

### Documentation

- [📖 Complete User Guide](USER_GUIDE.md)
- [🚀 Quick Start Guide](QUICK_START.md)
- [❓ FAQ](FAQ.md)
- [🏗️ Technical Architecture](../architecture/ARCHITECTURE.md)
- [🚀 Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [🗺️ Roadmap](../../ROADMAP.md)
- [📋 Technical README](../../README.md)

### Tools

- **SQLite Browser**: [https://sqlitebrowser.org/](https://sqlitebrowser.org/)
- **PostgreSQL Admin**: pgAdmin, DBeaver
- **Monitoring**: Prometheus, Grafana (for production)

### Communities

- **GitHub Issues**: [https://github.com/FoxOps/leviia-schedule/issues](https://github.com/FoxOps/leviia-schedule/issues)
- **GitHub Discussions**: [https://github.com/FoxOps/leviia-schedule/discussions](https://github.com/FoxOps/leviia-schedule/discussions)

---

## 📝 Administrator Checklist

### After Installation

- [ ] Change the default administrator password
- [ ] Configure the necessary groups
- [ ] Add users
- [ ] Configure shift types
- [ ] Test the application
- [ ] Configure automatic backups

### Monthly

- [ ] Check backups
- [ ] Check logs for errors
- [ ] Update the application
- [ ] Check disk space
- [ ] Audit users and permissions

### Quarterly

- [ ] Test backup restoration
- [ ] Optimize the database
- [ ] Review automation rules
- [ ] Update the documentation

---

## 📞 Administrator Support

### Contacting Support

1. **GitHub Issues**: For bugs and feature requests
2. **GitHub Discussions**: For general questions
3. **Documentation**: Refer to this guide and other documents

### Information to Provide

When reporting an issue, provide:
- Application version
- Database type
- Steps to reproduce
- Error logs
- Screenshot (if applicable)

---

> **⚠️ Reminder**: As an administrator, you are responsible for the security and proper use of the application.

---

*© 2026 FoxOps - All rights reserved under the CeCILL v2.1 license*
