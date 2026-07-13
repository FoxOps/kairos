# Dockerisation de Leviia Schedule (Version Simplifiée)

## 📋 Structure Ultra-Simple

Chemins relatifs (`.env`, `data/`, `logs/`) résolus par rapport à
`docker/docker-compose.yml`, donc tous sous `docker/` :

```
leviia-schedule/
└── docker/
    ├── Dockerfile          # Image Docker ultra-légère
    ├── entrypoint.sh       # Script de démarrage (serveur web + crond conditionnel)
    ├── crontabs/appuser    # Planification des rappels email et sauvegardes (crond)
    ├── docker-compose.yml  # Configuration de base
    ├── .env                # Variables d'environnement (à créer, non committé)
    ├── data/                # Données SQLite persistantes
    └── logs/                # Logs
```

**Taille de l'image** : ~150 Mo (avec Alpine Linux)

---

## 📥 Utiliser l'image déjà construite (registry)

L'image est construite et publiée automatiquement par la CI sur chaque
commit de la branche par défaut (job `build_docker`, voir
`.gitlab-ci/.gitlab-ci.yml`), sur un registry Harbor auto-hébergé :

```bash
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest
# ou une version précise (SHA court du commit) :
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:<sha-court>
```

> Remplacez `<HARBOR_PROJECT>` par le nom du projet Harbor réel (voir la
> variable CI/CD `CI_REGISTRY_IMAGE`, configurée pour pointer vers Harbor
> plutôt que vers le registry GitLab par défaut).

