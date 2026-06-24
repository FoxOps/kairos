# Leviia Schedule - Guide Docker

> **📚 Documentation complète disponible dans [../docs/](../docs/)**

Ce guide explique comment déployer **Leviia Schedule** avec Docker et Docker Compose.

---

## 📁 Structure du dossier Docker

```
docker/
├── Dockerfile              # Configuration de l'image Docker (sans PostgreSQL)
├── docker-compose.yml      # Orchestration des services (PostgreSQL externe)
├── .dockerignore           # Fichiers à exclure du build
├── .env.docker             # Variables d'environnement par défaut
├── entrypoint.sh           # Script d'entrée du conteneur
└── README.md               # Ce guide
```

> **⚠️ IMPORTANT** : PostgreSQL est géré comme un **service externe** via docker-compose.yml 
> et n'est PAS inclus dans l'image Docker de l'application.

---

## 🚀 Démarrage Rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 ou supérieure)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 1.29 ou supérieure)
- 1 Go d'espace disque minimum
- 512 Mo de RAM minimum (1 Go recommandé)

---

## 📦 Déploiement avec PostgreSQL (Service externe)

### 1. Cloner le dépôt

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

### 2. Configurer l'environnement

Copiez le fichier d'environnement Docker :

```bash
cp docker/.env.docker docker/.env
```

Éditez le fichier `docker/.env` et modifiez au minimum ces variables :

```bash
# Clé secrète (OBLIGATOIRE: générez-en une nouvelle)
SECRET_KEY=votre-nouvelle-cle-secrete-ici

# Mot de passe admin (à changer)
DEFAULT_ADMIN_PASSWORD=votre-mot-de-passe

# Mot de passe PostgreSQL (à changer)
POSTGRES_PASSWORD=votre-mot-de-passe-postgres
```

Pour générer une clé secrète sécurisée :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Démarrer les services

```bash
# Se placer dans le dossier docker
cd docker

# Construire et démarrer tous les services (app + PostgreSQL)
docker-compose up -d
```

### 4. Vérifier le déploiement

```bash
# Voir l'état des services
docker-compose ps

# Voir les logs de l'application
docker-compose logs -f app
```

### 5. Accéder à l'application

Ouvrez votre navigateur à l'adresse : **http://localhost:5000**

Identifiants par défaut :
- Email : `admin@leviia.local` (ou celui configuré dans `DEFAULT_ADMIN_EMAIL`)
- Mot de passe : celui configuré dans `DEFAULT_ADMIN_PASSWORD`

> **⚠️ IMPORTANT** : Changez le mot de passe après la première connexion !

---

## 💾 Déploiement avec SQLite (Pour le développement ou tests)

Si vous préférez utiliser SQLite au lieu de PostgreSQL :

### 1. Modifier la configuration

Dans le fichier `docker/.env`, changez l'URL de la base de données :

```bash
# Utiliser SQLite au lieu de PostgreSQL
DATABASE_URL=sqlite:////app/data/app.db
```

### 2. Démarrer uniquement l'application

```bash
# Se placer dans le dossier docker
cd docker

# Démarrer uniquement le service app (sans PostgreSQL)
docker-compose up -d app
```

> **Note** : Avec SQLite, les données seront stockées dans le volume Docker `leviia-data`.

---

## 🛠️ Commandes Docker Utiles

### Commandes de base

> **Exécutez ces commandes depuis le dossier `docker/`**

| Commande | Description |
|----------|-------------|
| `docker-compose up -d` | Démarrer tous les services |
| `docker-compose down` | Arrêter tous les services |
| `docker-compose down -v` | Arrêter et supprimer les volumes |
| `docker-compose ps` | Voir l'état des services |
| `docker-compose logs -f` | Voir tous les logs |
| `docker-compose logs -f app` | Voir les logs de l'application |

### Commandes Makefile

Le projet inclut un Makefile avec des raccourcis pratiques (à exécuter depuis la racine) :

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

---

## 📊 Architecture Docker

### Services disponibles

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `app` | Construite localement | 5000 | Application Flask Leviia Schedule |
| `db` | postgres:15-alpine | 5432 | **Service externe** - Base de données PostgreSQL (optionnelle) |
| `redis` | redis:7-alpine | 6379 | **Service externe** - Cache Redis (optionnel) |

