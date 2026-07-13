# Guide Avancé : Déploiement avec PostgreSQL et Redis

Ce guide explique comment étendre la configuration Docker de base pour utiliser **PostgreSQL** comme base de données et **Redis** comme cache, une fois que vous maîtrisez le déploiement de base avec SQLite.

---

## 📋 Prérequis

- Avoir déployé avec succès Leviia Schedule avec SQLite (voir [docs/docker.md](docker.md))
- Comprendre les concepts de base de Docker et Docker Compose
- Avoir accès à un serveur avec Docker installé

---

## 🏗️ Architecture Étendue

```
┌─────────────────────────────────────────────────────────────┐
│                        Application Web                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Leviia Schedule (Gunicorn)                 │  │
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

## 📦 Étapes pour ajouter PostgreSQL

### 1. Créer un fichier `docker-compose.postgres.yml`

Créez un nouveau fichier dans le dossier `docker/` :

```yaml
# docker/docker-compose.postgres.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: leviia-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-leviia}
      - POSTGRES_USER=${POSTGRES_USER:-leviia}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changez-moi}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - leviia-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-leviia} -d ${POSTGRES_DB:-leviia}"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"

volumes:
  postgres_data:
    driver: local

networks:
  leviia-net:
    external: true
```

### 2. Modifier le service web pour utiliser PostgreSQL

Modifiez votre `docker/docker-compose.yml` pour ajouter la dépendance à PostgreSQL :

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: leviia-web
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY:-changez-moi}
      - DATABASE_URL=${DATABASE_URL:-postgresql://leviia:changez-moi@db:5432/leviia}
      - DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD:-changez-moi}
    volumes:
      - ../data:/app/data
      - ../logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
    networks:
      - leviia-net

networks:
  leviia-net:
    driver: bridge
```

### 3. Configurer les variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```env
# Configuration PostgreSQL
POSTGRES_DB=leviia
POSTGRES_USER=leviia
POSTGRES_PASSWORD=votre_mot_de_passe_sécurisé
DATABASE_URL=postgresql://leviia:votre_mot_de_passe_sécurisé@db:5432/leviia

# Configuration production
FLASK_ENV=production
SECRET_KEY=votre_clé_secrète
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_admin
```

⚠️ **Important** : Générez des mots de passe sécurisés :
```bash
# Générer un mot de passe PostgreSQL
python -c "import secrets; print(secrets.token_urlsafe(24))"

# Générer une clé secrète Flask
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Démarrer les services

```bash
# Démarrer PostgreSQL et l'application
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml up -d
```

### 5. Vérifier le fonctionnement

```bash
# Vérifier que PostgreSQL est prêt
docker compose logs db

# Vérifier que l'application se connecte
docker compose logs web
```

---

## 🔴 Ajouter Redis pour le cache

### 1. Créer un fichier `docker-compose.redis.yml`

```yaml
# docker/docker-compose.redis.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: leviia-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - leviia-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
    driver: local

networks:
  leviia-net:
    external: true
```

### 2. Configurer l'application pour utiliser Redis

Modifiez votre `docker/docker-compose.yml` pour ajouter la configuration Redis :

```yaml
services:
  web:
    # ... configuration existante ...
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY:-changez-moi}
      - DATABASE_URL=${DATABASE_URL:-postgresql://leviia:changez-moi@db:5432/leviia}
      - DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD:-changez-moi}
      - CACHE_TYPE=RedisCache
      - CACHE_REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    # ... reste de la configuration ...
```

### 3. Démarrer avec Redis

```bash
# Démarrer PostgreSQL, Redis et l'application
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
```

---

## 🌐 Configuration Complète de Production

### Fichier `.env` pour la production

