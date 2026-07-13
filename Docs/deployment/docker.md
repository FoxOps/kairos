# Dockerisation de Leviia Schedule (Version Simplifiée)

> **Méthode recommandée** : deux fichiers à récupérer
> (`docker-compose.example.yml` + `.env.example`, à la racine du dépôt),
> une image déjà construite sur le registry - pas de clone du dépôt, pas
> de build local, pas de mock OIDC (dev only). Construire l'image
> soi-même ou cloner le dépôt pour un environnement de dev complet
> (`docker/`) sont des alternatives réservées au développement ou à des
> cas particuliers - voir plus bas.

---

## 🚀 Démarrage rapide (méthode recommandée)

L'image est construite et publiée automatiquement par la CI sur chaque
commit de la branche par défaut (job `build_docker`, voir
`.gitlab-ci/.gitlab-ci.yml`), sur un registry Harbor auto-hébergé.

### 1️⃣ Récupérer les deux fichiers nécessaires

Pas besoin de cloner le dépôt entier - seuls deux fichiers, à la racine
du dépôt, sont nécessaires :

```bash
mkdir leviia-schedule && cd leviia-schedule

curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/.env.example
```

### 2️⃣ Configurer

```bash
nano .env
```

**Variables minimales :**
```env
# Image à tirer du registry Harbor - remplacez <HARBOR_PROJECT> par le
# nom du projet Harbor réel (voir la variable CI/CD CI_REGISTRY_IMAGE,
# configurée pour pointer vers Harbor plutôt que le registry GitLab).
LEVIIA_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest

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

### 3️⃣ Démarrer

```bash
docker compose up -d
```

`docker-compose.yml` (issu de `docker-compose.example.yml`) n'a pas de
section `build:` - il ne peut que tirer l'image du registry, jamais la
construire localement. Mode développement (Flask avec reloader) ou
production (Gunicorn) selon `FLASK_ENV` dans `.env` (`development` par
défaut).

### 4️⃣ Accéder à l'application

Ouvrez votre navigateur : [http://localhost:5000](http://localhost:5000)

**Identifiants par défaut :**
- Email : `admin@leviia.local`
- Mot de passe : `admin123` (ou celui que vous avez configuré dans `.env`)

### Mettre à jour

```bash
docker compose pull
docker compose up -d
```

---

## 🛠️ Alternatives : développement et cas particuliers

Réservé aux cas où l'image du registry ne suffit pas : contribuer au
code, tester une modification du `Dockerfile`, exercer le flux SSO/OIDC
en local (mock optionnel). Nécessite de cloner le dépôt entier :

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule/docker
```

Structure de `docker/` (chemins relatifs `.env`/`data`/`logs` résolus
par rapport à `docker/docker-compose.yml`, donc tous sous `docker/`) :

```
leviia-schedule/
└── docker/
    ├── Dockerfile          # Image Docker ultra-légère
    ├── entrypoint.sh       # Script de démarrage (serveur web + crond conditionnel)
    ├── crontabs/appuser    # Planification des rappels email et sauvegardes (crond)
    ├── docker-compose.yml  # Service applicatif (build local ou registry) + mock OIDC optionnel (profil)
    ├── .env                # Variables d'environnement (à créer, non committé)
    ├── data/                # Données SQLite persistantes
    └── logs/                # Logs
```

Toutes les commandes ci-dessous s'exécutent **depuis le dossier `docker/`**.

### Configurer l'environnement

```bash
cp ../.env.example .env
nano .env
```

Mêmes variables que la méthode recommandée ci-dessus (`SECRET_KEY`,
`DEFAULT_ADMIN_PASSWORD`, `DATABASE_URL`, `TALISMAN_FORCE_HTTPS`).
`LEVIIA_IMAGE` reste utilisable ici aussi (voir plus bas).

### Construire l'image soi-même (`docker build` de base, sans Compose)

```bash
docker build -f Dockerfile -t leviia-schedule:dev ..
```

Le `Dockerfile` a besoin du reste du dépôt comme contexte de build
(`..`) - la commande elle-même s'exécute dans `docker/`, pas depuis la
racine.

### Construire et démarrer via Compose

Sans `LEVIIA_IMAGE` dans `.env` (ou en le retirant), `docker/docker-compose.yml`
retombe sur son tag de build local par défaut (`leviia-schedule:dev`) :

```bash
docker compose build
docker compose up -d
```

Avec `LEVIIA_IMAGE` défini, `docker compose pull leviia-schedule` puis
`docker compose up -d --no-build` utilise l'image du registry sans
jamais déclencher de build local - utile pour tester la stack de dev
(mock OIDC compris) contre une image déjà publiée.

### Tester le flux SSO/OIDC en local (mock)

`docker/docker-compose.yml` inclut un fournisseur OIDC de test
(`ghcr.io/soluto/oidc-server-mock`), démarré uniquement via son profil
Compose dédié - jamais par un `docker compose up -d` normal :

