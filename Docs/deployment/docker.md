# Dockerisation de Leviia Schedule (Version Simplifiée)

> **Méthode recommandée** : `docker pull` de l'image déjà construite sur
> le registry, puis `docker run`. C'est la façon principale de lancer
> l'application. `docker compose` (environnement de dev avec mock OIDC)
> et la construction locale de l'image (`docker build`) sont des
> alternatives réservées au développement ou à des cas particuliers
> (contribution au code, modification du `Dockerfile`, pas d'accès au
> registry) - voir plus bas.

## 📋 Structure Ultra-Simple

Chemins relatifs (`.env`, `data/`, `logs/`) résolus par rapport à
`docker/docker-compose.yml`, donc tous sous `docker/` :

```
leviia-schedule/
└── docker/
    ├── Dockerfile          # Image Docker ultra-légère
    ├── entrypoint.sh       # Script de démarrage (serveur web + crond conditionnel)
    ├── crontabs/appuser    # Planification des rappels email et sauvegardes (crond)
    ├── docker-compose.yml  # Stack de développement (app + mock OIDC)
    ├── .env                # Variables d'environnement (à créer, non committé)
    ├── data/                # Données SQLite persistantes
    └── logs/                # Logs
```

**Taille de l'image** : ~150 Mo (avec Alpine Linux)

---

## 🚀 Démarrage rapide (méthode recommandée) : image du registry

L'image est construite et publiée automatiquement par la CI sur chaque
commit de la branche par défaut (job `build_docker`, voir
`.gitlab-ci/.gitlab-ci.yml`), sur un registry Harbor auto-hébergé. C'est
la source à utiliser en priorité pour lancer l'application - pas besoin
de cloner le dépôt ni d'installer d'outil de build.

### 1️⃣ Tirer l'image

```bash
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest
# ou une version précise (SHA court du commit) :
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:<sha-court>
```

> Remplacez `<HARBOR_PROJECT>` par le nom du projet Harbor réel (voir la
> variable CI/CD `CI_REGISTRY_IMAGE`, configurée pour pointer vers Harbor
> plutôt que vers le registry GitLab par défaut).

### 2️⃣ Préparer la configuration et les volumes

```bash
mkdir -p leviia-schedule/data leviia-schedule/logs
cd leviia-schedule

curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/.env.example
nano .env  # SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, TALISMAN_FORCE_HTTPS (voir Configuration ci-dessous)
```

### 3️⃣ Démarrer le conteneur

```bash
docker run -d \
  --name leviia-schedule \
  -p 5000:5000 \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest
```

Mode développement (Flask avec reloader) ou production (Gunicorn) selon
`FLASK_ENV` dans `.env` (`development` par défaut).

### 4️⃣ Accéder à l'application