```env
# Configuration de base
FLASK_ENV=production
SECRET_KEY=votre_clé_secrète_générée
PREFERRED_URL_SCHEME=https

# Base de données PostgreSQL
POSTGRES_DB=leviia
POSTGRES_USER=leviia
POSTGRES_PASSWORD=votre_mot_de_passe_postgres
DATABASE_URL=postgresql://leviia:votre_mot_de_passe_postgres@db:5432/leviia

# Cache Redis
CACHE_TYPE=RedisCache
CACHE_REDIS_URL=redis://redis:6379/0

# Sécurité
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=true
RATE_LIMIT_ENABLED=true
COMPRESS_ENABLED=true
WTF_CSRF_ENABLED=true

# Données par défaut
DEFAULT_ADMIN_EMAIL=admin@votre-domaine.com
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_admin_sécurisé
DEFAULT_GROUP_NAME=Defaut
```

### Commande de démarrage complète

```bash
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
```

---

## 🔧 Configuration de Gunicorn pour la Production

Par défaut, l'image utilise Gunicorn avec 1 worker pour SQLite. Pour PostgreSQL, vous pouvez augmenter le nombre de workers.

### Modifier le script d'entrée

Éditez `docker/entrypoint.sh` et modifiez la section production :

```bash
if [ "$FLASK_ENV" = "production" ]; then
    # Pour PostgreSQL avec plus de workers
    exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 run:app
    
    # Pour SQLite (1 worker max)
    # exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
fi
```

### Reconstruire l'image

```bash
docker compose -f docker/docker-compose.yml build --no-cache
```

---

## 📊 Comparaison des Configurations

| Configuration | Base de données | Cache | Workers Gunicorn | Complexité |
|---------------|----------------|-------|------------------|------------|
| **De base** | SQLite | ❌ Non | 1 | ⭐ Très simple |
| **PostgreSQL** | PostgreSQL | ❌ Non | 1 | ⭐⭐ Simple |
| **PostgreSQL + Redis** | PostgreSQL | ✅ Redis | 4 | ⭐⭐⭐ Moyenne |
| **Production complète** | PostgreSQL | ✅ Redis | 4 | ⭐⭐⭐ Moyenne |

---

## 🔒 Sécurité en Production

### 1. Ne jamais exposer les ports des services internes

❌ **À éviter** :
```yaml
services:
  db:
    ports:
      - "5432:5432"  # Expose PostgreSQL sur le réseau
  redis:
    ports:
      - "6379:6379"  # Expose Redis sur le réseau
```

✅ **Recommandé** :
```yaml
services:
  db:
    # Pas de ports exposés, accessible uniquement via le réseau Docker
  redis:
    # Pas de ports exposés
```

### 2. Utiliser un reverse proxy

Configurez **Nginx** ou **Traefik** comme reverse proxy pour :
- Terminer SSL/HTTPS
- Gérer les requêtes HTTP/HTTPS
- Ajouter des headers de sécurité

Exemple de configuration Nginx minimale :

```nginx
upstream leviia {
    server web:5000;
}

server {
    listen 80;
    server_name leviia.votre-domaine.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name leviia.votre-domaine.com;
    
    ssl_certificate /etc/letsencrypt/live/leviia.votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/leviia.votre-domaine.com/privkey.pem;
    
    location / {
        proxy_pass http://leviia;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Configurer HTTPS

Utilisez **Let's Encrypt** pour obtenir des certificats SSL gratuits :

```bash
# Installer Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtenir un certificat
sudo certbot --nginx -d leviia.votre-domaine.com

# Configurer le renouvellement automatique
sudo certbot renew --dry-run
```

### 4. Sécuriser les accès

- **Ne jamais utiliser l'admin par défaut en production**
- **Changer tous les mots de passe** dans `.env`
- **Limiter l'accès** au serveur
- **Configurer un firewall** (ufw, iptables)

---

## 📁 Sauvegardes

### Sauvegarder PostgreSQL

```bash
# Sauvegarde manuelle
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
  exec db pg_dump -U leviia -d leviia > backups/leviia-$(date +%Y%m%d-%H%M%S).sql

# Restaurer une sauvegarde
docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
  exec -T db psql -U leviia -d leviia < backups/leviia-20240101-120000.sql
```

### Sauvegarder Redis

```bash
# Sauvegarde manuelle
docker compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml \
  exec redis redis-cli save

# Les données sont déjà persistées dans le volume redis_data
```

### Script de sauvegarde automatique

Créez un script `backup.sh` :

```bash
#!/bin/bash