```bash
docker compose --profile oidc-mock up -d
```

Accès : [http://localhost:5000](http://localhost:5000) (identifiants par
défaut identiques à la section recommandée ci-dessus).

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `LEVIIA_IMAGE` | Image à utiliser (registry) | requis dans `docker-compose.example.yml` ; `leviia-schedule:dev` (build local) dans `docker/docker-compose.yml` | ✅ / ❌ selon le fichier |
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
# Image du registry - obligatoire avec docker-compose.example.yml
LEVIIA_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest

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

### docker-compose.example.yml (racine du dépôt)
- **Méthode recommandée** : un seul service, pas de `build:` - tire
  toujours `LEVIIA_IMAGE` depuis le registry. À copier en
  `docker-compose.yml` dans le dossier où vous déployez (voir
  Démarrage rapide).
- **Volumes** : `./data:/app/data`, `./logs:/app/logs` (créés
  automatiquement par Docker au premier démarrage si absents)
- **Port** : 5000 exposé

### docker/Dockerfile
- **Base** : Python 3.11 Alpine (ultra-léger)
- **Dépendances** : Installe `requirements.txt` + Gunicorn
- **Utilisateur** : `appuser` (non-root) pour la sécurité
- **Taille** : Optimisée avec Alpine et nettoyage des dépendances de build
- **Contexte de build** : `..` (racine du dépôt) - le `Dockerfile` copie
  `docker/requirements.txt`, `docker/entrypoint.sh` et le code applicatif
  (`COPY . .`), donc le contexte doit englober tout le dépôt même si la
  commande `docker build` est lancée depuis `docker/`. Non pertinent si
  vous utilisez l'image du registry (méthode recommandée).

### docker/entrypoint.sh
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

### docker/docker-compose.yml (environnement de dev, clone requis)
- **Service applicatif** (`leviia-schedule`) : `image: ${LEVIIA_IMAGE:-leviia-schedule:dev}`
  - build local par défaut (`build: context: ..`), ou image du registry
    sans build si `LEVIIA_IMAGE` est défini et `--no-build` passé - voir
    ci-dessus. Et, si activé, les rappels par email et/ou les
    sauvegardes - même conteneur, voir ci-dessus - voir
    [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)
    pour la configuration SMTP et
    [`deployment/BACKUP_GUIDE.md`](BACKUP_GUIDE.md) pour les sauvegardes
- **Service `oidc-mock`** : optionnel, derrière le profil Compose
  `oidc-mock` - ne démarre jamais avec un `docker compose up -d` normal
  (voir Alternatives ci-dessus)
- **Volumes** : Persistance des données et logs
- **Ports** : 5000 exposé (+ 8080 pour `oidc-mock` si son profil est activé)

---

## 🎯 Commandes

### Recommandé (deux fichiers récupérés, sans clone)

| Commande | Description |
|----------|-------------|
| `docker compose up -d` | Tirer l'image et démarrer |
| `docker compose pull` | Mettre à jour l'image |
| `docker compose logs -f leviia-schedule` | Voir les logs |
| `docker compose exec leviia-schedule sh` | Shell dans le conteneur |
| `docker compose down` | Arrêter |

### Alternatives dev (clone requis, depuis `docker/`)

| Commande | Description |
|----------|-------------|
| `docker build -f Dockerfile -t leviia-schedule:dev ..` | Construire l'image (docker build de base, sans Compose) |
| `docker compose build` | Construire l'image localement via Compose |
| `docker compose up -d` | Démarrer avec l'image construite localement |
| `docker compose --profile oidc-mock up -d` | Démarrer avec le mock OIDC en plus (test SSO local) |

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

- Mettre `FLASK_ENV=production` dans `.env`, puis `docker compose up -d`
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
docker compose logs leviia-schedule
```

**Vérifier l'image :**
```bash
docker compose pull
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

## 📚 Exemples

### Déploiement rapide (registry, sans clone)

```bash
mkdir leviia-schedule && cd leviia-schedule
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/.env.example

nano .env  # LEVIIA_IMAGE, SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, TALISMAN_FORCE_HTTPS

docker compose up -d

# Accéder à l'application
# http://localhost:5000
```

### Déploiement en production simple

```bash
mkdir leviia-schedule && cd leviia-schedule
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/.env.example

nano .env  # LEVIIA_IMAGE, SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, FLASK_ENV=production

# Le mode production - Gunicorn - est piloté par FLASK_ENV dans .env,
# pas par une commande séparée
docker compose up -d

# Accéder à l'application
# http://localhost:5000
```

---

## 📞 Support

Pour des configurations avancées (PostgreSQL, Redis, etc.), consultez :
- [Guide Avancé : PostgreSQL et Redis](DEPLOYMENT_ADVANCED.md)

Pour des problèmes spécifiques, vérifiez :
1. Les logs avec `docker compose logs`
2. La configuration dans `.env`
3. Les permissions des fichiers

---

*Documentation simplifiée pour Leviia Schedule - Dockerisation de base*
