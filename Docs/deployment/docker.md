# Dockerizing Kairos (Simplified Version)

> **Recommended method**: two files to grab
> (`docker/docker-compose.example.yml` + `docker/.env.example`), an
> already-built image from the registry - no repo clone, no
> local build, no OIDC mock (dev only). Building the image yourself
> or cloning the repo for a full dev environment (`docker/`)
> are alternatives reserved for development or special
> cases - see below.

---

## 🚀 Quick start (recommended method)

The image is meant to be pulled from the **GitHub Container Registry**
(`ghcr.io`), alongside the rest of this project's GitHub-hosted
tooling (Actions, releases). `.github/workflows/docker-release.yml`
builds and pushes both `ghcr.io/foxops/kairos:latest` and a
version-tagged `ghcr.io/foxops/kairos:<version>` - the version is read
straight from `app/utils/health.py`'s `APP_VERSION_DEFAULT` at build
time. Kept **manual-only** (`workflow_dispatch`, never triggered by a
tag push) so an image is only ever published as a deliberate action,
restricted to `main` (a `require-main` job fails loudly if run from any
other ref - `main` is the single source of truth for releases, dev
branches like `1.0.0-RC2` merge into it first, never the other way
around), and gated on `tests.yml` actually passing: it calls that
workflow directly (`workflow_call`) and only proceeds to build/push if
it succeeds - not a "remember to run that first" note, an enforced
dependency (`needs:`). Run it from the Actions tab (or `gh workflow run
docker-release.yml --ref main`). The same
build can also be run entirely outside GitHub Actions: `docker build -f
docker/Dockerfile -t ghcr.io/foxops/kairos:latest .` from the repo
root, then `docker push`, after `docker login ghcr.io` with a PAT that
has `write:packages` scope.

### 1️⃣ Grab the two required files

No need to clone the entire repo - only two files are
needed, both already adapted for Docker execution (absolute
paths under `/app/data`, `TALISMAN_FORCE_HTTPS=false` by default - no
TLS reverse proxy in this minimal stack):

```bash
mkdir kairos && cd kairos

curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example
```

### 2️⃣ Configure

```bash
nano .env
```

**Minimal variables to change:**
```env
# Image to pull from the GitHub Container Registry. No CI job
# currently sets/publishes this automatically (see the note above) -
# whoever pushes the image to ghcr.io must pick and communicate the
# tag used here.
KAIROS_IMAGE=ghcr.io/foxops/kairos:latest

SECRET_KEY=your_secret_key
DEFAULT_ADMIN_PASSWORD=your_password
```

### 3️⃣ Start

```bash
docker compose up -d
```

`docker-compose.yml` (derived from `docker-compose.example.yml`) has no
`build:` section - it can only pull the image from the registry, never
build it locally. Development mode (Flask with reloader) or
production (Gunicorn) depending on `FLASK_ENV` in `.env` (`production` by
default in `docker/.env.example` - the image's own baked-in fallback,
used only if the variable is unset entirely, is `development`, see
`docker/Dockerfile`).

### 4️⃣ Access the application