# Sauvegarder PostgreSQL
if [ -f docker/docker-compose.postgres.yml ]; then
    docker compose -f docker/docker-compose.yml -f docker/docker-compose.postgres.yml \
      exec db pg_dump -U leviia -d leviia > backups/leviia-$(date +%Y%m%d-%H%M%S).sql
    
    # Garder seulement les 7 dernières sauvegardes
    find backups -name "leviia-*.sql" -mtime +7 -delete
fi

# Sauvegarder Redis (déjà persistant via volume)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml \
  exec redis redis-cli save
```

Configurez une tâche cron pour exécuter ce script quotidiennement :

```bash
# Éditer la crontab
crontab -e

# Ajouter cette ligne pour une sauvegarde à 2h du matin
0 2 * * * /chemin/vers/leviia-schedule/backup.sh
```

---

## 🔄 Mises à jour

### Mettre à jour l'application

```bash
# Arrêter les services
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml down

# Mettre à jour le code
git pull origin main

# Reconstruire et redémarrer
docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml build --no-cache

docker compose -f docker/docker-compose.yml \
  -f docker/docker-compose.postgres.yml \
  -f docker/docker-compose.redis.yml up -d
```

### Mettre à jour les dépendances

```bash
# Dans le conteneur
docker compose -f docker/docker-compose.yml exec leviia-schedule sh

# Mettre à jour requirements.txt
pip freeze > requirements.txt

# Reconstruire l'image
docker compose -f docker/docker-compose.yml build --no-cache
```

---

## 🐛 Dépannage

### Problème : PostgreSQL ne démarre pas

**Symptômes :**
- Le conteneur `db` crash
- Erreur de permissions sur `/var/lib/postgresql/data`

**Solutions :**

1. **Vérifier les logs** :
   ```bash
   docker compose logs db
   ```

2. **Supprimer le volume et redémarrer** :
   ```bash
   docker volume rm leviia-schedule_postgres_data
   docker compose up -d
   ```

3. **Vérifier les permissions** :
   ```bash
   docker compose exec db ls -la /var/lib/postgresql/data
   ```

### Problème : L'application ne se connecte pas à PostgreSQL

**Symptômes :**
- Erreur de connexion dans les logs de `web`
- Timeout ou refus de connexion

**Solutions :**

1. **Vérifier que PostgreSQL est prêt** :
   ```bash
   docker compose exec db pg_isready -U leviia -d leviia
   ```

2. **Vérifier les variables d'environnement** :
   ```bash
   docker compose exec web env | grep DATABASE_URL
   ```

3. **Tester la connexion manuellement** :
   ```bash
   docker compose exec web python -c "
   from sqlalchemy import create_engine
   engine = create_engine('${DATABASE_URL}')
   print(engine.connect())
   "
   ```

### Problème : Redis ne répond pas

**Symptômes :**
- Erreurs de cache dans l'application
- Timeout sur Redis

**Solutions :**

1. **Vérifier que Redis est prêt** :
   ```bash
   docker compose exec redis redis-cli ping
   ```

2. **Vérifier la configuration** :
   ```bash
   docker compose exec web env | grep CACHE
   ```

3. **Tester la connexion manuellement** :
   ```bash
   docker compose exec web python -c "
   import redis
   r = redis.Redis.from_url('${CACHE_REDIS_URL}')
   print(r.ping())
   "
   ```

---

## 📚 Ressources Utiles

- [Documentation officielle de PostgreSQL](https://www.postgresql.org/docs/)
- [Documentation officielle de Redis](https://redis.io/docs/)
- [Documentation Docker Compose](https://docs.docker.com/compose/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

---

## 🤝 Support

Si vous rencontrez des problèmes avec cette configuration avancée :

1. **Vérifiez les logs** : `docker compose logs`
2. **Testez les connexions** manuellement
3. **Consultez la documentation** officielle
4. **Revenez à la configuration SQLite** si nécessaire

Pour une assistance plus poussée, envisagez de faire appel à un administrateur système expérimenté.
