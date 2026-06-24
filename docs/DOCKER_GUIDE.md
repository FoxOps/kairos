# 🐳 Guide Docker pour Leviia Schedule

> **Version** : 1.0.0 | **Dernière mise à jour** : Juin 2026

---

## 📚 **À propos de ce guide**

Ce document fait partie de la **documentation officielle** de Leviia Schedule et couvre spécifiquement le déploiement et la gestion de l'application avec **Docker** et **Docker Compose**.

> **💡 Pour une introduction rapide, consultez le [Guide de Démarrage Rapide](QUICK_START.md)**

---

## 🎯 **Public cible**

| Rôle | Niveau | Utilité |
|------|--------|---------|
| **👥 Utilisateur** | Débutant | Déploiement local pour test |
| **🛡️ Administrateur** | Intermédiaire | Déploiement en production |
| **💻 Développeur** | Avancé | Développement avec Docker |

---

## 🚀 **Prérequis**

### Logiciels requis

| Logiciel | Version minimale | Lien |
|----------|------------------|------|
| Docker | 20.10 | [Installer Docker](https://docs.docker.com/get-docker/) |
| Docker Compose | 1.29 | [Installer Docker Compose](https://docs.docker.com/compose/install/) |

### Ressources matérielles

| Environnement | CPU | RAM | Espace disque |
|---------------|-----|-----|---------------|
| Développement | 1 cœur | 512 Mo | 1 Go |
| Production (petite équipe) | 2 cœurs | 1 Go | 2 Go |
| Production (grande équipe) | 4 cœurs | 2 Go | 5 Go |

---

## 📦 **Architecture Docker**

### Schéma global

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Host                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Leviia App    │    │   PostgreSQL    │    │    Redis    │ │
│  │   (Flask)        │    │   (Optionnel)    │    │  (Optionnel) │ │
│  └────────┬────────┘    └────────┬────────┘    └──────┬──────┘ │
│           │                       │                     │         │
│           └───────────────────────┼─────────────────────┘         │
│                               │                                   │
│                    ┌──────────▼──────────┐                          │
│                    │  leviia-network      │                          │
│                    │  (Réseau Docker)     │                          │
│                    └──────────────────────┘                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Volumes Docker                              ││
│  ├─────────────────┬─────────────────┬───────────────────────────┤│
│  │ leviia-data      │ leviia-logs      │ leviia-postgres-data      ││
│  │ leviia-instance  │ leviia-redis-data│                           ││
│  └─────────────────┴─────────────────┴───────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Services disponibles

| Service | Image | Port interne | Port externe | Description |
|---------|-------|--------------|--------------|-------------|
| `app` | `hardened-images/catalog/dhi/python:alpine-3.24/3.14` | 5000 | 5000 | Application Flask Leviia Schedule |
| `db` | `postgres:15-alpine` | 5432 | 5432 | Base de données PostgreSQL |
| `redis` | `redis:7-alpine` | 6379 | 6379 | Cache Redis (optionnel) |

### Volumes persistants

| Volume | Montage | Description | Persistant |
|--------|---------|-------------|-------------|
| `leviia-data` | `/app/data` | Données de l'application (SQLite, uploads) | ✅ Oui |
| `leviia-logs` | `/app/logs` | Fichiers de log | ✅ Oui |
| `leviia-instance` | `/app/instance` | Instance Flask (SQLite si utilisé) | ✅ Oui |
| `leviia-postgres-data` | `/var/lib/postgresql/data` | Données PostgreSQL | ✅ Oui |
| `leviia-redis-data` | `/data` | Données Redis | ✅ Oui |

---

## 📥 **Installation et Configuration**

### Étape 1 : Cloner le dépôt

```bash
# Cloner le dépôt Git
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

### Étape 2 : Configurer l'environnement

#### Option A : Utiliser le fichier d'exemple

```bash
# Copier le fichier d'environnement Docker
cp docker/.env.docker docker/.env

# Éditer le fichier .env avec vos paramètres
nano .env  # ou utilisez votre éditeur préféré
```

#### Option B : Créer un fichier .env personnalisé

```bash
# Créer un nouveau fichier .env
cat > .env << 'EOF'
# Configuration de base
LEVIIA_PORT=5000
FLASK_ENV=production
SERVER=gunicorn

# Sécurité (À CHANGER ABSOLUMENT!)
SECRET_KEY=votre-cle-secrete-ici

# Base de données PostgreSQL
DATABASE_URL=postgresql://leviia:motdepasse@db:5432/leviia
POSTGRES_DB=leviia
POSTGRES_USER=leviia
POSTGRES_PASSWORD=motdepasse

# Données par défaut
DEFAULT_ADMIN_EMAIL=admin@leviia.local
DEFAULT_ADMIN_PASSWORD=admin123
EOF
```

### Étape 3 : Générer une clé secrète

> **⚠️ IMPORTANT** : Ne jamais utiliser la clé par défaut en production !

```bash
# Générer une clé secrète sécurisée
python -c "import secrets; print(secrets.token_hex(32))"

# Copier le résultat dans le fichier .env
# SECRET_KEY=votre-nouvelle-cle-secrete
```

---

## 🚀 **Déploiement**

### Option 1 : Déploiement complet avec PostgreSQL (Recommandé)

```bash
# Se placer dans le dossier docker
cd docker

# Construire et démarrer tous les services
docker-compose up -d

# Vérifier que tout est démarré
docker-compose ps
```

**Accès** : http://localhost:5000

### Option 2 : Déploiement simple avec SQLite

```bash
# Se placer dans le dossier docker
cd docker

# Modifier la configuration pour utiliser SQLite
echo "DATABASE_URL=sqlite:////app/data/app.db" >> .env

# Démarrer uniquement l'application (sans PostgreSQL)
docker-compose up -d app
```

**Accès** : http://localhost:5000

### Option 3 : Déploiement avec Redis (pour le cache)

```bash
# Se placer dans le dossier docker
cd docker

# Démarrer tous les services y compris Redis
docker-compose up -d

# Vérifier que Redis est démarré
docker-compose ps
```

---

## 📋 **Configuration Détaillée**

### Variables d'Environnement

#### 🔧 Configuration de l'Application

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `LEVIIA_PORT` | 5000 | Port externe de l'application | Changez si 5000 est occupé |
| `FLASK_ENV` | production | Environnement Flask | `development` pour le dev |
| `FLASK_DEBUG` | false | Mode debug Flask | `true` uniquement en développement |
| `SERVER` | gunicorn | Serveur WSGI | gunicorn, flask, uwsgi |
| `SECRET_KEY` | - | **Clé secrète Flask** | **OBLIGATOIRE à changer** |

#### 🗄️ Configuration de la Base de Données

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `DATABASE_URL` | postgresql://... | URL de connexion | SQLite ou PostgreSQL |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | false | Suivi des modifications | Laissez à false |
| `SQLALCHEMY_ECHO` | false | Afficher les requêtes SQL | true pour le débogage |

**Exemples d'URL de base de données** :
```bash
# PostgreSQL (recommandé pour la production)
DATABASE_URL=postgresql://user:password@db:5432/database

# SQLite (pour le développement)
DATABASE_URL=sqlite:////app/data/app.db

# MySQL/MariaDB
DATABASE_URL=mysql://user:password@db:3306/database
```

#### 🔐 Configuration PostgreSQL

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `POSTGRES_DB` | leviia | Nom de la base de données | Changez si nécessaire |
| `POSTGRES_USER` | leviia | Utilisateur PostgreSQL | Changez pour la sécurité |
| `POSTGRES_PASSWORD` | leviia-pass | **Mot de passe PostgreSQL** | **À CHANGER ABSOLUMENT** |
| `POSTGRES_PORT` | 5432 | Port PostgreSQL | Changez si nécessaire |

#### ⚡ Configuration Gunicorn

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `GUNICORN_BIND` | 0.0.0.0:5000 | Adresse et port | 0.0.0.0:5000 pour Docker |
| `GUNICORN_WORKERS` | 4 | Nombre de workers | 2-4 par CPU core |
| `GUNICORN_THREADS` | 2 | Threads par worker | 2-4 selon la charge |
| `GUNICORN_TIMEOUT` | 120 | Timeout (secondes) | 60-300 selon les requêtes |
| `GUNICORN_LOG_LEVEL` | info | Niveau de log | debug, info, warning, error |

#### 👤 Données par Défaut

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `DEFAULT_ADMIN_EMAIL` | admin@leviia.local | Email de l'admin | Changez pour la sécurité |
| `DEFAULT_ADMIN_PASSWORD` | admin123 | **Mot de passe admin** | **À CHANGER IMMÉDIATEMENT** |
| `DEFAULT_GROUP_NAME` | Défaut | Nom du groupe | Personnalisez si nécessaire |
| `DEFAULT_GROUP_IN_SCHEDULE` | true | Groupe dans le planning | true/false |
| `DEFAULT_GROUP_IN_ONCALL` | true | Groupe dans les astreintes | true/false |

#### 📝 Configuration du Logging

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `LOG_LEVEL` | INFO | Niveau de log principal | DEBUG, INFO, WARNING, ERROR |
| `LOG_DIR` | /app/logs | Dossier des logs | Ne pas changer |
| `LOG_FILE_APP` | leviia-app.log | Fichier de log application | Personnalisable |
| `LOG_FILE_ERRORS` | leviia-errors.log | Fichier de log erreurs | Personnalisable |

#### 🔒 Configuration de la Sécurité

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `SESSION_COOKIE_SECURE` | false | Cookies sécurisés (HTTPS) | **true en production** |
| `SESSION_COOKIE_HTTPONLY` | true | Cookies HTTP-only | Laissez à true |
| `SESSION_COOKIE_SAMESITE` | Lax | Politique SameSite | Lax, Strict, None |
| `RATE_LIMIT_ENABLED` | true | Limite de taux | true pour la sécurité |
| `RATE_LIMIT_DEFAULT` | 200 per day, 50 per hour | Limites par défaut | Ajustez selon besoins |
| `COMPRESS_ENABLED` | true | Compression Gzip | true pour les performances |
| `WTF_CSRF_ENABLED` | true | Protection CSRF | Laissez à true |

---

## 🛠️ **Commandes Docker**

### Commandes de base

| Commande | Description |
|----------|-------------|
| `docker-compose up -d` | Démarrer tous les services |
| `docker-compose down` | Arrêter tous les services |
| `docker-compose down -v` | Arrêter et supprimer les volumes |
| `docker-compose ps` | Voir l'état des services |
| `docker-compose logs -f` | Voir tous les logs |
| `docker-compose logs -f app` | Voir les logs de l'application |

### Commandes Makefile

Le projet inclut un Makefile avec des raccourcis pratiques :

| Commande | Description |
|----------|-------------|
| `make docker-build` | Construire l'image Docker |
| `make docker-up` | Démarrer les services |
| `make docker-down` | Arrêter les services |
| `make docker-logs` | Voir les logs de l'application |
| `make docker-shell` | Ouvrir un shell dans le conteneur |
| `make docker-ps` | Voir l'état des services |
| `make docker-rebuild` | Reconstruire et redémarrer |
| `make docker-clean` | Nettoyer les ressources Docker |
| `make docker-test` | Démarrer pour les tests (SQLite) |

### Commandes avancées

```bash
# Reconstruire sans cache
docker-compose build --no-cache

# Mettre à jour les images
docker-compose pull && docker-compose up -d

# Exécuter une commande dans le conteneur
docker-compose exec app python -c "from app import app; print('OK')"

# Sauvegarder les volumes
docker run --rm --volumes-from leviia-schedule-app -v $(pwd):/backup busybox tar cvf /backup/backup.tar /app/data /app/logs

# Restaurer les volumes
docker run --rm --volumes-from leviia-schedule-app -v $(pwd):/backup busybox tar xvf /backup/backup.tar -C /
```

---

## 🔍 **Vérification du Déploiement**

### Vérifier que les services sont démarrés

```bash
# Voir l'état des services
docker-compose ps

# Résultat attendu:
#      Name                     Command                  State           Ports
# ---------------------------------------------------------------------------------------
#   leviia-schedule-app   /app/entrypoint.sh gunicorn ...   Up (healthy)   0.0.0.0:5000->5000/tcp
#   leviia-schedule-db    docker-entrypoint.sh postgres    Up (healthy)   0.0.0.0:5432->5432/tcp
```

### Vérifier les logs

```bash
# Voir les logs de l'application
docker-compose logs app

# Voir les logs en temps réel
docker-compose logs -f app

# Voir les logs de la base de données
docker-compose logs db
```

### Tester la connexion

```bash
# Tester la connexion à l'application
curl -v http://localhost:5000

# Tester la connexion à la base de données (si PostgreSQL)
docker-compose exec db psql -U leviia -d leviia -c "SELECT 1;"
```

---

## 📊 **Monitoring et Maintenance**

### Statistiques des conteneurs

```bash
# Voir les statistiques en temps réel
docker stats leviia-schedule-app

# Voir l'utilisation des ressources
docker-compose top
```

### Gestion des logs

```bash
# Voir la taille des fichiers de log
docker-compose exec app du -sh /app/logs

# Tronquer les fichiers de log (si trop volumineux)
docker-compose exec app truncate -s 0 /app/logs/*.log
```

### Sauvegarde et restauration

#### Sauvegarde manuelle

```bash
# Créer une sauvegarde des volumes
docker run --rm \
  --volumes-from leviia-schedule-app \
  -v $(pwd)/backups:/backup \
  busybox \
  tar cvf /backup/leviia-backup-$(date +%Y%m%d-%H%M%S).tar \
    /app/data \
    /app/logs

# Sauvegarder la base de données PostgreSQL
docker-compose exec db pg_dump -U leviia leviia > backups/leviia-db-$(date +%Y%m%d).sql
```

#### Restauration

```bash
# Restaurer les volumes
docker run --rm \
  --volumes-from leviia-schedule-app \
  -v $(pwd)/backups:/backup \
  busybox \
  tar xvf /backup/leviia-backup-20240101.tar -C /

# Restaurer la base de données PostgreSQL
cat backups/leviia-db-20240101.sql | docker-compose exec -T db psql -U leviia leviia
```

---

## 🔧 **Dépannage**

### Problèmes courants et solutions

#### 🔴 Problème : Connection refused à la base de données

**Symptômes** :
```
OperationalError: (psycopg2.OperationalError) connection to server at "db" (172.20.0.2), port 5432 failed: Connection refused
```

**Solutions** :
1. Vérifiez que le service PostgreSQL est démarré :
   ```bash
   docker-compose ps
   ```

2. Attendez que PostgreSQL soit prêt :
   ```bash
   docker-compose logs db
   ```

3. Vérifiez l'URL de la base de données dans `.env` :
   ```bash
   echo $DATABASE_URL
   ```

4. Redémarrez les services :
   ```bash
   docker-compose down && docker-compose up -d
   ```

---

#### 🔴 Problème : Le conteneur redémarre en boucle

**Symptômes** :
```
leviia-schedule-app   /app/entrypoint.sh gunicorn ...   Restarting (10)
```

**Solutions** :
1. Voir les logs pour identifier l'erreur :
   ```bash
   docker-compose logs app
   ```

2. Tester l'import de l'application :
   ```bash
   docker-compose exec app python -c "from app import app; print('OK')"
   ```

3. Vérifiez les permissions :
   ```bash
   docker-compose exec app ls -la /app/
   ```

---

#### 🔴 Problème : Port déjà utilisé

**Symptômes** :
```
Error: Address already in use
```

**Solutions** :
1. Changez le port dans `.env` :
   ```bash
   LEVIIA_PORT=5001
   ```

2. Trouvez et arrêtez le processus utilisant le port :
   ```bash
   # Sur Linux
   sudo lsof -i :5000
   sudo kill -9 <PID>
   ```

---

#### 🔴 Problème : Problème de mémoire (Killed)

**Symptômes** :
```
Killed
```

**Solutions** :
1. Augmentez la mémoire allouée à Docker
2. Réduisez les limites dans `.env` :
   ```bash
   LEVIIA_MEMORY_LIMIT=1G
   POSTGRES_MEMORY_LIMIT=512M
   ```

3. Réduisez le nombre de workers Gunicorn :
   ```bash
   GUNICORN_WORKERS=2
   ```

---

#### 🔴 Problème : Erreur de permission sur les volumes

**Symptômes** :
```
Permission denied: /app/data
```

**Solutions** :
1. Supprimez les volumes et recréez-les :
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. Vérifiez les permissions dans le conteneur :
   ```bash
   docker-compose exec app ls -la /app/
   ```

---

## 🛡️ **Sécurité en Production**

### Checklist de sécurité

- [ ] **Clé secrète générée aléatoirement**
- [ ] **Mots de passe changés** (admin, PostgreSQL)
- [ ] **HTTPS configuré** (via reverse proxy)
- [ ] **SESSION_COOKIE_SECURE=true**
- [ ] **SESSION_COOKIE_HTTPONLY=true**
- [ ] **RATE_LIMIT_ENABLED=true**
- [ ] **WTF_CSRF_ENABLED=true**
- [ ] **Sauvegardes automatiques configurées**
- [ ] **Mises à jour régulières**

### Configuration HTTPS avec Nginx

```nginx
# /etc/nginx/sites-available/leviia
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name votre-domaine.com;
    
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Script-Name /;
    }
}
```

### Configuration HTTPS avec Traefik

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - --api.insecure=true
      - --providers.docker
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.myresolver.acme.tlschallenge=true
      - --certificatesresolvers.myresolver.acme.email=admin@votre-domaine.com
      - --certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard Traefik
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(`traefik.votre-domaine.com`)"
      - "traefik.http.routers.traefik.service=api@internal"

  app:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.leviia.rule=Host(`votre-domaine.com`)"
      - "traefik.http.routers.leviia.entrypoints=websecure"
      - "traefik.http.routers.leviia.tls.certresolver=myresolver"
```

---

## 📈 **Optimisation des Performances**

### Configuration pour la production

```bash
# Dans le fichier .env
GUNICORN_WORKERS=8
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=300
GUNICORN_LOG_LEVEL=warning

# Limites de ressources
LEVIIA_MEMORY_LIMIT=2G
POSTGRES_MEMORY_LIMIT=1G
```

### Configuration PostgreSQL optimisée

```yaml
# docker-compose.override.yml
services:
  db:
    environment:
      POSTGRES_DB: leviia
      POSTGRES_USER: leviia
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      # Optimisations
      POSTGRES_INITDB_ARGS: --encoding=UTF8 --data-checksums
    command: >
      postgres -c shared_buffers=256MB
      -c effective_cache_size=768MB
      -c work_mem=16MB
      -c maintenance_work_mem=64MB
      -c max_connections=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
```

---

## 🔄 **Mises à jour**

### Mettre à jour l'application

```bash
# Arrêter les services
docker-compose down

# Mettre à jour le code source
git pull origin main

# Reconstruire et redémarrer
docker-compose build --no-cache
docker-compose up -d
```

### Mettre à jour les images de base

```bash
# Mettre à jour PostgreSQL
docker-compose pull db
docker-compose up -d db

# Mettre à jour Redis
docker-compose pull redis
docker-compose up -d redis
```

---

## 📚 **Ressources Complémentaires**

### Documentation officielle

- [📚 Documentation complète](README.md) - Index de toute la documentation
- [🚀 Guide de Démarrage Rapide](QUICK_START.md) - Installation en 5 minutes
- [🛡️ Guide Administrateur](ADMIN_GUIDE.md) - Configuration et maintenance
- [💻 Architecture Technique](ARCHITECTURE.md) - Comprendre le fonctionnement
- [📖 Guide Utilisateur](USER_GUIDE.md) - Utilisation quotidienne

### Ressources externes

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

---

## 🤝 **Contribution**

Les contributions à ce guide sont les bienvenues ! Pour contribuer :

1. Forker le dépôt
2. Créer une branche pour vos modifications
3. Faire vos modifications
4. Ouvrir une Pull Request

---

## 📜 **Licence**

Ce document fait partie de **Leviia Schedule**, sous licence **CeCILL v2.1**. Voir [LICENSE](../../LICENSE) pour plus de détails.

---

> **💡 Besoin d'aide ?** Consultez le [Guide de Dépannage](#-dépannage) ou ouvrez une issue sur GitHub.