C'est équivalent à construire l'image vous-même (section suivante) - à
utiliser en priorité si vous n'avez pas besoin de modifier le code.
Ensuite, passez directement à la section [Démarrer](#3️⃣-démarrer) en
remplaçant `leviia-schedule:dev` par le tag de l'image tirée du registry
dans `docker/docker-compose.yml` (`image:`), ou lancez-la directement
avec `docker run` (voir [Configuration](#⚙️-configuration) pour les
variables d'environnement et volumes nécessaires).

---

## 🚀 Construire l'image soi-même

Pas de wrapper Make : `docker build` en direct, lancé **depuis le
dossier `docker/`** (le `Dockerfile` a besoin du reste du dépôt comme
contexte de build - `..` - mais la commande elle-même s'exécute dans
`docker/`, pas depuis la racine) :

```bash
cd docker
docker build -f Dockerfile -t leviia-schedule:dev ..
```

Ou, si vous préférez orchestrer via Compose (nécessaire pour le service
`oidc-mock` associé, voir plus bas) :

```bash
cd docker
docker compose build
```

### 1️⃣ Configurer l'environnement

`docker-compose.yml` n'a pas de bloc `environment:` - tout passe par le
fichier `.env` (`env_file: ./.env`, résolu relativement à
`docker/docker-compose.yml`, donc **placez-le à `docker/.env`**, pas à
la racine du dépôt).

```bash
# Depuis le dossier docker/
cd docker
cp ../.env.example .env
nano .env
```

**Variables minimales dans `docker/.env` :**
```env
SECRET_KEY=votre_clé_secrète
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe
```

**Variables à adapter pour Docker** (valeurs différentes de celles par
défaut dans `.env.example`, pensées pour une exécution hors conteneur) :
```env
# Chemin absolu dans le conteneur, résolu sur le volume monté
# (./data:/app/data) - sans ça la base SQLite n'est pas persistée.
DATABASE_URL=sqlite:////app/data/app.db

# Pas de reverse proxy TLS dans cette stack par défaut : forcer HTTPS
# ferait boucler chaque requête sur une redirection https:// que rien
# ne sert. Repassez à true (ou retirez la ligne) une fois un reverse
# proxy TLS placé devant ce service.
TALISMAN_FORCE_HTTPS=false
```

### 2️⃣ Construire l'image

Voir [Construire l'image soi-même](#🚀-construire-limage-soi-même)
ci-dessus, ou tirez l'image du registry (voir plus haut) pour sauter
cette étape.

### 3️⃣ Démarrer

```bash
# Toujours depuis le dossier docker/
docker compose up -d
```

Mode développement (Flask avec reloader) ou production (Gunicorn) selon
`FLASK_ENV` dans `docker/.env` (`development` par défaut) - une seule
variable à changer, pas de commande séparée.

### 4️⃣ Accéder à l'application

Ouvrez votre navigateur : [http://localhost:5000](http://localhost:5000)

**Identifiants par défaut :**
- Email : `admin@leviia.local`
- Mot de passe : `admin123` (ou celui que vous avez configuré dans `.env`)

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `FLASK_ENV` | Mode (development/production) | development | ❌ |
| `SECRET_KEY` | Clé secrète Flask | requis | ✅ |
| `DATABASE_URL` | URL de la base de données (voir note ci-dessous) | sqlite:////app/data/app.db | ❌ |
| `TALISMAN_FORCE_HTTPS` | Forcer HTTPS - `false` sans reverse proxy TLS | `false` (dev/tests), `true` (prod) | ❌ |
| `DEFAULT_ADMIN_PASSWORD` | Mot de passe admin | admin123 | ✅ |

> **Note `DATABASE_URL`** : quatre slashs (`sqlite:////app/data/app.db`),
> pas trois - c'est un chemin absolu (`/app/data/app.db`) résolu sur le
> volume monté, pas un chemin relatif.

### Exemple de `docker/.env` complet

```env
# Configuration de base
FLASK_ENV=development
SECRET_KEY=votre_clé_secrète_générée

# Base de données - chemin absolu sur le volume monté (./data:/app/data)
DATABASE_URL=sqlite:////app/data/app.db

# Pas de reverse proxy TLS devant ce service par défaut
TALISMAN_FORCE_HTTPS=false

# Mot de passe admin
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe_sécurisé
```

---

## 📦 Fichiers Expliqués

### Dockerfile
- **Base** : Python 3.11 Alpine (ultra-léger)
- **Dépendances** : Installe `requirements.txt` + Gunicorn
- **Utilisateur** : `appuser` (non-root) pour la sécurité
- **Taille** : Optimisée avec Alpine et nettoyage des dépendances de build
- **Contexte de build** : `..` (racine du dépôt) - le `Dockerfile` copie
  `docker/requirements.txt`, `docker/entrypoint.sh` et le code applicatif
  (`COPY . .`), donc le contexte doit englober tout le dépôt même si la
  commande `docker build` est lancée depuis `docker/`.

### entrypoint.sh
- **Initialisation** : Crée la base de données SQLite si elle n'existe pas
- **Données par défaut** : Crée les types de shifts, le groupe et l'admin
- **Notifications par email et sauvegardes** : si `NOTIFICATIONS_ENABLED=true`
  et/ou `BACKUP_ENABLED=true` (voir `.env`), démarre `crond` (busybox,
  déjà présent dans l'image Alpine, pas de paquet supplémentaire) en
  arrière-plan avant de lancer le serveur web - planning dans
  `docker/crontabs/appuser`. Rien de plus à configurer : une variable
  d'environnement par fonctionnalité, aucun service Docker supplémentaire
  à gérer. Pour que les sauvegardes locales survivent aux recréations du
  conteneur, réglez `BACKUP_LOCAL_DIR=/app/data/backups` (le volume
  `./data:/app/data` est déjà monté).
- **Sélection serveur** :
  - `development` → `python run.py` (avec reloader)
  - `production` → `gunicorn` (1 worker pour SQLite)

### docker-compose.yml
- **Service web** : conteneur avec l'application (et, si activé, les
  rappels par email et/ou les sauvegardes - même conteneur, voir
  ci-dessus) - voir
  [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)
  pour la configuration SMTP et
  [`deployment/BACKUP_GUIDE.md`](BACKUP_GUIDE.md) pour les sauvegardes
- **Volumes** : Persistance des données et logs
- **Ports** : 5000 exposé

---

## 🎯 Commandes

Toutes les commandes ci-dessous s'exécutent **depuis le dossier
`docker/`** (`cd docker` au préalable) :

| Commande | Description |
|----------|-------------|
| `docker build -f Dockerfile -t leviia-schedule:dev ..` | Construire l'image (docker build de base, sans Compose) |
| `docker compose build` | Construire l'image via Compose |
| `docker compose up -d` | Démarrer (dev ou prod selon `FLASK_ENV` dans `.env`) |
| `docker compose down` | Arrêter |
| `docker compose logs -f` | Voir les logs |
| `docker compose exec leviia-schedule sh` | Shell dans le conteneur |

---

## 🔒 Sécurité de Base

### 1. Générer une clé secrète

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Générer un mot de passe admin

```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 3. Ne jamais commiter `.env`

```bash
echo ".env" >> .gitignore
```

### 4. En production

- Mettre `FLASK_ENV=production` dans `docker/.env`, puis (depuis
  `docker/`) `docker compose up -d`
- Changer `SECRET_KEY` et `DEFAULT_ADMIN_PASSWORD`
- Configurer un reverse proxy (Nginx, Traefik) pour HTTPS, puis repasser
  `TALISMAN_FORCE_HTTPS=true` (ou retirer la ligne) dans `docker/.env`

---

## 🌐 Pour aller plus loin

Cette configuration de base utilise **SQLite** et est optimisée pour :
- **Simplicité** : Un seul conteneur, facile à déployer
- **Portabilité** : Fonctionne partout avec Docker
- **Légèreté** : Image de ~150 Mo

### Pour ajouter PostgreSQL et Redis

Consultez le guide avancé : [DEPLOYMENT_ADVANCED.md](DEPLOYMENT_ADVANCED.md)

Ce guide explique comment étendre cette configuration pour utiliser :
- **PostgreSQL** comme base de données relationnelle
- **Redis** comme cache
- **Gunicorn avec plusieurs workers** pour de meilleures performances

⚠️ **Recommandation** : Maîtrisez d'abord le déploiement de base avec SQLite avant d'ajouter ces composants.

---

## 🐛 Dépannage

Toutes les commandes ci-dessous s'exécutent depuis `docker/`.

### Problème : Le conteneur ne démarre pas

**Vérifier les logs :**
```bash
docker compose logs leviia-schedule
```

**Vérifier le build :**
```bash
docker compose build --no-cache
```

### Problème : Erreur de permissions

**Solution :**
```bash
# Donner les permissions à l'utilisateur courant
sudo chown -R $USER:$USER .

# Créer les répertoires nécessaires
mkdir -p data logs
chmod -R 755 data logs
```

### Problème : Base de données non initialisée

**Solution :**
```bash
# Supprimer la base de données existante
rm -f data/app.db

# Redémarrer le conteneur
docker compose down && docker compose up -d
```

### Problème : Port 5000 déjà utilisé

**Solution :**
```bash
# Trouver le processus
sudo lsof -i :5000

# Tuer le processus
kill <PID>

# Ou changer le port dans docker-compose.yml
```

---

## 🔄 Mises à jour

Toutes les commandes ci-dessous s'exécutent depuis `docker/`.

### Mettre à jour l'application

```bash
# Arrêter
docker compose down

# Mettre à jour le code
git -C .. pull origin main

# Reconstruire et redémarrer
docker compose build --no-cache
docker compose up -d
```

### Mettre à jour les dépendances

```bash
# Dans le conteneur
docker compose exec leviia-schedule sh

# Mettre à jour requirements.txt (depuis la racine du dépôt)
pip freeze > ../docker/requirements.txt

# Reconstruire
docker compose build --no-cache
```

---

## 📚 Exemples

### Déploiement local rapide

```bash
# Cloner le projet
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule/docker

# Configurer (docker/.env, pas .env à la racine - voir section
# "Configurer l'environnement" plus haut)
cp ../.env.example .env
nano .env  # Modifier SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, TALISMAN_FORCE_HTTPS

# Construire puis démarrer
docker compose build
docker compose up -d

# Accéder à l'application
# http://localhost:5000
```

### Déploiement en production simple

```bash
cd docker
cp ../.env.example .env
nano .env  # Modifier SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, FLASK_ENV=production

# Construire puis démarrer (le mode production - Gunicorn - est piloté
# par FLASK_ENV dans .env, pas par une commande séparée)
docker compose build
docker compose up -d

# Accéder à l'application
# http://localhost:5000
```

---

## 📞 Support

Pour des configurations avancées (PostgreSQL, Redis, etc.), consultez :
- [Guide Avancé : PostgreSQL et Redis](DEPLOYMENT_ADVANCED.md)

Pour des problèmes spécifiques, vérifiez :
1. Les logs avec `docker compose logs` (depuis `docker/`)
2. La configuration dans `docker/.env`
3. Les permissions des fichiers

---

*Documentation simplifiée pour Leviia Schedule - Dockerisation de base*