Open your browser: [http://localhost:5000](http://localhost:5000)

**Default credentials:**
- Email: `admin@kairos.local`
- Password: `admin123` (or whichever you configured in `.env`)

### Update

```bash
docker compose pull
docker compose up -d
```

---

## 🛠️ Alternatives: development and special cases

Reserved for cases where the registry image isn't enough: contributing to
the code, testing a `Dockerfile` change, exercising the SSO/OIDC flow
locally (optional mock). Requires cloning the entire repo:

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule/docker
```

Structure of `docker/` (relative `.env`/`data`/`logs` paths resolved
relative to `docker/docker-compose.yml`, so all under `docker/`):

```
leviia-schedule/
└── docker/
    ├── Dockerfile          # Ultra-lightweight Docker image
    ├── entrypoint.sh       # Startup script (web server + conditional crond)
    ├── crontabs/appuser    # Email reminder and backup scheduling (crond)
    ├── docker-compose.yml  # App service (local build or registry) + optional OIDC mock (profile)
    ├── .env                # Environment variables (to create, not committed)
    ├── data/                # Persistent SQLite data
    └── logs/                # Logs
```

All commands below run **from the `docker/` folder**.

### Configure the environment

```bash
cp .env.example .env
nano .env
```

Same variables as the recommended method above (`SECRET_KEY`,
`DEFAULT_ADMIN_PASSWORD`, `DATABASE_URL`, `TALISMAN_FORCE_HTTPS`).
`KAIROS_IMAGE` can also be used here (see below).

### Build the image yourself (plain `docker build`, no Compose)

```bash
docker build -f Dockerfile -t kairos:dev ..
```

The `Dockerfile` needs the rest of the repo as its build
context (`..`) - the command itself runs from `docker/`, not from the
repo root.

### Build and start via Compose

Without `KAIROS_IMAGE` in `.env` (or if removed), `docker/docker-compose.yml`
falls back to its default local build tag (`kairos:dev`):

```bash
docker compose build
docker compose up -d
```

With `KAIROS_IMAGE` set, `docker compose pull kairos` then
`docker compose up -d --no-build` uses the registry image without
ever triggering a local build - useful for testing the dev stack
(including the OIDC mock) against an already-published image.

### Test the SSO/OIDC flow locally (mock)

`docker/docker-compose.yml` includes a test OIDC provider
(`ghcr.io/soluto/oidc-server-mock`), started only via its dedicated
Compose profile - never by a plain `docker compose up -d`:

```bash
docker compose --profile oidc-mock up -d
```

Access: [http://localhost:5000](http://localhost:5000) (default
credentials identical to the recommended section above).

---

## ⚙️ Configuration

### Environment variables

| Variable | Description | Default | Required |
|----------|-------------|--------|--------|
| `KAIROS_IMAGE` | Image to use (registry) | required in `docker/docker-compose.example.yml`; `kairos:dev` (local build) in `docker/docker-compose.yml` | ✅ / ❌ depending on the file |
| `FLASK_ENV` | Mode (development/production) | `production` (set explicitly in `docker/.env.example`; the image's own baked-in fallback if unset is `development`) | ❌ |
| `SECRET_KEY` | Flask secret key | required | ✅ |
| `DATABASE_URL` | Database URL (see note below) | sqlite:////app/data/app.db | ❌ |
| `TALISMAN_FORCE_HTTPS` | Force HTTPS - `false` without a TLS reverse proxy | `false` (both in `docker/.env.example` and the app's own fallback in `app/config/base.py` when unset - there is no separate prod default; flip it to `true` yourself once a TLS-terminating reverse proxy is in place, see "In production" below) | ❌ |
| `DEFAULT_ADMIN_PASSWORD` | Admin password | admin123 | ✅ |

> **`DATABASE_URL` note**: four slashes (`sqlite:////app/data/app.db`),
> not three - it's an absolute path (`/app/data/app.db`) resolved on the
> mounted volume, not a relative one.

### Full `.env` example

```env
# Registry image - mandatory with docker/docker-compose.example.yml
KAIROS_IMAGE=ghcr.io/foxops/kairos:latest

# Basic configuration
FLASK_ENV=development
SECRET_KEY=your_generated_secret_key

# Database - absolute path on the mounted volume (./data:/app/data)
DATABASE_URL=sqlite:////app/data/app.db

# No TLS reverse proxy in front of this service by default
TALISMAN_FORCE_HTTPS=false

# Admin password
DEFAULT_ADMIN_PASSWORD=your_secure_password
```

---

## 📦 Files Explained

### docker/docker-compose.example.yml
- **Recommended method**: a single service, no `build:` - always pulls
  `KAIROS_IMAGE` from the registry. Copy it to
  `docker-compose.yml` in the folder where you deploy (see
  Quick start).
- **Volumes**: `./data:/app/data`, `./logs:/app/logs` (created
  automatically by Docker on first startup if missing)
- **Port**: 5000 exposed

### docker/Dockerfile
- **Base**: Python 3.11 Alpine (ultra-lightweight)
- **Dependencies**: Installs `docker/requirements.txt` (includes Gunicorn, `psycopg[binary]`, and `PyMySQL` - not the root `requirements.txt`)
- **User**: `appuser` (non-root) for security
- **Size**: Optimized with Alpine and cleanup of build dependencies
- **Build context**: `..` (repo root) - the `Dockerfile` copies
  `docker/requirements.txt`, `docker/entrypoint.sh`, and the application code
  (`COPY . .`), so the context has to cover the whole repo even though the
  `docker build` command is run from `docker/`. Not relevant if
  you use the registry image (recommended method).

### docker/entrypoint.sh
- **Initialization**: Creates the SQLite database if it doesn't exist
- **Default data**: Creates the shift types, the group, and the admin
- **Email notifications and backups**: if `NOTIFICATIONS_ENABLED=true`
  and/or `BACKUP_ENABLED=true` (see `.env`), starts `crond` (busybox,
  already present in the Alpine image, no extra package needed) in the
  background before launching the web server - schedule in
  `docker/crontabs/appuser`. Nothing else to configure: one environment
  variable per feature, no extra Docker service
  to manage. For local backups to survive container recreation,
  set `BACKUP_LOCAL_DIR=/app/data/backups` (the `./data:/app/data`
  volume is already mounted).
- **Server selection**:
  - `development` → `python run.py` (with reloader)
  - `production` → `gunicorn` (1 worker for SQLite)

### docker/docker-compose.yml (dev environment, clone required)
- **App service** (`kairos`): `image: ${KAIROS_IMAGE:-kairos:dev}`
  - local build by default (`build: context: ..`), or registry image
    without building if `KAIROS_IMAGE` is set and `--no-build` is passed - see
    above. And, if enabled, email reminders and/or
    backups - same container, see above - see
    [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-notification-configuration)
    for the SMTP configuration and
    [`deployment/BACKUP_GUIDE.md`](BACKUP_GUIDE.md) for backups
- **`oidc-mock` service**: optional, behind the `oidc-mock` Compose
  profile - never starts with a plain `docker compose up -d`
  (see Alternatives above)
- **Volumes**: Data and log persistence
- **Ports**: 5000 exposed (+ 8080 for `oidc-mock` if its profile is enabled)

---

## 🎯 Commands

### Recommended (two files downloaded, no clone)

| Command | Description |
|----------|-------------|
| `docker compose up -d` | Pull the image and start |
| `docker compose pull` | Update the image |
| `docker compose logs -f kairos` | View logs |
| `docker compose exec kairos sh` | Shell into the container |
| `docker compose down` | Stop |

### Dev alternatives (clone required, from `docker/`)

| Command | Description |
|----------|-------------|
| `docker build -f Dockerfile -t kairos:dev ..` | Build the image (plain docker build, no Compose) |
| `docker compose build` | Build the image locally via Compose |
| `docker compose up -d` | Start with the locally built image |
| `docker compose --profile oidc-mock up -d` | Start with the OIDC mock as well (local SSO testing) |

---

## 🔒 Basic Security

### 1. Generate a secret key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Generate an admin password

```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 3. Never commit `.env`

```bash
echo ".env" >> .gitignore
```

### 4. In production

- Set `FLASK_ENV=production` in `.env`, then `docker compose up -d`
- Change `SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD`
- Set up a reverse proxy (Nginx, Traefik) for HTTPS, then switch
  `TALISMAN_FORCE_HTTPS=true` back on (or remove the line) in `.env`

---

## 🌐 Going further

This basic configuration uses **SQLite** and is optimized for:
- **Simplicity**: A single container, easy to deploy
- **Portability**: Works anywhere with Docker
- **Lightness**: ~150 MB image

### Adding PostgreSQL or MySQL/MariaDB

See the advanced guide: [DEPLOYMENT_ADVANCED.md](DEPLOYMENT_ADVANCED.md)

This guide explains how to extend this configuration to use:
- **PostgreSQL** or **MySQL/MariaDB** as the relational database
- **Gunicorn with multiple workers** for better performance

⚠️ **Recommendation**: Master the basic SQLite deployment first before adding these components.

---

## 🐛 Troubleshooting

### Problem: The container doesn't start

**Check the logs:**
```bash
docker compose logs kairos
```

**Check the image:**
```bash
docker compose pull
```

### Problem: Permission error

**Solution:**
```bash
# Give ownership to the current user
sudo chown -R $USER:$USER data logs

# Create the required directories if missing
mkdir -p data logs
chmod -R 755 data logs
```

### Problem: Database not initialized

**Solution:**
```bash
# Remove the existing database
rm -f data/app.db

# Restart the container
docker compose down && docker compose up -d
```

### Problem: Port 5000 already in use

**Solution:**
```bash
# Find the process
sudo lsof -i :5000

# Kill the process
kill <PID>

# Or change the port in docker-compose.yml
```

---

## 📚 Examples

### Quick deployment (registry, no clone)

```bash
mkdir kairos && cd kairos
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # KAIROS_IMAGE, SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, TALISMAN_FORCE_HTTPS

docker compose up -d

# Access the application
# http://localhost:5000
```

### Simple production deployment

```bash
mkdir kairos && cd kairos
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # KAIROS_IMAGE, SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, FLASK_ENV=production

# Production mode - Gunicorn - is driven by FLASK_ENV in .env,
# not a separate command
docker compose up -d

# Access the application
# http://localhost:5000
```

---

## 📞 Support

For advanced configurations (PostgreSQL, MySQL/MariaDB, etc.), see:
- [Advanced Guide: PostgreSQL or MySQL/MariaDB](DEPLOYMENT_ADVANCED.md)

For specific issues, check:
1. The logs with `docker compose logs`
2. The configuration in `.env`
3. File permissions

---

*Simplified documentation for Kairos - Basic Dockerization*
