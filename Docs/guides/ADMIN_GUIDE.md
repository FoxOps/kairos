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

This bootstrap password is set programmatically and bypasses the password
policy below (it's not typed through the change-password form), but the
account is created with a forced-change flag - **you cannot use the app
past login without setting a new, policy-compliant password first**, no
manual reminder needed. In production, set `DEFAULT_ADMIN_PASSWORD` to a
strong value before the very first startup anyway, rather than relying on
this forced first-login change.

#### Password policy

**Enforced** (not just a recommendation) for every password created or
changed through the app - based on the [ANSSI-PG-078
guide](https://cyber.gouv.fr/), section 4 ("Facteur de connaissance"):

- Minimum 12 characters (no maximum beyond a 128-character DoS guard)
- At least 3 of the 4 character classes: lowercase, uppercase, digits,
  symbols
- Rejected if it matches a common/weak password list, or contains the
  account's own name/email
- **Every account must change its password on first login** - enforced
  app-wide, not just recommended (a banner blocks every other page until
  done)

**Applies to local (basic-auth) accounts only.** When OIDC/SSO is enabled,
password management is entirely delegated to the upstream identity
provider - OIDC users have no local password at all, and none of the
above applies to them.

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
with `400 Bad Request`. See [`api/API.md`](../api/API.md#authentication)
for the procedure to follow from a script.

#### HTTP security headers (Talisman)

`Flask-Talisman` is **always active** outside the test config (`app/__init__.py`)
— it applies the CSP, `X-Content-Type-Options`, `X-Frame-Options`, etc. on
every request regardless of `TALISMAN_FORCE_HTTPS`. `TALISMAN_FORCE_HTTPS`
(`.env`, default `false`) only controls the HTTP→HTTPS redirect and HSTS
header, not the rest of the headers — an earlier version of this app gated
every Talisman header behind `TALISMAN_FORCE_HTTPS`, which left a
TLS-terminated-upstream deployment with `TALISMAN_FORCE_HTTPS=false`
entirely without security headers; this was fixed, so the headers are now
unconditional. Set `TALISMAN_FORCE_HTTPS=false` for plain-HTTP setups
(e.g. `python run.py` on `http://localhost:5000`, or Docker without a
TLS-terminating reverse proxy yet) to avoid a redirect loop; set it to
`true` once a TLS reverse proxy is actually in front of the app (see
[`deployment/DEPLOYMENT_GUIDE.md`](../deployment/DEPLOYMENT_GUIDE.md)).

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
[`architecture/SEQUENCE_DIAGRAMS.md`](../architecture/SEQUENCE_DIAGRAMS.md#oidcsso-login).

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
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-logging-configuration)).
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
| `morning` | `07h-15h` | 7:00 AM | 3:00 PM | 8h |
| `afternoon` | `09h-17h` | 9:00 AM | 5:00 PM | 8h |
| `evening` | `13h-21h` | 1:00 PM | 9:00 PM | 8h |

### Creating a Custom Shift Type

> ⚠️ **Important**: shift types cannot cross midnight. Both the start and
> end hour must be integers between 0 and 23, and the end hour must be
> strictly greater than the start hour (`app/services/shift_type_service.py`) -
> there is no way to encode e.g. a 22h-06h night shift.

#### Example: Short Shift

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
- **Pending swaps**: Number of shift swap requests awaiting admin review

### Advanced Statistics

> 📌 **Coming soon**: Detailed charts and reports will be added.

### Quick Access

From the dashboard, you can access:
- **Users**: Full user management
- **Groups**: Group configuration
- **Schedule**: View/manage shifts
- **Shift Types**: Shift type settings
- **On-Call**: View/manage on-call periods
- **Leave**: View/manage leave periods
- **Swaps**: Review pending shift swap requests
- **Automation**: Automation configuration
- **Backups**: Trigger/download database backups
- **Audit log**: Consult the who-did-what-when trail
- **Notification targets**: Manage external (Slack/Discord/webhook...) notification destinations
- **Service accounts**: Manage API keys for the public JSON API
- **Settings**: Org-wide runtime settings

---

## ⚡ Full Automation

### Automation Architecture

A single sidebar entry, **Admin > Automation**, covers everything below -
there is no separate "Shifts" page and no separate "Refresh shifts" page
anymore (older versions had two pages here; they were merged into one for
clarity). It opens on a dashboard with at-a-glance stats and, when
relevant, a proactive alert (see "Gap alert" below); the **Générer /
rafraîchir le planning** button on that dashboard takes you to the
actual generation/refresh page.

```mermaid
graph TB
    subgraph Automation["AUTOMATION (single page)"]
        OnCall["On-Call rotation"]
        Shifts["Shifts"]
        Full["Generate<br/>(On-call + Shifts in a single pass)"]
        Refresh["Refresh shifts<br/>(on-calls untouched / gaps filled / regenerated)"]

        OnCall --> Full
        Shifts --> Full
        Full --> Refresh
    end
```

### Configuring Automatic On-Call

#### Step 1: Define the rotation order

1. Go to **Admin** > **Automation**, then **Générer / rafraîchir le
   planning**
2. For each eligible user:
   - ✅ **Include in rotation**: Check to include
   - **Order**: Drag and drop the user up/down the list to set their
     rotation position
3. Click **Sauvegarder l'ordre**

#### Step 2: Configure the period

1. **Start date**: First Friday of the period
2. **End date**: Last day of the period
3. Click **Prévisualiser (Dry Run)** to preview

#### Step 3: Generate

1. Check the preview result
2. Click **Générer les astreintes et shifts** to create the on-call
   periods and the shifts that follow from it (there is no separate step
   for shifts)

On-call generation searches for the assignment that **maximizes the
number of filled weeks** (backtracking, not a first-fit greedy pick) - a
week is only left empty for admin follow-up when no legal permutation of
the rotation order can cover it (e.g. every eligible user is on leave or
would break the minimum-rest rule that week), never just because an
earlier, avoidable choice used up the wrong person.

### Automatic Shift Generation

There is no dedicated "Shifts" automation page and no configurable
per-day/per-shift-type headcount setting. Shifts are generated
automatically as part of **Generate** above, from a fixed set of
business rules implemented in `AdvancedShiftAutomation`
(`app/utils/automation/advanced_shift_automation.py`):

- The 1pm-9pm slot is reserved for that week's on-call person, if they
  belong to a schedule group
- Slot rotation: whoever was on the 1pm-9pm slot one week must be on the
  7am-3pm slot the following week
- Everyone else defaults to the 9am-5pm slot (several people can share it)
- If only 2 people are available on a given day, the one who is *not*
  on-call is put on the 7am-3pm slot
- **7am-3pm minimum coverage**: at least one person must always be on this
  slot. If the rotation above doesn't naturally put anyone there (e.g. the
  person due for it isn't available/eligible that day), one available
  person is reassigned to it instead - the first one in the configured
  rotation order, so the choice stays predictable. With only 1 person
  available that day, they're placed directly on 7am-3pm rather than the
  usual 9am-5pm default, for the same reason.
- Monday to Friday only, respecting existing leave and on-call periods

If you need to touch shifts without regenerating on-call periods, use
**Refresh Shifts** below instead of **Generate**.

### Generate (On-Call + Shifts)

To generate both on-call periods and shifts in a single operation:

1. Go to **Admin** > **Automation** > **Générer / rafraîchir le planning**
2. Configure the on-call rotation order
3. Select the period
4. Click **Prévisualiser (Dry Run)**
5. Check that everything is correct
6. Click **Générer les astreintes et shifts**

> 💡 **Tip**: Generation takes on-call periods into account to avoid conflicts with shifts.
> This replaces all on-calls and shifts already on the selected period.

### Refreshing Shifts

Same page, separate section ("Rafraîchir les shifts"): recalculates
shifts from the on-calls already in the database, without discarding and
regenerating on-call periods themselves by default. Choose how on-calls
themselves are treated via a radio choice before clicking **Rafraîchir
les shifts**:

- **Ne pas y toucher** - only shifts are recalculated, on-calls are left
  exactly as they are (manual edits included)
- **Combler les trous d'astreintes** - creates on-calls only for weeks
  in the period that don't have one yet; existing on-calls (manual or
  previously generated) are never deleted or reassigned
- **Régénérer entièrement** - discards and regenerates every on-call in
  the period, then recalculates shifts

> ⚠️ **Warning**: shifts on the selected period are always replaced by this
> action, regardless of which on-call option you pick.

### Gap alert

The **Admin > Automation** dashboard (the page you land on before
"Générer / rafraîchir le planning") shows a banner when on-calls are
missing on Fridays strictly between the earliest and latest on-call
currently in the database - a case easy to miss because the generation
page's own default period starts from *today*, which may not reach a gap
sitting in the past. The banner's **Combler ces trous** button opens the
generation page with the exact affected date range and "Combler les
trous d'astreintes" already selected, so there's no manual date entry to
figure out.

### Business Rules

These rules are **hardcoded** in the automation classes, not stored in a
config file or database row you can inspect/edit. The only thing that is
actually persisted and editable through the admin UI is the on-call
**rotation order** (a plain list of user ids, `AutomationConfig` key
`rotation_order`, set via **Admin > Automation > Générer / rafraîchir le
planning**, see above) - everything else below is a fixed constant in
the code.

#### On-call (`app/utils/automation/oncall_automation.py`)

- Each on-call period always lasts 7 days, from Friday 9:00 PM (21h) to
  the following Friday 7:00 AM (7h) - not configurable
- Rotation follows the saved `rotation_order`, chosen by a backtracking
  search that maximizes the number of filled weeks (see "Step 3:
  Generate" above), not a first-available-candidate greedy pick
- Minimum 2-week gap enforced between two on-calls for the same user,
  checked against every on-call the user has (past and future), not just
  their single most recent one
- When on-calls are wiped and regenerated for a period (the automatic
  rebalance after a leave is added, and "Rafraîchir > Régénérer
  entièrement" - never the "Générer" button, an explicit full reset)
  each week prefers keeping the user it already had, instead of
  replaying the rotation order from scratch - minimizes how much of an
  already-working schedule gets reshuffled on every rebalance. Not a
  guarantee: a week whose occupant has a real conflict (on leave,
  overlapping another on-call) falls back to the rotation order for
  that week exactly like before

#### Shifts (`app/utils/automation/advanced_shift_automation.py`)

- Fixed time slots: `SHIFT_07_15` (7am-3pm), `SHIFT_09_17` (9am-5pm, the
  default), `SHIFT_13_21` (1pm-9pm, reserved for that week's on-call
  person)
- 7am-3pm minimum coverage is enforced separately from the per-user
  rotation rules above (`_ensure_minimum_07_15_coverage()`): if none of
  them puts anyone on that slot for a given day, one available person is
  reassigned to it - the first one in the configured rotation order
  (falls back to the first available person if the rotation order is
  empty or none of its users are available that day)
- Monday to Friday only ("weekend excluded" is not a toggle, it's simply
  never generated)
- No "number of people per shift type per day" setting exists anywhere
  in the UI or config

### Customizing Rules

The rotation order is the only piece of this that's customizable from
the UI (**Admin > Automation > Générer / rafraîchir le planning**).
Changing the fixed business rules above requires a code change to
`app/utils/automation/`.

---

## 🔧 Technical Configuration

### Settings configurable via the UI (`/admin/settings`)

Since versions 0.7.10 through 0.9.0, a growing set of settings —
previously environment variables only — is editable at runtime from
`/admin/settings` without a redeploy: default timezone, default language
(French/English), default date/time formats, public URL, pagination
(items per page), email notifications (global toggle), backup retention,
ICS token expiry duration, audit trail retention, and schedule history
retention (how many days of *past* shifts/on-calls to keep before an
automatic daily purge deletes them — 365 days by default, 0 disables the
purge entirely; see `scripts/cleanup_schedule_data.py` below). Each setting
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
dotenv run -- python run.py
```

- **Port**: 5000 (`FLASK_PORT`)
- **Host**: `0.0.0.0` by default (`FLASK_HOST`) - listens on every
  interface, not just localhost
- **Debug**: Disabled by default (`FLASK_DEBUG`, default `false`) - see
  "Enabling debug mode" under "Logs and Troubleshooting" below before
  turning it on; it is a real code-execution risk if left on for a
  reachable deployment

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

> ⚠️ **SQLite warning**: Multiple workers (`-w 4`) require a database
> that supports real concurrent writers (PostgreSQL or MariaDB/MySQL -
> see "Database Configuration" below). With the default SQLite database,
> use a single worker (`-w 1`) - this is exactly why
> `docker/entrypoint.sh` runs `gunicorn --workers 1 --threads 4` by
> default in the Docker image.

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
from their own profile (**Profile > ICS Token > Generate a token**,
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

### Public REST API

Shipped in v0.9.3 (this is no longer a planned feature) - a read-only
JSON API for third-party integrations, distinct from the internal
cookie-based `/api/*` routes used by the app's own frontend:

- Prefix `/api/v1/*` (`app/api/`), built with flask-smorest
- Authenticated with a bearer token issued to a **service account**
  (`Admin > Service accounts`, `/admin/service-accounts` - create,
  regenerate, revoke), not a user session
- Read-only: `GET` list (paginated) and `GET <id>` for shifts, on-call,
  leave, users, and list-only for shift types - no write endpoints in v1
- Auto-generated OpenAPI spec at `GET /api/v1/openapi.json` (no
  interactive Swagger/Redoc UI is served, to avoid relaxing the CSP for a
  CDN-hosted UI)
- Rate-limited per service account

See [`api/API.md`](../api/API.md) (documents the internal `/api/*`
routes) and the auto-generated `/api/v1/openapi.json` spec for the public
API's exact schema.

### Webhooks

There is no general-purpose outbound webhook system for arbitrary
third-party event subscriptions. What does exist is narrower: **external
notification targets** (`Admin > Notification targets`,
`/admin/notification-targets`), which can point at a generic webhook URL
(or Slack/Discord/Telegram/...) via [Apprise](https://github.com/caronc/apprise)
service URLs, and receive notifications for a closed set of categories
(`swap`, `backup`, `system`, `shift_weekly`, `oncall_weekly`) - not a
mechanism for subscribing to arbitrary application events.

---

## 🎨 Customization

### Interface Customization

#### Logo and Favicon

Replace the file `app/static/images/favicon.png` (referenced by
`app/templates/base.html`) to change the application's favicon. There is
no image-logo slot in the header - the header currently shows the
"Kairos" text brand only, no image is loaded there (coming soon).

#### Custom CSS

There is no auto-loaded custom CSS hook - `app/static/css/custom.css` is
not referenced anywhere and would not be picked up automatically. To add
custom styles today, add a `<link rel="stylesheet">` for your file
directly in `app/templates/base.html` alongside the other stylesheets, or
edit the existing files under `app/static/css/` (see "Frontend" in
`CLAUDE.md` for the current CSS structure - Tailwind/daisyUI via CDN,
`theme-colors.css` for the Dracula/Alucard palette, a handful of custom
files for FullCalendar/dashboard/rotation-order overrides).

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
   [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-notification-configuration)):
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
retention, and email alerts — see the [Backup Guide](../deployment/BACKUP_GUIDE.md)
for the full detail. Entirely driven by environment variables
(`BACKUP_ENABLED` first and foremost, see
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-backup-configuration))
— disabled by default.

Two ways to trigger a backup:

- **Admin interface** (`/admin/backups`): active configuration, list of
  local/S3 backups, on-demand creation, cleanup, download. Manual
  creation is refused if `BACKUP_ENABLED=false`.
- **Cron** (recommended for automation): see [Automation with
  Cron](../deployment/BACKUP_GUIDE.md#-automation-with-cron), or, in Docker,
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

### Schedule History Cleanup

`scripts/cleanup_schedule_data.py` deletes shifts and on-calls older than
the configured retention window — controlled by the "Historique du
planning" setting on `/admin/settings` (365 days by default, 0 disables
the purge entirely). Unlike backups/notifications, no environment
variable gates this one: the retention value itself is the on/off
switch. Triggered by an external cron job — in Docker, already present
in `docker/crontabs/appuser` (runs daily at 4am) and requires no
`*_ENABLED` flag, since a schedule this far in the past isn't shown by
the calendar anyway (see [`architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)).
Bare-metal deployments need their own crontab entry:

```bash
# Daily at 4am: purge old shifts/on-calls past the retention window
0 4 * * * cd /path/to/kairos && venv/bin/python scripts/cleanup_schedule_data.py >> /var/log/kairos-cleanup.log 2>&1
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

**Solution**: Check your email and password. There is no self-service
"forgot password" feature - an administrator must reset the password for
you from **Admin > Users > Edit** (see "Resetting passwords" above).

#### Error 500: Server error

**Cause**: Internal server issue.

**Solution**:
1. Check the application logs
2. Check that the database is accessible
3. Restart the application
4. Contact support if the problem persists

### Logs and Troubleshooting

#### Enabling debug mode

Set the `FLASK_DEBUG=true` environment variable (`.env`) - `run.py`
reads it via `Config.DEBUG` and passes it to `app.run(debug=...)`.

> ⚠️ **Do not hardcode `debug=True` in `run.py`**: `FLASK_DEBUG` defaults
> to `false` specifically because Werkzeug's interactive debugger (shown
> on any unhandled exception when debug is on) is a remote code
> execution surface on a reachable deployment - hardcoding `debug=True`
> would silently re-enable it regardless of what an admin sets in `.env`.
> Only ever enable this on a local/trusted machine, never in production.

#### Viewing logs

```bash
# Run the application with logs (dotenv run so .env is actually applied -
# see "Development (built-in Flask server)" above)
dotenv run -- python run.py
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
