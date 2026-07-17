# 🏢 Guide de Déploiement - Leviia Schedule

> **Version** : 1.0  
> **Derniere mise à jour** : Juin 2026  
> **Statut** : Documentation pour la production

> ⚠️ **Méthode recommandée : Docker.** Ce guide couvre le déploiement
> **sans Docker** (Gunicorn/uWSGI bare-metal) - une alternative pour les
> cas où Docker n'est pas disponible ou pas souhaité. Pour la méthode
> principale (image publiée sur le registry), voir
> [`docker.md`](docker.md).

---

## 📁 Sommaire

1. [Prérequis](#1-prérequis)
2. [Préparation de l'environnement](#2-préparation-de-lenvironnement)
3. [Configuration](#3-configuration)
4. [Déploiement avec Gunicorn](#4-déploiement-avec-gunicorn)
5. [Déploiement avec uWSGI](#5-déploiement-avec-uwsgi)
6. [Déploiement avec Docker](#6-déploiement-avec-docker)
7. [Configuration de la base de données](#7-configuration-de-la-base-de-données)
8. [Configuration des variables d'environnement](#8-configuration-des-variables-denvironnement)
9. [Sécurité en production](#9-sécurité-en-production)
10. [Maintenance](#10-maintenance)
11. [Dépannage](#11-dépannage)

---

## 1. 📁 Prérequis

### 1.1 Système d'exploitation
- Linux (Ubuntu 20.04/22.04, Debian 11/12, CentOS 8+)
- macOS (10.15+)
- Windows (10/11 avec WSL2 recommandé)

### 1.2 Logiciels requis
| Logiciel | Version minimale | Description |
|----------|------------------|-------------|
| Python | 3.8+ | Langage de programmation |
| pip | 26.1+ | Gestionnaire de paquets Python |
| Git | 2.20+ | Contrôle de version |
| PostgreSQL | 12+ | Base de données (recommandé) |
| SQLite | 3.31+ | Base de données embarquée (pour le développement) |
| Redis | 6.0+ | Cache (optionnel) |

### 1.3 Ressources matérielles
- **CPU** : 2 cœurs minimum (4 recommandés)
- **RAM** : 2 Go minimum (4 Go recommandés)
- **Stockage** : 10 Go minimum (SSD recommandé)

---

## 2. 📁 Préparation de l'environnement

### 2.1 Cloner le dépôt
```bash
# Cloner le dépôt GitHub
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule

# Basculer sur la dernière version stable
git checkout main
```

### 2.2 Créer un environnement virtuel
```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur Linux/macOS
source venv/bin/activate

# Sur Windows
venv\Scripts\activate
```

### 2.3 Installer les dépendances
```bash
# Installer les dépendances de base
pip install --upgrade pip
pip install -r requirements.txt

# Installer les dépendances optionnelles (PostgreSQL, Redis)
pip install psycopg[binary] redis
```

---

## 3. 📁 Configuration

### 3.1 Fichier .env
Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```bash
# Configuration de base
FLASK_ENV=production
SECRET_KEY=votre_cle_secrete_ici_generée_avec_secrets_token_urlsafe_32

# Base de données (choisir une option)
# Option 1: SQLite (pour le développement)
DATABASE_URL=sqlite:///app.db

# Option 2: PostgreSQL (recommandé pour la production)
# DATABASE_URL=postgresql://user:password@localhost:5432/leviia

# Option 3: MySQL/MariaDB
# DATABASE_URL=mysql://user:password@localhost:3306/leviia

# Configuration de sécurité
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True
PREFERRED_URL_SCHEME=https
WTF_CSRF_ENABLED=True

# Configuration du logging
LOG_LEVEL=WARNING
LOG_DIR=./logs

# Configuration des performances
RATE_LIMIT_ENABLED=True
COMPRESS_ENABLED=True

# Configuration de l'authentification
# LOGIN_DISABLED=False  # Cette option a été supprimée pour la sécurité
```

### 3.2 Générer une clé secrète
```bash
# Utiliser Python pour générer une clé sécurisée
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. 📁 Déploiement avec Gunicorn

### 4.1 Installation
```bash
pip install gunicorn
```

### 4.2 Configuration de base
```bash
# Démarrer avec Gunicorn (4 workers, port 5000)
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### 4.3 Configuration recommandée pour la production
```bash
# Démarrer avec plus de workers et timeout plus long
gunicorn \
  -w 8 \
  -b 0.0.0.0:5000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --graceful-timeout 30 \
  run:app
```

### 4.4 Configuration avec fichier de configuration
Créez un fichier `gunicorn.conf.py` :

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

Puis démarrez avec :
```bash
gunicorn -c gunicorn.conf.py run:app
```

### 4.5 Utiliser un socket Unix
```bash
gunicorn -w 8 -b unix:/tmp/leviia.sock run:app
```

---

## 5. 📁 Déploiement avec uWSGI

### 5.1 Installation
```bash
pip install uwsgi
```

### 5.2 Configuration de base
Créez un fichier `uwsgi.ini` :

```ini
[uwsgi]
module = run:app
workers = 8
threads = 4
master = true
chmod-socket = 660
vacuum = true
die-on-term = true

# Configuration du socket
socket = /tmp/leviia_uwsgi.sock
chown-socket = www-data:www-data
chmod-socket = 660

# Configuration HTTP (optionnelle)
# http = 0.0.0.0:5000

# Configuration des processus
max-requests = 1000
max-worker-lifetime = 3600
reload-mercy = 30

# Configuration de la mémoire
buffer-size = 32768
```

### 5.3 Démarrer uWSGI
```bash
uwsgi --ini uwsgi.ini
```

---

## 6. 📁 Déploiement avec Docker

**Méthode recommandée pour l'ensemble du projet** (voir l'avertissement
en tête de ce guide) - le vrai `Dockerfile`/`docker-compose.yml` vivent
sous `docker/`, avec l'image publiée sur un registry par la CI. Ce guide
couvre spécifiquement le déploiement bare-metal (Gunicorn/uWSGI), donc
n'entretient pas de copie séparée de cette configuration ici.

👉 Voir [`docker.md`](docker.md) pour le détail complet : tirer l'image
du registry (méthode recommandée), ou la construire soi-même/passer par
Docker Compose (alternative dev).

---

## 7. 📁 Configuration de la base de données

### 7.1 SQLite (pour le développement)
```bash
# SQLite est configuré par défaut
# La base de données sera créée automatiquement au premier démarrage

# Pour initialiser manuellement
python run.py
```

### 7.2 PostgreSQL (recommandé pour la production)

#### 7.2.1 Installation
```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Sur CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 7.2.2 Configuration
```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Créer un utilisateur et une base de données
CREATE USER leviia_user WITH PASSWORD 'votre_mot_de_passe';
CREATE DATABASE leviia OWNER leviia_user;
GRANT ALL PRIVILEGES ON DATABASE leviia TO leviia_user;
\q
```

#### 7.2.3 Configuration dans Leviia
```bash
# Dans votre fichier .env
DATABASE_URL=postgresql://leviia_user:votre_mot_de_passe@localhost:5432/leviia
```

### 7.3 MySQL/MariaDB

Leviia Schedule se connecte à tout serveur MySQL/MariaDB via SQLAlchemy +
`PyMySQL` — un driver 100% pur Python, déjà inclus dans `requirements.txt`.
Aucune bibliothèque système (`libmariadb-dev`/`libmysqlclient-dev`) n'est
requise, ni à l'installation ni à l'exécution, ni sur l'hôte ni dans l'image
Docker.

#### 7.3.1 Cas recommandé : serveur MySQL/MariaDB externe

Si vous disposez déjà d'un serveur MySQL/MariaDB géré ailleurs (hébergeur
managé, cluster existant, autre VM), il suffit de créer la base et
l'utilisateur applicatif **sur ce serveur** (pas sur la machine qui exécute
Leviia Schedule), puis de pointer `DATABASE_URL` dessus :

```bash
# Sur le serveur MySQL/MariaDB externe (exécuté là-bas, pas ici)
CREATE DATABASE leviia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'leviia_user'@'%' IDENTIFIED BY 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON leviia.* TO 'leviia_user'@'%';
FLUSH PRIVILEGES;
```

```bash
# Dans le .env de Leviia Schedule (cette machine - aucun serveur MySQL
# local requis, ni sur l'hôte ni dans l'image Docker)
DATABASE_URL=mariadb://leviia_user:votre_mot_de_passe@mysql-externe.example.com:3306/leviia

# Recommandé pour un serveur externe : les connexions inactives peuvent
# être coupées côté serveur (wait_timeout MySQL par défaut ~8h, souvent
# plus court sur une offre managée) - pool_pre_ping revalide la connexion
# avant chaque emprunt au pool, pool_recycle la referme proactivement.
SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": true, "pool_recycle": 3600}
```

#### 7.3.2 Alternative : serveur MySQL/MariaDB local (dev/test)

Pour héberger MariaDB directement sur la même machine (typiquement en
développement) :

```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install mariadb-server
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Sécuriser MySQL
sudo mysql_secure_installation
```

```bash
# Se connecter à MySQL
sudo mysql -u root

# Créer un utilisateur et une base de données
CREATE USER 'leviia_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
CREATE DATABASE leviia;
GRANT ALL PRIVILEGES ON leviia.* TO 'leviia_user'@'localhost';
FLUSH PRIVILEGES;
quit
```

```bash
# Dans votre fichier .env
DATABASE_URL=mysql://leviia_user:votre_mot_de_passe@localhost:3306/leviia
```

Voir aussi
[`DEPLOYMENT_ADVANCED.md`](DEPLOYMENT_ADVANCED.md#-ajouter-mysqlmariadb-devtest-local)
pour un overlay docker-compose optionnel équivalent à ce cas local.

---

## 8. 📁 Configuration des variables d'environnement

### 8.1 Variables essentielles
| Variable | Description | Valeur par défaut | Recommandation |
|----------|-------------|----------------|----------------|
| `FLASK_ENV` | Environnement d'exécution | `default` | `production` |
| `SECRET_KEY` | Clé secrète Flask | Aléatoire | **OBLIGATOIRE** |
| `DATABASE_URL` | URL de la base de données | `sqlite:///app.db` | PostgreSQL |
| `LOG_LEVEL` | Niveau de logging | `INFO` | `WARNING` |
| `RATE_LIMIT_ENABLED` | Activer le rate limiting | `True` | `True` |
| `COMPRESS_ENABLED` | Activer la compression | `True` | `True` |

### 8.2 Variables de sécurité
| Variable | Description | Valeur par défaut | Recommandation |
|----------|-------------|----------------|----------------|
| `SESSION_COOKIE_SECURE` | Cookies HTTPS uniquement | `True` | `True` |
| `SESSION_COOKIE_HTTPONLY` | Cookies non accessibles via JS | `True` | `True` |
| `SESSION_COOKIE_SAMESITE` | Politique SameSite | `Lax` | `Lax` ou `Strict` |
| `REMEMBER_COOKIE_SECURE` | Remember me HTTPS | `True` | `True` |
| `WTF_CSRF_ENABLED` | Activer CSRF | `True` | `True` |
| `PREFERRED_URL_SCHEME` | Schéma URL | `https` | `https` |

### 8.3 Variables de performance
| Variable | Description | Valeur par défaut | Recommandation |
|----------|-------------|----------------|----------------|
| `DATABASE_POOL_SIZE` | Taille du pool de connexions | `5` (SQLite), `10` (PostgreSQL) | 10-20 |
| `DATABASE_MAX_OVERFLOW` | Overflow du pool | `10` (SQLite), `20` (PostgreSQL) | 20-40 |
| `DATABASE_POOL_RECYCLE` | Recyclage des connexions (s) | `3600` | 3600 |

---

## 9. 📁 Sécurité en production

### 9.1 Bonnes pratiques
- â03 Utiliser **toujours** HTTPS en production
- â03 Ne **jamais** exposer l'application sans authentification
- â03 Maintenir les dépendances à jour (`pip install --upgrade -r requirements.txt`)
- â03 Utiliser un WAF (Web Application Firewall) comme Cloudflare ou ModSecurity
- â03 Configurer des sauvegardes régulières de la base de données
- â03 Limiter l'accès à l'interface d'administration

### 9.2 Configuration du pare-feu
```bash
# Autoriser uniquement les ports nécessaires
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### 9.3 Configuration SSL/TLS
Utilisez **Let's Encrypt** avec Certbot pour obtenir des certificats SSL gratuits :

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir un certificat
sudo certbot --nginx -d votre-domaine.com

# Renouvellement automatique
sudo certbot renew --dry-run
```

### 9.4 Sécurité des headers HTTP
Les headers de sécurité sont déjà configurés dans l'application :
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

---

## 10. 📁 Maintenance

### 10.1 Mise à jour
```bash
# Mettre à jour l'application
git pull origin main

# Mettre à jour les dépendances
pip install --upgrade -r requirements.txt

# Redémarrer l'application
# systemctl restart leviia  # Si vous utilisez systemd
```

### 10.2 Sauvegarde
```bash
# Sauvegarder la base de données SQLite
cp app.db app.db.backup-$(date +%Y%m%d)

# Sauvegarder PostgreSQL
pg_dump leviia > leviia_backup_$(date +%Y%m%d).sql

# Sauvegarder le répertoire de configuration
cp -r .env config.py leviia_config_backup_$(date +%Y%m%d)/
```

### 10.3 Monitoring
```bash
# Voir les logs
tail -f logs/leviia-app.log

# Vérifier l'état de l'application
# Si vous utilisez systemd
systemctl status leviia

# Vérifier l'utilisation des ressources
top
h top
```

---

## 11. 📁 Dépannage

### 11.1 Problèmes courants

#### 11.1.1 "Database is locked"
**Cause** : SQLite ne supporte pas les accès concurrents.  
**Solution** : 
- Utiliser PostgreSQL pour la production
- Ou configurer le retry dans `config.py` (déjà configuré)

#### 11.1.2 "502 Bad Gateway" (Nginx)
**Cause** : Gunicorn/uWSGI ne répond pas.  
**Solution** :
```bash
# Vérifier que Gunicorn/uWSGI est en cours d'exécution
ps aux | grep gunicorn
ps aux | grep uwsgi

# Redémarrer le service
systemctl restart leviia
```

#### 11.1.3 "Connection refused" (PostgreSQL)
**Cause** : PostgreSQL n'est pas en cours d'exécution ou la configuration est incorrecte.  
**Solution** :
```bash
# Vérifier que PostgreSQL est en cours d'exécution
sudo systemctl status postgresql

# Tester la connexion
psql -U leviia_user -d leviia -h localhost
```

#### 11.1.4 "ModuleNotFoundError"
**Cause** : Les dépendances ne sont pas installées.  
**Solution** :
```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 11.2 Logs et diagnostic

#### 11.2.1 Voir les logs de l'application
```bash
# Logs de l'application
tail -f logs/leviia-app.log

# Logs des erreurs
tail -f logs/leviia-errors.log

# Logs HTTP
tail -f logs/leviia-http-errors.log
```

#### 11.2.2 Tester la connexion à la base de données
```bash
# Tester la connexion SQLite
sqlite3 app.db "SELECT COUNT(*) FROM user;"

# Tester la connexion PostgreSQL
psql -U leviia_user -d leviia -c "SELECT COUNT(*) FROM user;"
```

---

## 📁 Annexes

### A.1 Configuration systemd
Créez un fichier `/etc/systemd/system/leviia.service` :

```ini
[Unit]
Description=Leviia Schedule Application
After=network.target postgresql.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/leviia-schedule
Environment="PATH=/var/www/leviia-schedule/venv/bin"
ExecStart=/var/www/leviia-schedule/venv/bin/gunicorn -w 8 -b unix:/tmp/leviia.sock run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Puis :
```bash
# Recharger systemd
sudo systemctl daemon-reload

# Démarrer le service
sudo systemctl start leviia

# Activer au démarrage
sudo systemctl enable leviia

# Vérifier l'état
sudo systemctl status leviia
```

### A.2 Configuration Nginx
Créez un fichier `/etc/nginx/sites-available/leviia` :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/leviia.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /var/www/leviia-schedule/app/static/;
        expires 30d;
    }
}
```

Puis :
```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/leviia /etc/nginx/sites-enabled/

# Tester la configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx
```

---

## 📁 Support

Pour toute question ou problème :
- Consultez la [documentation complète](../README.md)
- Ouvrez une **Issue** sur [GitHub](https://github.com/FoxOps/leviia-schedule/issues)
- Consultez les [discussions](https://github.com/FoxOps/leviia-schedule/discussions)

---

> **⚠️ Note importante** : Ce guide suppose que vous avez une connaissance de base de l'administration système Linux. Pour un déploiement en production, il est fortement recommandé de faire appel à un administrateur système expérimenté.
