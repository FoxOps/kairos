# Dockerisation de Leviia Schedule

## 📋 Table des matières

- [Introduction](#introduction)
- [Prérequis](#prérequis)
- [Structure des fichiers](#structure-des-fichiers)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Variables d'environnement](#variables-denvironnement)
  - [Configuration pour le développement](#configuration-pour-le-développement)
  - [Configuration pour la production](#configuration-pour-la-production)
    - [Production avec SQLite](#production-avec-sqlite)
    - [Production avec PostgreSQL](#production-avec-postgresql)
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
✅ **Scalabilité** : Facile à mettre à l'échelle
✅ **Gestion simplifiée** : Une seule commande pour démarrer tous les services

---

## 📁 Structure des fichiers

```
leviia-schedule/
├── docker/                          # ⭐ Tous les fichiers Docker
│   ├── Dockerfile                  # Image Docker (multi-stage)
│   ├── docker-compose.yml          # Configuration de base commune
│   ├── docker-compose.dev.yml      # Développement
│   ├── docker-compose.prod.sqlite.yml   # Production avec SQLite
│   ├── docker-compose.prod.postgres.yml # Production avec PostgreSQL
│   ├── Makefile.docker             # Commandes utiles
│   └── .dockerignore                # Exclusion des fichiers inutiles
│
├── docs/
│   └── docker.md                   # Cette documentation
│
└── ...                            # Autres fichiers du projet
```

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

**Méthode recommandée (sécurisée) :**

```bash
# Créer un fichier .env à partir de l'exemple
cp .env.example .env

# Générer une clé secrète et un mot de passe admin sécurisés
# Puis éditer le fichier pour remplacer les valeurs par défaut
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ADMIN_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))")

# Utiliser sed pour remplacer les valeurs dans le fichier .env
# (cette méthode évite d'ajouter des doublons)
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
sed -i "s/^DEFAULT_ADMIN_PASSWORD=.*/DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD/" .env
sed -i "s/^FLASK_ENV=.*/FLASK_ENV=production/" .env

# Vérifier et modifier manuellement si nécessaire
nano .env
```

**Méthode alternative (éditer manuellement) :**

```bash
# Créer un fichier .env
cp .env.example .env

# Générer une clé secrète (à copier-coller dans le fichier)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Générer un mot de passe admin sécurisé (à copier-coller dans le fichier)
python -c "import secrets; print('DEFAULT_ADMIN_PASSWORD=' + secrets.token_urlsafe(16))"

# Éditer le fichier .env et remplacer les valeurs par défaut
nano .env
```

⚠️ **Important** : Ne jamais utiliser `>>` pour ajouter des variables au fichier `.env` existant, car cela créerait des doublons. Toujours **remplacer** les valeurs existantes.

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

#### Base de données (PostgreSQL)

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
| `SESSION_COOKIE_SAMESITE` | Politique SameSite | Lax | ✅ Production |
| `RATE_LIMIT_ENABLED` | Activer le rate limiting | true | ❌ |
| `WTF_CSRF_ENABLED` | Activer la protection CSRF | true | ✅ Production |

#### Données par défaut

| Variable | Description | Valeur par défaut | Requis |
|----------|-------------|-------------------|--------|
| `DEFAULT_ADMIN_EMAIL` | Email de l'admin | admin@leviia.local | ❌ |
| `DEFAULT_ADMIN_PASSWORD` | Mot de passe de l'admin | admin123 | ✅ Production |
| `DEFAULT_GROUP_NAME` | Nom du groupe par défaut | Defaut | ❌ |

### Configuration pour le développement

Le fichier `docker/docker-compose.dev.yml` configure :

- Mode debug activé
- Affichage des requêtes SQL
- Utilisation de SQLite pour simplifier le développement
- Reloader Flask activé
- Rate limiting désactivé

Pour démarrer :

```bash
make -f docker/Makefile.docker up-dev
```

Ou avec docker compose directement :

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

### Configuration pour la production

Deux options sont disponibles pour la production :

#### Production avec SQLite

**⚠️ Attention** : SQLite n'est pas recommandé pour la production avec plusieurs workers Gunicorn. Utilisez cette option uniquement pour des environnements avec une charge légère ou un seul worker.

Le fichier `docker/docker-compose.prod.sqlite.yml` configure :
- Gunicorn avec 1 worker (pour éviter les problèmes de verrouillage SQLite)
- SQLite comme base de données
- Persistance des données dans `./data/`

Pour démarrer :

```bash
make -f docker/Makefile.docker up-prod-sqlite
```

Ou avec docker compose :

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.sqlite.yml up -d
```

#### Production avec PostgreSQL

**✅ Recommandé** : PostgreSQL est la solution idéale pour la production, surtout avec plusieurs workers.

Le fichier `docker/docker-compose.prod.postgres.yml` configure :
- Gunicorn avec 4 workers et 2 threads par worker
- PostgreSQL comme base de données
- Redis pour le cache
- Persistance des données PostgreSQL et Redis

Pour démarrer :

```bash
make -f docker/Makefile.docker up-prod-pg
```

Ou avec docker compose :

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.postgres.yml up -d
```

---

## 🎯 Commandes Docker

### Commandes de base

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker build` | Construire l'image Docker |
| `make -f docker/Makefile.docker up-dev` | Démarrer en mode développement |
| `make -f docker/Makefile.docker down-dev` | Arrêter le développement |
| `make -f docker/Makefile.docker up-prod-pg` | Démarrer en production (PostgreSQL) |
| `make -f docker/Makefile.docker up-prod-sqlite` | Démarrer en production (SQLite) |
| `make -f docker/Makefile.docker down-prod-pg` | Arrêter la production (PostgreSQL) |
| `make -f docker/Makefile.docker down-prod-sqlite` | Arrêter la production (SQLite) |

### Commandes de service

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker logs` | Afficher les logs |
| `make -f docker/Makefile.docker logs-web` | Afficher les logs du service web |
| `make -f docker/Makefile.docker shell` | Ouvrir un shell dans le conteneur |
| `make -f docker/Makefile.docker bash` | Ouvrir un bash dans le conteneur |
| `make -f docker/Makefile.docker ps` | Lister les conteneurs |

### Commandes de base de données (PostgreSQL)

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker db-shell-pg` | Ouvrir un shell PostgreSQL |
| `make -f docker/Makefile.docker db-backup-pg` | Créer une sauvegarde |
| `make -f docker/Makefile.docker db-restore-pg FILE=backup.sql` | Restaurer une sauvegarde |

### Commandes de test et qualité

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker test` | Exécuter les tests |
| `make -f docker/Makefile.docker lint` | Exécuter le linting |
| `make -f docker/Makefile.docker quality` | Exécuter toutes les vérifications |

### Commandes avancées

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker rebuild` | Reconstruire et redémarrer (dev) |
| `make -f docker/Makefile.docker rebuild-prod-pg` | Reconstruire et redémarrer (prod PostgreSQL) |
| `make -f docker/Makefile.docker rebuild-prod-sqlite` | Reconstruire et redémarrer (prod SQLite) |
| `make -f docker/Makefile.docker clean` | Nettoyer les ressources inutilisées |

---

## 🏗️ Architecture

### Schéma des services (Production avec PostgreSQL)

```
┌─────────────────────────────────────────────────────────────┐
│                        Application Web                         │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────┐  │
│  │   Gunicorn   │    │   Flask     │    │  Static Files     │  │
│  │  (4 workers) │    │  (Dev)      │    │  (CSS, JS, etc.)   │  │
│  └─────────────┘    └─────────────┘    └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL     │   │     Redis       │
│   (Production)   │   │   (Cache)       │
└─────────────────┘   └─────────────────┘
```

### Schéma des services (Production avec SQLite)

```
┌─────────────────────────────────────────────────────────────┐
│                        Application Web                         │
│  ┌─────────────┐    ┌───────────────────┐                  │
│  │   Gunicorn   │    │  Static Files     │                  │
│  │  (1 worker)  │    │  (CSS, JS, etc.)   │                  │
│  └─────────────┘    └───────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   SQLite         │
│   (Fichier DB)   │
└─────────────────┘
```

### Ports utilisés

| Service | Port interne | Port externe | Description |
|---------|--------------|--------------|-------------|
| Web | 5000 | 5000 | Application Flask/Gunicorn |
| PostgreSQL | 5432 | 5432 | Base de données (uniquement avec PostgreSQL) |
| Redis | 6379 | 6379 | Cache (uniquement avec PostgreSQL) |

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
   - Le reverse proxy (Nginx, Traefik, etc.) doit être configuré séparément
   - Configurer `PREFERRED_URL_SCHEME=https`
   - Configurer `SESSION_COOKIE_SECURE=true`

4. **Base de données** : 
   - **PostgreSQL recommandé** pour la production avec plusieurs workers
   - **SQLite** uniquement pour des environnements légers ou un seul worker
   - Configurer des sauvegardes automatiques pour PostgreSQL

5. **Réseau** :
   - Limiter l'accès aux ports de la base de données
   - Utiliser des réseaux Docker dédiés
   - Ne pas exposer les ports de PostgreSQL et Redis en production

6. **Mises à jour** :
   - Garder Docker et les images à jour
   - Mettre à jour régulièrement les dépendances

---

## 🐛 Dépannage

### Problèmes courants

#### 1. Erreur de permission sur les volumes

**Symptôme** : Erreur de permission lors de l'écriture dans les volumes

**Solution** :
```bash
# Donner les permissions à l'utilisateur courant
sudo chown -R $USER:$USER .

# Créer les répertoires nécessaires
mkdir -p data logs
chmod -R 755 data logs
```

#### 2. La base de données PostgreSQL ne se connecte pas

**Symptôme** : Erreur de connexion à PostgreSQL

**Solution** :
- Vérifier que le service `db` est démarré : `docker compose ps`
- Vérifier les logs : `docker compose logs db`
- Attendre que PostgreSQL soit prêt (healthcheck)
- Vérifier les variables d'environnement dans `.env`
- Vérifier que le mot de passe PostgreSQL est correct

#### 3. L'application ne démarre pas

**Symptôme** : Le conteneur web crash au démarrage

**Solution** :
- Vérifier les logs : `docker compose logs web`
- Vérifier que toutes les dépendances sont installées
- Vérifier la configuration de la base de données
- Vérifier que le fichier `.env` contient les bonnes variables

#### 4. Problème de port déjà utilisé

**Symptôme** : Erreur "port already in use"

**Solution** :
- Trouver le processus utilisant le port : `sudo lsof -i :5000`
- Arrêter le processus : `kill <PID>`
- Ou changer le port dans `docker/docker-compose.yml`

#### 5. Problèmes avec SQLite en production

**Symptôme** : Erreurs "database is locked" avec SQLite

**Solution** :
- Utiliser PostgreSQL à la place
- Ou limiter à 1 worker Gunicorn (déjà configuré dans `docker/docker-compose.prod.sqlite.yml`)
- Vérifier que le volume `../data` est correctement monté

### Commandes de diagnostic

```bash
# Vérifier l'état des services
docker compose -f docker/docker-compose.yml ps

# Vérifier les logs
docker compose -f docker/docker-compose.yml logs

# Vérifier les logs d'un service spécifique
docker compose -f docker/docker-compose.yml logs web
docker compose -f docker/docker-compose.yml logs db

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
   make -f docker/Makefile.docker down-prod-pg  # ou down-prod-sqlite
   ```

2. Mettre à jour le code :
   ```bash
   git pull origin main
   ```

3. Reconstruire et redémarrer :
   ```bash
   make -f docker/Makefile.docker rebuild-prod-pg  # ou rebuild-prod-sqlite
   ```

### Mettre à jour les dépendances

1. Mettre à jour `requirements.txt` :
   ```bash
   # Dans le conteneur
   make -f docker/Makefile.docker shell
   pip freeze > requirements.txt
   exit
   ```

2. Reconstruire l'image :
   ```bash
   make -f docker/Makefile.docker rebuild-prod-pg  # ou rebuild-prod-sqlite
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

Ce projet est sous licence MIT. Voir le fichier [LICENSE](../LICENSE) pour plus de détails.

---

*Documentation générée pour Leviia Schedule - Dockerisation*