Ouvrez votre navigateur : [http://localhost:5000](http://localhost:5000)

**Identifiants par défaut :**
- Email : `admin@leviia.local`
- Mot de passe : `admin123` (ou celui que vous avez configuré dans `.env`)

### Mettre à jour

```bash
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest
docker stop leviia-schedule && docker rm leviia-schedule
# puis relancer la commande docker run de l'étape 3
```

---

## 🛠️ Alternatives : développement et cas particuliers

Réservé aux cas où l'image du registry ne suffit pas : contribuer au
code, tester une modification du `Dockerfile`, exercer le flux SSO/OIDC
en local (mock fourni par `docker-compose.yml`), ou absence d'accès au
registry Harbor.

### Construire l'image soi-même (`docker build`)

Pas de wrapper Make : `docker build` en direct, lancé **depuis le
dossier `docker/`** (le `Dockerfile` a besoin du reste du dépôt comme
contexte de build - `..` - mais la commande elle-même s'exécute dans
`docker/`, pas depuis la racine) :

```bash
cd docker
docker build -f Dockerfile -t leviia-schedule:dev ..
```

### Environnement de dev complet via Docker Compose (app + mock OIDC)

`docker-compose.yml` construit l'image localement (`build: context: ..`)
et démarre en plus un fournisseur OIDC de test
(`ghcr.io/soluto/oidc-server-mock`, dépendance obligatoire de ce
fichier) - pratique pour développer/tester le flux SSO sans vrai
Keycloak/Okta, mais superflu pour un déploiement normal (préférez
`docker run` avec l'image du registry, voir plus haut).

#### Configurer l'environnement

`docker-compose.yml` n'a pas de bloc `environment:` pour le service
applicatif - tout passe par le fichier `.env` (`env_file: ./.env`,
résolu relativement à `docker/docker-compose.yml`, donc **placez-le à
`docker/.env`**, pas à la racine du dépôt).

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

#### Construire et démarrer

```bash
# Toujours depuis le dossier docker/
docker compose build
docker compose up -d
```

Accès : [http://localhost:5000](http://localhost:5000) (identifiants par
défaut identiques à la section recommandée ci-dessus).

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

### Exemple de `.env` complet

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
  commande `docker build` est lancée depuis `docker/`. Non pertinent si
  vous utilisez l'image du registry (méthode recommandée).

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
- **Environnement de dev uniquement** (voir Alternatives ci-dessus) :
  construit l'image localement et démarre en plus un mock OIDC
  (`oidc-mock`, dépendance obligatoire du fichier). Pour un déploiement
  normal, préférez `docker run` avec l'image du registry.
- **Service applicatif** : conteneur avec l'application (et, si activé,
  les rappels par email et/ou les sauvegardes - même conteneur, voir
  ci-dessus) - voir
  [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)
  pour la configuration SMTP et
  [`deployment/BACKUP_GUIDE.md`](BACKUP_GUIDE.md) pour les sauvegardes
- **Volumes** : Persistance des données et logs
- **Ports** : 5000 exposé

---

## 🎯 Commandes

### Recommandé (image du registry)

| Commande | Description |
|----------|-------------|
| `docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest` | Tirer la dernière image |
| `docker run -d --name leviia-schedule -p 5000:5000 --env-file .env -v "$(pwd)/data:/app/data" -v "$(pwd)/logs:/app/logs" harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest` | Démarrer |
| `docker logs -f leviia-schedule` | Voir les logs |
| `docker exec -it leviia-schedule sh` | Shell dans le conteneur |
| `docker stop leviia-schedule && docker rm leviia-schedule` | Arrêter et supprimer le conteneur |

### Alternatives dev (depuis le dossier `docker/`)

| Commande | Description |
|----------|-------------|
| `docker build -f Dockerfile -t leviia-schedule:dev ..` | Construire l'image (docker build de base, sans Compose) |
| `docker compose build` | Construire l'image + mock OIDC via Compose |
| `docker compose up -d` | Démarrer la stack de dev complète |
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

- Mettre `FLASK_ENV=production` dans `.env`, puis relancer le conteneur
  (`docker run`, voir méthode recommandée ci-dessus)
- Changer `SECRET_KEY` et `DEFAULT_ADMIN_PASSWORD`
- Configurer un reverse proxy (Nginx, Traefik) pour HTTPS, puis repasser
  `TALISMAN_FORCE_HTTPS=true` (ou retirer la ligne) dans `.env`

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

### Problème : Le conteneur ne démarre pas

**Vérifier les logs :**
```bash
docker logs leviia-schedule
# ou, en dev via Compose (depuis docker/) : docker compose logs leviia-schedule
```

**Vérifier l'image :**
```bash
docker pull harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest
# ou, en dev (depuis docker/) : docker compose build --no-cache
```

### Problème : Erreur de permissions

**Solution :**
```bash
# Donner les permissions à l'utilisateur courant
sudo chown -R $USER:$USER data logs

# Créer les répertoires nécessaires si absents
mkdir -p data logs
chmod -R 755 data logs
```

### Problème : Base de données non initialisée

**Solution :**
```bash
# Supprimer la base de données existante
rm -f data/app.db

# Redémarrer le conteneur
docker stop leviia-schedule && docker rm leviia-schedule
# puis relancer la commande docker run (voir Démarrage rapide)
```

### Problème : Port 5000 déjà utilisé

**Solution :**
```bash
# Trouver le processus
sudo lsof -i :5000

# Tuer le processus
kill <PID>

# Ou changer le port exposé (-p 5001:5000 par exemple)
```

---

## 📞 Support

Pour des configurations avancées (PostgreSQL, Redis, etc.), consultez :
- [Guide Avancé : PostgreSQL et Redis](DEPLOYMENT_ADVANCED.md)

Pour des problèmes spécifiques, vérifiez :
1. Les logs avec `docker logs leviia-schedule`
2. La configuration dans `.env`
3. Les permissions des fichiers

---

*Documentation simplifiée pour Leviia Schedule - Dockerisation de base*
