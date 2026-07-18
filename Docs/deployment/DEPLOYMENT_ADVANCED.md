# Advanced Guide: Deploying with PostgreSQL or MySQL/MariaDB

This guide explains how to extend the base Docker configuration to use **PostgreSQL** or **MySQL/MariaDB** as the database, once you're comfortable with the basic SQLite deployment.

> **Note**: this guide previously also covered adding Redis as a
> cache. The app has no caching integration at all - no `CACHE_TYPE`/
> `CACHE_REDIS_URL` config is read anywhere, Flask-Limiter deliberately
> uses in-memory storage (`app/__init__.py`), and there is no `redis`
> package in `requirements.txt`/`docker/requirements.txt`. That section
> has been removed rather than left describing a feature that doesn't
> exist.

---

## 📋 Prerequisites

- Successfully deployed Kairos with SQLite (see [docs/docker.md](docker.md))
- Understand basic Docker and Docker Compose concepts
- Have access to a server with Docker installed

---

## 🏗️ Extended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Application                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   Kairos (Gunicorn)                      │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL     │
│   (Production)   │
└─────────────────┘
```

---

## 📦 Steps to add PostgreSQL

### 1. Create a `docker-compose.postgres.yml` file

Create a new file in the `docker/` folder:

```yaml
# docker/docker-compose.postgres.yml
services:
  db:
    image: postgres:15-alpine
    container_name: kairos-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-kairos}
      - POSTGRES_USER=${POSTGRES_USER:-kairos}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changez-moi}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - kairos-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-kairos} -d ${POSTGRES_DB:-kairos}"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

volumes:
  postgres_data:
    driver: local

networks:
  kairos-network:
    external: true
```

### 2. Modify the `kairos` service to use PostgreSQL

Edit your `docker/docker-compose.yml` to add the PostgreSQL dependency.
The service is named `kairos` there (not `web`) and the network is
`kairos-network` (not `kairos-net`) - both must match the real
`docker/docker-compose.yml` exactly, or `docker compose -f
docker-compose.yml -f docker-compose.postgres.yml` merges the override
into an unrelated new service/network instead of extending the
existing one:

```yaml
# docker/docker-compose.yml
services:
  kairos:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: kairos
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY:-changez-moi}
      - DATABASE_URL=${DATABASE_URL:-postgresql://kairos:changez-moi@db:5432/kairos}
      - DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD:-changez-moi}
    volumes:
      - ../data:/app/data
      - ../logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
    networks:
      - kairos-network

networks:
  kairos-network:
    driver: bridge
```

### 3. Configure environment variables

Add these variables to your `.env` file:

```env
# PostgreSQL configuration
POSTGRES_DB=kairos
POSTGRES_USER=kairos
POSTGRES_PASSWORD=votre_mot_de_passe_sécurisé
DATABASE_URL=postgresql://kairos:votre_mot_de_passe_sécurisé@db:5432/kairos

# Production configuration
FLASK_ENV=production
SECRET_KEY=votre_clé_secrète
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_admin
```

⚠️ **Important**: Generate secure passwords:
```bash
# Generate a PostgreSQL password
python -c "import secrets; print(secrets.token_urlsafe(24))"

# Generate a Flask secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Start the services

```bash
# Start PostgreSQL and the application
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml up -d
```

### 5. Verify it's working

```bash
# Check that PostgreSQL is ready
docker compose logs db

# Check that the application connects
docker compose logs kairos
```

---

## 🐬 Add MySQL/MariaDB (local dev/test)

