# Dockerisation de Leviia Schedule

## 📋 Table des matières

- [Introduction](#introduction)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Variables d'environnement](#variables-denvironnement)
  - [Configuration pour le développement](#configuration-pour-le-développement)
  - [Configuration pour la production](#configuration-pour-la-production)
- [Commandes Docker](#commandes-docker)
- [Architecture](#architecture)
- [Sécurité](#sécurité)
- [Dépannage](#dépannage)
- [Mises à jour](#mises-à-jour)

---

## 🚀 Introduction

Ce guide explique comment déployer **Leviia Schedule** avec Docker. L'application est conçue pour fonctionner dans des conteneurs Docker, ce qui simplifie grandement le déploiement et la gestion des dépendances.

### Avantages de la dockerisation

✅ **Isolation** : Chaque service (web, base de données, cache) fonctionne dans son propre conteneur
✅ **Portabilité** : Déploiement identique sur tous les environnements (dev, staging, prod)
✅ **Reproductibilité** : Pas de problèmes de "ça marche chez moi"
✅ **Scalabilité** : Facile à mettre à l'échelle avec Kubernetes ou Docker Swarm
✅ **Gestion simplifiée** : Une seule commande pour démarrer tous les services

---

## 📦 Prérequis

Avant de commencer, assurez-vous d'avoir installé :

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 ou supérieure)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 1.29 ou supérieure)
- Git (pour cloner le dépôt)

Vérifiez les installations :

```bash
# Vérifier Docker
docker --version

# Vérifier Docker Compose
docker compose version
```

---

## 💻 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

### 2. Configurer l'environnement

#### Pour le développement :

```bash
# Créer un fichier .env pour le développement
cp .env.example .env

# Modifier le fichier .env selon vos besoins
nano .env
```

#### Pour la production :

```bash
# Créer un fichier .env sécurisé
cp .env.example .env

# Générer une clé secrète
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env

# Générer un mot de passe admin sécurisé
python -c "import secrets; print('DEFAULT_ADMIN_PASSWORD=' + secrets.token_urlsafe(16))" >> .env

# Modifier le fichier .env
nano .env
```

### 3. Construire et démarrer les conteneurs

#### Développement :

```bash
# Démarrer tous les services en mode développement
make -f Makefile.docker up-dev

# Ou avec docker compose directement
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

#### Production :

```bash
# Démarrer tous les services en mode production
make -f Makefile.docker up-prod

# Ou avec docker compose directement
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Accéder à l'application

- **Développement** : http://localhost:5000
- **Production** : https://leviia.example.com (à configurer)

Identifiants par défaut :
- Email : `admin@leviia.local`
- Mot de passe : `admin123` (à changer immédiatement en production !)

---

## ⚙️ Configuration

### Variables d'environnement

Le projet utilise les variables d'environnement pour la configuration. Voici les principales :

#### Configuration de base

| Variable | Description | Valeur par défaut | Requis |
|----------|-------------|-------------------|--------|
| `SECRET_KEY` | Clé secrète Flask | Générée aléatoirement | ✅ Production |
| `FLASK_ENV` | Environnement (development/production) | development | ❌ |
| `DATABASE_URL` | URL de la base de données | sqlite:///app.db | ❌ |

#### Base de données

| Variable | Description | Valeur par défaut | Requis |
|----------|-------------|-------------------|--------|
| `POSTGRES_DB` | Nom de la base PostgreSQL | leviia | ❌ |
| `POSTGRES_USER` | Utilisateur PostgreSQL | leviia | ❌ |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | leviia-pass | ❌ |

#### Sécurité

| Variable | Description | Valeur par défaut | Requis |
|----------|-------------|-------------------|--------|
| `SESSION_COOKIE_SECURE` | Cookies sécurisés (HTTPS) | true | ✅ Production |
| `SESSION_COOKIE_HTTPONLY` | Cookies HTTP-only | true | ✅ Production |
| `RATE_LIMIT_ENABLED` | Activer le rate limiting | true | ❌ |
| `WTF_CSRF_ENABLED` | Activer la protection CSRF | true | ✅ Production |

#### Données par défaut

| Variable | Description | Valeur par défaut | Requis |
|----------|-------------|-------------------|--------|
| `DEFAULT_ADMIN_EMAIL` | Email de l'admin | admin@leviia.local | ❌ |
| `DEFAULT_ADMIN_PASSWORD` | Mot de passe de l'admin | admin123 | ✅ Production |
| `DEFAULT_GROUP_NAME` | Nom du groupe par défaut | Defaut | ❌ |

### Configuration pour le développement

Le fichier `docker-compose.dev.yml` configure :

- Mode debug activé
- Affichage des requêtes SQL
- Utilisation de SQLite pour simplifier le développement
- Reloader Flask activé
- Rate limiting désactivé

Pour démarrer :

```bash
make -f Makefile.docker up-dev
```

### Configuration pour la production

Le fichier `docker-compose.prod.yml` configure :

- Mode production
- Utilisation de PostgreSQL
- Gunicorn comme serveur WSGI (4 workers, 2 threads)
- Cache Redis activé
- Sécurité maximale (HTTPS, cookies sécurisés, etc.)
- Reverse proxy Nginx (optionnel)
- Backup automatique de la base de données (optionnel)

Pour démarrer :

```bash
make -f Makefile.docker up-prod
```

---

## 🎯 Commandes Docker

### Commandes de base

| Commande | Description |
|----------|-------------|
| `make -f Makefile.docker build` | Construire l'image Docker |
| `make -f Makefile.docker up` | Démarrer les services |
| `make -f Makefile.docker up-dev` | Démarrer en mode développement |
| `make -f Makefile.docker up-prod` | Démarrer en mode production |
| `make -f Makefile.docker down` | Arrêter les services |
| `make -f Makefile.docker restart` | Redémarrer les services |
| `make -f Makefile.docker logs` | Afficher les logs |
| `make -f Makefile.docker shell` | Ouvrir un shell dans le conteneur |

### Commandes de base de données

| Commande | Description |
|----------|-------------|
| `make -f Makefile.docker db-shell` | Ouvrir un shell PostgreSQL |
| `make -f Makefile.docker db-backup` | Créer une sauvegarde |
| `make -f Makefile.docker db-restore FILE=backup.sql` | Restaurer une sauvegarde |

### Commandes de test et qualité

| Commande | Description |
|----------|-------------|
| `make -f Makefile.docker test` | Exécuter les tests |
| `make -f Makefile.docker lint` | Exécuter le linting |
| `make -f Makefile.docker quality` | Exécuter toutes les vérifications |

### Commandes avancées

| Commande | Description |
|----------|-------------|
| `make -f Makefile.docker rebuild` | Reconstruire et redémarrer |
| `make -f Makefile.docker migrate` | Appliquer les migrations |
| `make -f Makefile.docker init-db` | Initialiser la base de données |
| `make -f Makefile.docker clean` | Nettoyer les ressources inutilisées |

---

## 🏗️ Architecture

### Schéma des services

```
┌─────────────────────────────────────────────────────────────┐
│                        Reverse Proxy (Nginx)                   │
│                         (Optionnel en production)             │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                        Application Web                         │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────┐  │
│  │   Flask     │    │  Gunicorn   │    │  Static Files     │  │
│  │  (Dev)      │    │  (Prod)     │    │  (CSS, JS, etc.)   │  │
│  └─────────────┘    └─────────────┘    └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL     │   │     Redis       │   │   Volume        │
│   (Production)   │   │   (Cache)       │   │   (Données)     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Ports utilisés

| Service | Port interne | Port externe | Description |
|---------|--------------|--------------|-------------|
| Web | 5000 | 5000 | Application Flask/Gunicorn |
| PostgreSQL | 5432 | 5432 | Base de données |
| Redis | 6379 | 6379 | Cache |
| Nginx | 80/443 | 80/443 | Reverse proxy (optionnel) |

---

## 🔒 Sécurité

### Bonnes pratiques pour la production

1. **Clé secrète** : Toujours utiliser une clé secrète forte et unique
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Mot de passe admin** : Toujours changer le mot de passe par défaut
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(16))"
   ```

3. **HTTPS** : Toujours utiliser HTTPS en production
   - Configurer Nginx avec des certificats SSL valides
   - Utiliser Let's Encrypt pour des certificats gratuits

4. **Base de données** : 
   - Ne jamais utiliser SQLite en production avec plusieurs workers
   - Utiliser PostgreSQL ou MariaDB
   - Configurer des sauvegardes automatiques

5. **Réseau** :
   - Limiter l'accès aux ports de la base de données
   - Utiliser des réseaux Docker dédiés

6. **Mises à jour** :
   - Garder Docker et les images à jour
   - Mettre à jour régulièrement les dépendances

### Configuration SSL avec Let's Encrypt

1. Installer Certbot :
   ```bash
   sudo apt-get install certbot
   ```

2. Obtenir un certificat :
   ```bash
   sudo certbot certonly --standalone -d leviia.example.com
   ```

3. Copier les certificats dans le dossier `certs/` :
   ```bash
   sudo cp /etc/letsencrypt/live/leviia.example.com/fullchain.pem certs/leviia.crt
   sudo cp /etc/letsencrypt/live/leviia.example.com/privkey.pem certs/leviia.key
   sudo chmod 644 certs/leviia.key
   ```

4. Configurer Nginx pour utiliser les certificats (déjà configuré dans `nginx/conf.d/leviia.conf`)

---

## 🐛 Dépannage

### Problèmes courants

#### 1. Erreur de permission sur les volumes

**Symptôme** : Erreur de permission lors de l'écriture dans les volumes

**Solution** :
```bash
# Donner les permissions à l'utilisateur courant
sudo chown -R $USER:$USER .

# Ou démarrer avec l'utilisateur root (non recommandé)
docker compose -f docker-compose.yml up -d --user root
```

#### 2. La base de données ne se connecte pas

**Symptôme** : Erreur de connexion à PostgreSQL

**Solution** :
- Vérifier que le service `db` est démarré : `docker compose ps`
- Vérifier les logs : `docker compose logs db`
- Attendre que PostgreSQL soit prêt (healthcheck)
- Vérifier les variables d'environnement dans `.env`

#### 3. L'application ne démarre pas

**Symptôme** : Le conteneur web crash au démarrage

**Solution** :
- Vérifier les logs : `docker compose logs web`
- Vérifier que toutes les dépendances sont installées
- Vérifier la configuration de la base de données

#### 4. Problème de port déjà utilisé

**Symptôme** : Erreur "port already in use"

**Solution** :
- Trouver le processus utilisant le port : `sudo lsof -i :5000`
- Arrêter le processus : `kill <PID>`
- Ou changer le port dans `docker-compose.yml`

### Commandes de diagnostic

```bash
# Vérifier l'état des services
docker compose ps

# Vérifier les logs
docker compose logs

# Vérifier les ressources
docker stats

# Inspecter un conteneur
docker inspect leviia-schedule-web

# Vérifier les volumes
docker volume ls

# Vérifier les réseaux
docker network ls
```

---

## 🔄 Mises à jour

### Mettre à jour l'application

1. Arrêter les services :
   ```bash
   make -f Makefile.docker down
   ```

2. Mettre à jour le code :
   ```bash
   git pull origin main
   ```

3. Reconstruire et redémarrer :
   ```bash
   make -f Makefile.docker rebuild
   ```

### Mettre à jour les dépendances

1. Mettre à jour `requirements.txt` :
   ```bash
   # Dans le conteneur
   make -f Makefile.docker shell
   pip freeze > requirements.txt
   exit
   ```

2. Reconstruire l'image :
   ```bash
   make -f Makefile.docker rebuild
   ```

---

## 📚 Documentation supplémentaire

- [Documentation officielle de Docker](https://docs.docker.com/)
- [Documentation de Docker Compose](https://docs.docker.com/compose/)
- [Documentation de Flask](https://flask.palletsprojects.com/)
- [Documentation de PostgreSQL](https://www.postgresql.org/docs/)

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forker le dépôt
2. Créer une branche (`git checkout -b feature/ma-fonctionnalité`)
3. Commiter vos changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Pousser vers la branche (`git push origin feature/ma-fonctionnalité`)
5. Ouvrir une Pull Request

---

## 📜 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

*Documentation générée pour Leviia Schedule - Dockerisation*
