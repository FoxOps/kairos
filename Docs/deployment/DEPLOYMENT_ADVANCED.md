# Advanced Guide: Deploying with PostgreSQL, MySQL/MariaDB and Redis

This guide explains how to extend the base Docker configuration to use **PostgreSQL** or **MySQL/MariaDB** as the database and **Redis** as the cache, once you're comfortable with the basic SQLite deployment.

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
         │                          │
         ▼                          ▼
┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL     │   │     Redis       │
│   (Production)   │   │   (Cache)       │
└─────────────────┘   └─────────────────┘
```

---

## 📦 Steps to add PostgreSQL

### 1. Create a `docker-compose.postgres.yml` file

Create a new file in the `docker/` folder:

```yaml
# docker/docker-compose.postgres.yml
version: '3.8'

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
      - kairos-net
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
  kairos-net:
    external: true
```

### 2. Modify the web service to use PostgreSQL

Edit your `docker/docker-compose.yml` to add the PostgreSQL dependency:

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: kairos-web
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
      - kairos-net

networks:
  kairos-net:
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
docker compose logs web
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
version: '3.8'

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
      - kairos-net
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
  kairos-net:
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

No changes to the `Dockerfile`/the `kairos-web` image are
necessary: the `PyMySQL` driver is already included in
`docker/requirements.txt`, 100% pure Python, with no system dependency.

### 3. Start the services

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql.yml up -d
```

---

## 🔴 Add Redis for caching

### 1. Create a `docker-compose.redis.yml` file

```yaml
# docker/docker-compose.redis.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: kairos-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - kairos-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
    driver: local

networks:
  kairos-net:
    external: true
```

### 2. Configure the application to use Redis

Edit your `docker/docker-compose.yml` to add the Redis configuration:

```yaml
services:
  web:
    # ... existing configuration ...
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY:-changez-moi}
      - DATABASE_URL=${DATABASE_URL:-postgresql://kairos:changez-moi@db:5432/kairos}
      - DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD:-changez-moi}
      - CACHE_TYPE=RedisCache
      - CACHE_REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    # ... rest of the configuration ...
```

### 3. Start with Redis

```bash
# Start PostgreSQL, Redis and the application
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
```

---

## 🌐 Full Production Configuration

### `.env` file for production

```env
# Base configuration
FLASK_ENV=production
SECRET_KEY=votre_clé_secrète_générée
PREFERRED_URL_SCHEME=https

# PostgreSQL database
POSTGRES_DB=kairos
POSTGRES_USER=kairos
POSTGRES_PASSWORD=votre_mot_de_passe_postgres
DATABASE_URL=postgresql://kairos:votre_mot_de_passe_postgres@db:5432/kairos

# Redis cache
CACHE_TYPE=RedisCache
CACHE_REDIS_URL=redis://redis:6379/0

# Security
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=true
RATE_LIMIT_ENABLED=true
COMPRESS_ENABLED=true
WTF_CSRF_ENABLED=true

# Default data
DEFAULT_ADMIN_EMAIL=admin@votre-domaine.com
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_admin_sécurisé
DEFAULT_GROUP_NAME=Defaut
```

### Full startup command

```bash
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
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

| Configuration | Database | Cache | Gunicorn Workers | Complexity |
|---------------|----------------|-------|------------------|------------|
| **Basic** | SQLite | ❌ No | 1 | ⭐ Very simple |
| **PostgreSQL** | PostgreSQL | ❌ No | 1 | ⭐⭐ Simple |
| **PostgreSQL + Redis** | PostgreSQL | ✅ Redis | 4 | ⭐⭐⭐ Medium |
| **Full production** | PostgreSQL | ✅ Redis | 4 | ⭐⭐⭐ Medium |

---

## 🔒 Production Security

### 1. Never expose internal service ports

❌ **To avoid**:
```yaml
services:
  db:
    ports:
      - "5432:5432"  # Exposes PostgreSQL on the network
  redis:
    ports:
      - "6379:6379"  # Exposes Redis on the network
```

✅ **Recommended**:
```yaml
services:
  db:
    # No exposed ports, accessible only via the Docker network
  redis:
    # No exposed ports
```

### 2. Use a reverse proxy

Configure **Nginx** or **Traefik** as a reverse proxy to:
- Terminate SSL/HTTPS
- Handle HTTP/HTTPS requests
- Add security headers

Example minimal Nginx configuration:

```nginx
upstream kairos {
    server web:5000;
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

### Backing up Redis

```bash
# Manual backup
docker compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml \
  exec redis redis-cli save

# Data is already persisted in the redis_data volume
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

# Back up Redis (already persistent via volume)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml \
  exec redis redis-cli save
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
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml down

# Update the code
git pull origin main

# Rebuild and restart
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml build --no-cache

docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
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
- Connection error in the `web` logs
- Timeout or connection refused

**Solutions:**

1. **Check that PostgreSQL is ready**:
   ```bash
   docker compose exec db pg_isready -U kairos -d kairos
   ```

2. **Check environment variables**:
   ```bash
   docker compose exec web env | grep DATABASE_URL
   ```

3. **Test the connection manually**:
   ```bash
   docker compose exec web python -c "
   from sqlalchemy import create_engine
   engine = create_engine('${DATABASE_URL}')
   print(engine.connect())
   "
   ```

### Issue: Redis is not responding

**Symptoms:**
- Cache errors in the application
- Timeout on Redis

**Solutions:**

1. **Check that Redis is ready**:
   ```bash
   docker compose exec redis redis-cli ping
   ```

2. **Check the configuration**:
   ```bash
   docker compose exec web env | grep CACHE
   ```

3. **Test the connection manually**:
   ```bash
   docker compose exec web python -c "
   import redis
   r = redis.Redis.from_url('${CACHE_REDIS_URL}')
   print(r.ping())
   "
   ```

---

## 📚 Useful Resources

- [Official PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Official Redis documentation](https://redis.io/docs/)
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