> **⚠️ IMPORTANT** : PostgreSQL et Redis sont des **services externes** gérés via docker-compose.yml. 
> Ils ne sont PAS inclus dans l'image Docker de l'application. L'image Docker ne contient 
> que l'application Flask et ses dépendances Python.

### Volumes persistants

| Volume | Montage | Description | Persistant |
|--------|---------|-------------|-------------|
| `leviia-data` | `/app/data` | Données de l'application (SQLite, uploads) | ✅ Oui |
| `leviia-logs` | `/app/logs` | Fichiers de log | ✅ Oui |
| `leviia-instance` | `/app/instance` | Instance Flask (SQLite si utilisé) | ✅ Oui |
| `leviia-postgres-data` | `/var/lib/postgresql/data` | Données PostgreSQL | ✅ Oui |
| `leviia-redis-data` | `/data` | Données Redis | ✅ Oui |

### Réseau Docker

- `leviia-network` : Réseau dédié pour la communication entre les services

---

## 🔧 Configuration Avancée

### Variables d'Environnement Principales

#### Configuration de l'application

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `LEVIIA_PORT` | 5000 | Port externe de l'application | Changez si 5000 est occupé |
| `FLASK_ENV` | production | Environnement Flask | `development` pour le dev |
| `FLASK_DEBUG` | false | Mode debug Flask | `true` uniquement en développement |
| `SERVER` | gunicorn | Serveur WSGI | gunicorn, flask, uwsgi |
| `SECRET_KEY` | - | **Clé secrète Flask** | **OBLIGATOIRE à changer** |

#### Configuration de la Base de Données

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `DATABASE_URL` | postgresql://... | URL de connexion | SQLite ou PostgreSQL |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | false | Suivi des modifications | Laissez à false |
| `SQLALCHEMY_ECHO` | false | Afficher les requêtes SQL | true pour le débogage |

**Exemples d'URL de base de données** :
```bash
# PostgreSQL (service externe via docker-compose)
DATABASE_URL=postgresql://leviia:motdepasse@db:5432/leviia

# SQLite (pour le développement, sans service externe)
DATABASE_URL=sqlite:////app/data/app.db

# MySQL/MariaDB (service externe)
DATABASE_URL=mysql://user:password@host:3306/database
```

#### Configuration PostgreSQL (Service Externe)

| Variable | Valeur par défaut | Description | Recommandation |
|----------|-------------------|-------------|----------------|
| `POSTGRES_DB` | leviia | Nom de la base de données | Changez si nécessaire |
| `POSTGRES_USER` | leviia | Utilisateur PostgreSQL | Changez pour la sécurité |
| `POSTGRES_PASSWORD` | leviia-pass | **Mot de passe PostgreSQL** | **À CHANGER ABSOLUMENT** |
| `POSTGRES_PORT` | 5432 | Port PostgreSQL | Changez si nécessaire |

---

## 🔒 Sécurité en Production

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

---

## 🐛 Dépannage

### Problèmes courants

#### 1. Erreur de connexion à PostgreSQL

**Symptômes** : `Connection refused` ou `could not connect to server`

**Solutions** :
1. Vérifiez que le service PostgreSQL est démarré : `docker-compose ps`
2. Attendez que PostgreSQL soit prêt : `docker-compose logs db`
3. Vérifiez l'URL de la base de données dans `.env`

#### 2. Utiliser SQLite sans PostgreSQL

Si vous ne voulez pas utiliser PostgreSQL :

```bash
# Dans docker/.env
DATABASE_URL=sqlite:////app/data/app.db

# Démarrer uniquement l'application
cd docker
docker-compose up -d app
```

---

## 📚 Documentation Complète

- [📚 Documentation complète](../docs/README.md) - Index de toute la documentation
- [🚀 Guide de Démarrage Rapide](../docs/QUICK_START.md) - Installation en 5 minutes
- [🛡️ Guide Administrateur](../docs/ADMIN_GUIDE.md) - Configuration et maintenance
- [🐳 Guide Docker](../docs/DOCKER_GUIDE.md) - Documentation Docker détaillée
- [💻 Architecture Technique](../docs/ARCHITECTURE.md) - Comprendre le fonctionnement

---

## 📜 Licence

Ce document fait partie de **Leviia Schedule**, sous licence **CeCILL v2.1**. 
Voir [LICENSE](../LICENSE) pour plus de détails.