This guide covers the case of a **locally Docker-Compose-managed** MySQL/MariaDB,
useful for development/testing — mirroring the PostgreSQL section above.
To connect to an **already existing external** MySQL/MariaDB server (the
most common case in production), see directly
[`DEPLOYMENT_GUIDE.md` section 7.3.1](DEPLOYMENT_GUIDE.md#731-recommended-case-external-mysqlmariadb-server) —
no Docker overlay is necessary in that case, only the `DATABASE_URL`
variable in `.env` changes.

### 1. Create a `docker-compose.mysql.yml` file

```yaml
# docker/docker-compose.mysql.yml
services:
  db:
    image: mariadb:11
    container_name: kairos-db
    restart: unless-stopped
    environment:
      - MARIADB_DATABASE=${MARIADB_DATABASE:-kairos}
      - MARIADB_USER=${MARIADB_USER:-kairos}
      - MARIADB_PASSWORD=${MARIADB_PASSWORD:-changez-moi}
      - MARIADB_ROOT_PASSWORD=${MARIADB_ROOT_PASSWORD:-changez-moi-aussi}
    volumes:
      - mariadb_data:/var/lib/mysql
    networks:
      - kairos-network
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - "3306:3306"

volumes:
  mariadb_data:
    driver: local

networks:
  kairos-network:
    external: true
```

### 2. Configure environment variables

```env
# MariaDB configuration
MARIADB_DATABASE=kairos
MARIADB_USER=kairos
MARIADB_PASSWORD=votre_mot_de_passe_sécurisé
MARIADB_ROOT_PASSWORD=un_autre_mot_de_passe_sécurisé
DATABASE_URL=mariadb://kairos:votre_mot_de_passe_sécurisé@db:3306/kairos
```

No changes to the `Dockerfile`/the `kairos` image are
necessary: the `PyMySQL` driver is already included in
`docker/requirements.txt`, 100% pure Python, with no system dependency.

### 3. Start the services

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql.yml up -d
```

---

## 🌐 Full Production Configuration

### `.env` file for production

```env
# Base configuration
FLASK_ENV=production
SECRET_KEY=votre_clé_secrète_générée

# PostgreSQL database
POSTGRES_DB=kairos
POSTGRES_USER=kairos
POSTGRES_PASSWORD=votre_mot_de_passe_postgres
DATABASE_URL=postgresql://kairos:votre_mot_de_passe_postgres@db:5432/kairos
SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": true, "pool_recycle": 3600}

# Security - SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE and
# RATE_LIMIT_ENABLED are the only ones of these actually read by the
# app (app/config/base.py); CSRF protection and response compression
# are unconditionally on regardless of any env var, and
# PREFERRED_URL_SCHEME/REMEMBER_COOKIE_SECURE/COMPRESS_ENABLED/
# WTF_CSRF_ENABLED are not read anywhere, so they are omitted here.
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
RATE_LIMIT_ENABLED=true

# Default data
DEFAULT_ADMIN_EMAIL=admin@votre-domaine.com
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_admin_sécurisé
DEFAULT_GROUP_NAME=Defaut
```

### Full startup command

```bash
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml up -d
```

---

## 🔧 Gunicorn Configuration for Production

By default, the image uses Gunicorn with 1 worker for SQLite. For PostgreSQL, you can increase the number of workers.

### Modify the entrypoint script

Edit `docker/entrypoint.sh` and modify the production section:

```bash
if [ "$FLASK_ENV" = "production" ]; then
    # For PostgreSQL with more workers
    exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 run:app
    
    # For SQLite (1 worker max)
    # exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
fi
```

### Rebuild the image

```bash
docker compose -f docker/docker-compose.yml build --no-cache
```

---

## 📊 Configuration Comparison

| Configuration | Database | Gunicorn Workers | Complexity |
|---------------|----------------|------------------|------------|
| **Basic** | SQLite | 1 | ⭐ Very simple |
| **PostgreSQL** | PostgreSQL | 1 (until `docker/entrypoint.sh` is edited, see below) | ⭐⭐ Simple |
| **Full production** | PostgreSQL | 4 | ⭐⭐⭐ Medium |

---

## 🔒 Production Security

### 1. Never expose internal service ports

❌ **To avoid**:
```yaml
services:
  db:
    ports:
      - "5432:5432"  # Exposes PostgreSQL on the network
```

✅ **Recommended**:
```yaml
services:
  db:
    # No exposed ports, accessible only via the Docker network
```

### 2. Use a reverse proxy

Configure **Nginx** or **Traefik** as a reverse proxy to:
- Terminate SSL/HTTPS
- Handle HTTP/HTTPS requests
- Add security headers

Example minimal Nginx configuration:

```nginx
upstream kairos {
    server kairos:5000;
}

server {
    listen 80;
    server_name kairos.votre-domaine.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name kairos.votre-domaine.com;
    
    ssl_certificate /etc/letsencrypt/live/kairos.votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kairos.votre-domaine.com/privkey.pem;
    
    location / {
        proxy_pass http://kairos;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

This `proxy_set_header Host $host` is generally sufficient: the app already
trusts a single reverse proxy via `ProxyFix` (see `app/__init__.py`).
If your topology adds extra hops (Kubernetes ingress,
load balancer) that don't correctly forward the original Host/domain,
set `PUBLIC_BASE_URL` (e.g. `https://kairos.votre-domaine.com`)
to force the domain used in absolute links generated by the app
(ICS export) — see [ENVIRONMENT_VARIABLES.md](../reference/ENVIRONMENT_VARIABLES.md).

### 3. Configure HTTPS

Use **Let's Encrypt** to get free SSL certificates:

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get a certificate
sudo certbot --nginx -d kairos.votre-domaine.com

# Configure automatic renewal
sudo certbot renew --dry-run
```

### 4. Secure access

- **Never use the default admin account in production**
- **Change all passwords** in `.env`
- **Restrict access** to the server
- **Configure a firewall** (ufw, iptables)

---

## 📁 Backups

### Backing up PostgreSQL

```bash
# Manual backup
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
  exec db pg_dump -U kairos -d kairos > backups/kairos-$(date +%Y%m%d-%H%M%S).sql

# Restore a backup
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
  exec -T db psql -U kairos -d kairos < backups/kairos-20240101-120000.sql
```

### Automatic backup script

Create a `backup.sh` script:

```bash
#!/bin/bash

# Back up PostgreSQL
if [ -f docker/docker-compose.postgres.yml ]; then
    docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
      exec db pg_dump -U kairos -d kairos > backups/kairos-$(date +%Y%m%d-%H%M%S).sql
    
    # Keep only the last 7 backups
    find backups -name "kairos-*.sql" -mtime +7 -delete
fi
```

Set up a cron job to run this script daily:

```bash
# Edit the crontab
crontab -e

# Add this line for a backup at 2am
0 2 * * * /chemin/vers/kairos/backup.sh
```

---

## 🔄 Updates

### Updating the application

```bash
# Stop the services
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml down

# Update the code
git pull origin main

# Rebuild and restart
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml build --no-cache

docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml up -d
```

### Updating dependencies

```bash
# Inside the container
docker compose -f docker/docker-compose.yml exec kairos sh

# Update requirements.txt
pip freeze > requirements.txt

# Rebuild the image
docker compose -f docker/docker-compose.yml build --no-cache
```

---

## 🐛 Troubleshooting

### Issue: PostgreSQL won't start

**Symptoms:**
- The `db` container crashes
- Permission error on `/var/lib/postgresql/data`

**Solutions:**

1. **Check the logs**:
   ```bash
   docker compose logs db
   ```

2. **Remove the volume and restart**:
   ```bash
   docker volume rm kairos_postgres_data
   docker compose up -d
   ```

3. **Check permissions**:
   ```bash
   docker compose exec db ls -la /var/lib/postgresql/data
   ```

### Issue: The application won't connect to PostgreSQL

**Symptoms:**
- Connection error in the `kairos` logs
- Timeout or connection refused

**Solutions:**

1. **Check that PostgreSQL is ready**:
   ```bash
   docker compose exec db pg_isready -U kairos -d kairos
   ```

2. **Check environment variables**:
   ```bash
   docker compose exec kairos env | grep DATABASE_URL
   ```

3. **Test the connection manually**:
   ```bash
   docker compose exec kairos python -c "
   from sqlalchemy import create_engine
   engine = create_engine('${DATABASE_URL}')
   print(engine.connect())
   "
   ```

---

## 📚 Useful Resources

- [Official PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Gunicorn documentation](https://docs.gunicorn.org/)

---

## 🤝 Support

If you run into problems with this advanced configuration:

1. **Check the logs**: `docker compose logs`
2. **Test the connections** manually
3. **Check the official documentation**
4. **Revert to the SQLite configuration** if necessary

For further assistance, consider engaging an experienced system administrator.
