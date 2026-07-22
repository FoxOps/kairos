# 🏢 Deployment Guide - Kairos

> **Version**: 1.0  
> **Last updated**: June 2026  
> **Status**: Production documentation

> ⚠️ **Recommended method: Docker.** This guide covers deployment
> **without Docker** (Gunicorn/uWSGI bare-metal) - an alternative for
> cases where Docker is not available or not desired. For the main
> method (image published to the registry), see
> [`docker.md`](docker.md).

---

## 📁 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Configuration](#3-configuration)
4. [Deploying with Gunicorn](#4-deploying-with-gunicorn)
5. [Deploying with uWSGI](#5-deploying-with-uwsgi)
6. [Deploying with Docker](#6-deploying-with-docker)
7. [Database Configuration](#7-database-configuration)
8. [Environment Variables Configuration](#8-environment-variables-configuration)
9. [Production Security](#9-production-security)
10. [Maintenance](#10-maintenance)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. 📁 Prerequisites

### 1.1 Operating System
- Linux (Ubuntu 20.04/22.04, Debian 11/12, CentOS 8+)
- macOS (10.15+)
- Windows (10/11 with WSL2 recommended)

### 1.2 Required Software
| Software | Minimum Version | Description |
|----------|------------------|-------------|
| Python | 3.11+ | Programming language (the codebase uses PEP 604 `X \| None` type hints, which require at least Python 3.10; `docker/Dockerfile` and `.github/workflows/tests.yml` both use 3.11, the only version this app is actually built/tested against) |
| pip | 26.1.2+ | Python package manager (`requirements.txt` pins `pip>=26.1.2` for CVE fixes) |
| Git | 2.20+ | Version control |
| PostgreSQL | 12+ | Database (recommended) |
| SQLite | 3.31+ | Embedded database (for development) |

### 1.3 Hardware Resources
- **CPU**: 2 cores minimum (4 recommended)
- **RAM**: 2 GB minimum (4 GB recommended)
- **Storage**: 10 GB minimum (SSD recommended)

---

## 2. 📁 Environment Setup

### 2.1 Clone the repository
```bash
# Clone the GitHub repository
git clone https://github.com/FoxOps/kairos.git
cd kairos

# Switch to the latest stable version
git checkout main
```

### 2.2 Create a virtual environment
```bash
# Create the virtual environment
python -m venv venv

# Activate the environment
# On Linux/macOS
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 2.3 Install dependencies
```bash
# Install base dependencies - already includes the PostgreSQL driver
# (psycopg[binary]) and the MySQL/MariaDB driver (PyMySQL), both listed
# in requirements.txt; no extra install step is needed for either
# database. The app has no Redis/caching integration at all (caching is
# handled outside the app, e.g. by a reverse proxy), so there is no
# `redis` package to install either.
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 📁 Configuration

### 3.1 .env File
Create a `.env` file at the project root with the following variables:

```bash
# Base configuration
# Note: outside Docker, FLASK_ENV itself has no effect on the app - it
# is read only by docker/entrypoint.sh to choose gunicorn vs `python
# run.py`. For this bare-metal guide, that choice is simply whichever
# command you run (see sections 4/5 below) - kept here mainly as a
# documented convention some process managers still check.
FLASK_ENV=production
SECRET_KEY=your_secret_key_here_generated_with_secrets_token_urlsafe_32

# Database (choose one option)
# Option 1: SQLite (for development)
DATABASE_URL=sqlite:///app.db

# Option 2: PostgreSQL (recommended for production)
# DATABASE_URL=postgresql://user:password@localhost:5432/kairos

# Option 3: MySQL/MariaDB
# DATABASE_URL=mysql://user:password@localhost:3306/kairos

# Security configuration
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
# CSRF protection (Flask-WTF's CSRFProtect) and Gzip/Brotli response
# compression (Flask-Compress) are both always on unconditionally
# (app/__init__.py) - there is no WTF_CSRF_ENABLED/COMPRESS_ENABLED
# switch read by the app, so neither variable is listed here.
# REMEMBER_COOKIE_SECURE/PREFERRED_URL_SCHEME are likewise not read by
# app/config/base.py - only REMEMBER_COOKIE_DURATION and
# SESSION_PROTECTION are, for the "remember me" cookie.

# Logging configuration
LOG_LEVEL=WARNING
# LOG_DIR is not actually read by app/utils/logging/logger.py - the
# app/error/http/audit log files always go to <current working
# directory>/logs (hardcoded), regardless of this variable. Run the
# app from the directory you want `logs/` created under (e.g. the
# project root, matching the systemd WorkingDirectory in Appendix A.1
# below) rather than relying on LOG_DIR.

# Performance configuration
RATE_LIMIT_ENABLED=True

# Authentication configuration
# LOGIN_DISABLED=False  # Never enable this in production
```

### 3.2 Generate a secret key
```bash
# Use Python to generate a secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. 📁 Deploying with Gunicorn

### 4.1 Installation
```bash
pip install gunicorn
```

### 4.2 Basic configuration
```bash
# Start with Gunicorn (4 workers, port 5000)
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### 4.3 Recommended configuration for production
```bash
# Start with more workers and a longer timeout
gunicorn \
  -w 8 \
  -b 0.0.0.0:5000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --graceful-timeout 30 \
  run:app
```

### 4.4 Configuration with a config file
Create a `gunicorn.conf.py` file:

```python
# gunicorn.conf.py
workers = 8
bind = "0.0.0.0:5000"
timeout = 120
max_requests = 1000
max_requests_jitter = 100
graceful_timeout = 30
worker_class = "gthread"
threads = 4
keepalive = 2
```

Then start with:
```bash
gunicorn -c gunicorn.conf.py run:app
```

### 4.5 Using a Unix socket
```bash
gunicorn -w 8 -b unix:/tmp/kairos.sock run:app
```

---

## 5. 📁 Deploying with uWSGI

### 5.1 Installation
```bash
pip install uwsgi
```

### 5.2 Basic configuration
Create a `uwsgi.ini` file:

```ini
[uwsgi]
module = run:app
workers = 8
threads = 4
master = true
chmod-socket = 660
vacuum = true
die-on-term = true

# Socket configuration
socket = /tmp/kairos_uwsgi.sock
chown-socket = www-data:www-data
chmod-socket = 660

# HTTP configuration (optional)
# http = 0.0.0.0:5000

# Process configuration
max-requests = 1000
max-worker-lifetime = 3600
reload-mercy = 30

# Memory configuration
buffer-size = 32768
```

### 5.3 Start uWSGI
```bash
uwsgi --ini uwsgi.ini
```

---

## 6. 📁 Deploying with Docker

**Recommended method for the whole project** (see the warning
at the top of this guide) - the actual `Dockerfile`/`docker-compose.yml` live
under `docker/`, with the image pulled from the GitHub Container Registry
(`ghcr.io`), built and pushed via a manual-only GitHub Actions workflow
(`docker-release.yml`) - see [`docker.md`](docker.md) for the details. This guide
specifically covers bare-metal deployment (Gunicorn/uWSGI), so it does not
maintain a separate copy of that configuration here.

👉 See [`docker.md`](docker.md) for the full details: pulling the image
from the registry (recommended method), or building it yourself/using
Docker Compose (dev alternative).

---

## 7. 📁 Database Configuration

### 7.1 SQLite (for development)
```bash
# SQLite is configured by default
# The database will be created automatically on first startup

# To initialize manually
python run.py
```

### 7.2 PostgreSQL (recommended for production)

#### 7.2.1 Installation
```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# On CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 7.2.2 Configuration
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create a user and a database
CREATE USER kairos_user WITH PASSWORD 'your_password';
CREATE DATABASE kairos OWNER kairos_user;
GRANT ALL PRIVILEGES ON DATABASE kairos TO kairos_user;
\q
```

#### 7.2.3 Configuration in Kairos
```bash
# In your .env file
DATABASE_URL=postgresql://kairos_user:your_password@localhost:5432/kairos
```

### 7.3 MySQL/MariaDB

Kairos connects to any MySQL/MariaDB server via SQLAlchemy +
`PyMySQL` — a 100% pure Python driver, already included in `requirements.txt`.
No system library (`libmariadb-dev`/`libmysqlclient-dev`) is
required, either to install or to run it, neither on the host nor in the
Docker image.

#### 7.3.1 Recommended case: external MySQL/MariaDB server

If you already have a MySQL/MariaDB server managed elsewhere (managed
hosting provider, existing cluster, another VM), you just need to create the
database and application user **on that server** (not on the machine running
Kairos), then point `DATABASE_URL` at it:

```bash
# On the external MySQL/MariaDB server (run there, not here)
CREATE DATABASE kairos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'kairos_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON kairos.* TO 'kairos_user'@'%';
FLUSH PRIVILEGES;
```

```bash
# In Kairos's .env (this machine - no local MySQL server
# required, neither on the host nor in the Docker image)
DATABASE_URL=mariadb://kairos_user:your_password@mysql-external.example.com:3306/kairos

# Recommended for an external server: idle connections may be
# dropped server-side (MySQL's wait_timeout defaults to ~8h, often
# shorter on a managed offering) - pool_pre_ping revalidates the connection
# before each checkout from the pool, pool_recycle proactively closes it.
SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": true, "pool_recycle": 3600}
```

#### 7.3.2 Alternative: local MySQL/MariaDB server (dev/test)

To host MariaDB directly on the same machine (typically in
development):

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install mariadb-server
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MySQL
sudo mysql_secure_installation
```

```bash
# Connect to MySQL
sudo mysql -u root

# Create a user and a database
CREATE USER 'kairos_user'@'localhost' IDENTIFIED BY 'your_password';
CREATE DATABASE kairos;
GRANT ALL PRIVILEGES ON kairos.* TO 'kairos_user'@'localhost';
FLUSH PRIVILEGES;
quit
```

```bash
# In your .env file
DATABASE_URL=mysql://kairos_user:your_password@localhost:3306/kairos
```

See also
[`DEPLOYMENT_ADVANCED.md`](DEPLOYMENT_ADVANCED.md#-add-mysqlmariadb-local-devtest)
for an optional docker-compose overlay equivalent to this local case.

---

## 8. 📁 Environment Variables Configuration

### 8.1 Essential variables
| Variable | Description | Default Value | Recommendation |
|----------|-------------|----------------|----------------|
| `FLASK_ENV` | Not read by the app itself - only by `docker/entrypoint.sh` (Docker only) | n/a outside Docker | n/a outside Docker |
| `SECRET_KEY` | Flask secret key | Random | **REQUIRED** |
| `DATABASE_URL` | Database URL | `sqlite:///app.db` | PostgreSQL |
| `LOG_LEVEL` | Logging level | `INFO` | `WARNING` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `True` | `True` |

### 8.2 Security variables
| Variable | Description | Default Value | Recommendation |
|----------|-------------|----------------|----------------|
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | `False` | `True` |
| `SESSION_COOKIE_HTTPONLY` | Cookies not accessible via JS | `True` | `True` |
| `SESSION_COOKIE_SAMESITE` | SameSite policy | `Lax` | `Lax` or `Strict` |

CSRF protection (Flask-WTF's `CSRFProtect`) and Gzip/Brotli response
compression (Flask-Compress) are both unconditionally enabled in
`app/__init__.py` - there is no `WTF_CSRF_ENABLED`/`COMPRESS_ENABLED`
switch read anywhere in `app/config/base.py`, so neither has any effect
if set. `REMEMBER_COOKIE_SECURE` and `PREFERRED_URL_SCHEME` are
likewise not read by the app - the actual "remember me" cookie
settings are `REMEMBER_COOKIE_DURATION` and `SESSION_PROTECTION`.

### 8.3 Performance variables
There is no `DATABASE_POOL_SIZE`/`DATABASE_MAX_OVERFLOW`/
`DATABASE_POOL_RECYCLE` triplet read by the app. The real mechanism is
a single JSON-encoded `SQLALCHEMY_ENGINE_OPTIONS` variable, passed
straight through to SQLAlchemy's `create_engine()`:

| Variable | Description | Default Value | Recommendation |
|----------|-------------|----------------|----------------|
| `SQLALCHEMY_ENGINE_OPTIONS` | JSON dict of SQLAlchemy engine options | `{}` | `{"pool_pre_ping": true, "pool_recycle": 3600}` for PostgreSQL/MySQL/MariaDB (see 7.3.1 above) |

---

## 9. 📁 Production Security

### 9.1 Best practices
- **Always** use HTTPS in production
- **Never** expose the application without authentication
- Keep dependencies up to date (`pip install --upgrade -r requirements.txt`)
- Use a WAF (Web Application Firewall) such as Cloudflare or ModSecurity
- Configure regular database backups
- Restrict access to the admin interface

### 9.2 Firewall configuration
```bash
# Only allow the necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### 9.3 SSL/TLS configuration
Use **Let's Encrypt** with Certbot to obtain free SSL certificates:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain a certificate
sudo certbot --nginx -d your-domain.com

# Automatic renewal
sudo certbot renew --dry-run
```

### 9.4 HTTP header security
Security headers are already configured in the application:
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

---

## 10. 📁 Maintenance

### 10.1 Update
```bash
# Update the application
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Restart the application
# systemctl restart kairos  # If you use systemd
```

### 10.2 Backup
```bash
# Back up the SQLite database
cp app.db app.db.backup-$(date +%Y%m%d)

# Back up PostgreSQL
pg_dump kairos > kairos_backup_$(date +%Y%m%d).sql

# Back up the configuration file
cp .env kairos_config_backup_$(date +%Y%m%d)/
```

### 10.3 Monitoring
```bash
# View the logs
tail -f logs/kairos-app.log

# Check the application status
# If you use systemd
systemctl status kairos

# Check resource usage
top
htop
```

---

## 11. 📁 Troubleshooting

### 11.1 Common issues

#### 11.1.1 "Database is locked"
**Cause**: SQLite does not support concurrent access.  
**Solution**: 
- Use PostgreSQL for production
- Or configure `SQLALCHEMY_ENGINE_OPTIONS` via `.env` (see
  Docs/reference/ENVIRONMENT_VARIABLES.md)

#### 11.1.2 "502 Bad Gateway" (Nginx)
**Cause**: Gunicorn/uWSGI is not responding.  
**Solution**:
```bash
# Check that Gunicorn/uWSGI is running
ps aux | grep gunicorn
ps aux | grep uwsgi

# Restart the service
systemctl restart kairos
```

#### 11.1.3 "Connection refused" (PostgreSQL)
**Cause**: PostgreSQL is not running or the configuration is incorrect.  
**Solution**:
```bash
# Check that PostgreSQL is running
sudo systemctl status postgresql

# Test the connection
psql -U kairos_user -d kairos -h localhost
```

#### 11.1.4 "ModuleNotFoundError"
**Cause**: Dependencies are not installed.  
**Solution**:
```bash
# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 11.2 Logs and diagnostics

#### 11.2.1 View the application logs
```bash
# Application logs
tail -f logs/kairos-app.log

# Error logs
tail -f logs/kairos-errors.log

# HTTP logs
tail -f logs/kairos-http-errors.log
```

#### 11.2.2 Test the database connection
```bash
# Test the SQLite connection
sqlite3 app.db "SELECT COUNT(*) FROM user;"

# Test the PostgreSQL connection
psql -U kairos_user -d kairos -c "SELECT COUNT(*) FROM user;"
```

---

## 📁 Appendices

### A.1 systemd configuration
Create a `/etc/systemd/system/kairos.service` file:

```ini
[Unit]
Description=Kairos Application
After=network.target postgresql.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/kairos
Environment="PATH=/var/www/kairos/venv/bin"
ExecStart=/var/www/kairos/venv/bin/gunicorn -w 8 -b unix:/tmp/kairos.sock run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start kairos

# Enable at startup
sudo systemctl enable kairos

# Check the status
sudo systemctl status kairos
```

### A.2 Nginx configuration
Create a `/etc/nginx/sites-available/kairos` file:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/kairos.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /var/www/kairos/app/static/;
        expires 30d;
    }
}
```

Then:
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/kairos /etc/nginx/sites-enabled/

# Test the configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## 📁 Support

For any questions or issues:
- See the [full documentation](../README.md)
- Open an **Issue** on [GitHub](https://github.com/FoxOps/kairos/issues)
- See the [discussions](https://github.com/FoxOps/kairos/discussions)

---

> **⚠️ Important note**: This guide assumes you have basic knowledge of Linux system administration. For a production deployment, it is strongly recommended to engage an experienced system administrator.
