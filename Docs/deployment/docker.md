# Dockerisation de Leviia Schedule (Version Simplifiée)

## 📋 Structure Ultra-Simple

Chemins relatifs (`.env`, `data/`, `logs/`) résolus par rapport à
`docker/docker-compose.yml`, donc tous sous `docker/` :

```
leviia-schedule/
└── docker/
    ├── Dockerfile          # Image Docker ultra-légère
    ├── entrypoint.sh       # Script de démarrage (serveur web + crond conditionnel)
    ├── crontabs/appuser    # Planification des rappels email (crond)
    ├── docker-compose.yml  # Configuration de base
    ├── Makefile            # Commandes simplifiées
    ├── .env                # Variables d'environnement (à créer, non committé)
    ├── data/                # Données SQLite persistantes
    └── logs/                # Logs
```

**Taille de l'image** : ~150 Mo (avec Alpine Linux)

---

## 🚀 Utilisation de Base

### 1️⃣ Configurer l'environnement

`docker-compose.yml` n'a pas de bloc `environment:` - tout passe par le
fichier `.env` (`env_file: ./.env`, chemin résolu relativement à
`docker/docker-compose.yml`, donc **placez-le à `docker/.env`**, pas à
la racine du dépôt).

```bash
# Copier l'exemple (depuis la racine du dépôt)
cp .env.example docker/.env

# Modifier les variables importantes
nano docker/.env
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

```bash
make -f docker/Makefile build
```

### 3️⃣ Démarrer

```bash
make -f docker/Makefile up
```

Mode développement (Flask avec reloader) ou production (Gunicorn) selon
`FLASK_ENV` dans `docker/.env` (`development` par défaut) - pas de
cible Make séparée, une seule variable à changer.

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

### entrypoint.sh
- **Initialisation** : Crée la base de données SQLite si elle n'existe pas
- **Données par défaut** : Crée les types de shifts, le groupe et l'admin
- **Notifications par email** : si `NOTIFICATIONS_ENABLED=true` (voir
  `.env`), démarre `crond` (busybox, déjà présent dans l'image Alpine,
  pas de paquet supplémentaire) en arrière-plan avant de lancer le
  serveur web - planning dans `docker/crontabs/appuser`. Rien de plus à
  configurer : une seule variable d'environnement, aucun service Docker
  supplémentaire à gérer.
- **Sélection serveur** : 
  - `development` → `python run.py` (avec reloader)
  - `production` → `gunicorn` (1 worker pour SQLite)

### docker-compose.yml
- **Service web** : conteneur avec l'application (et, si activé, les
  rappels par email - même conteneur, voir ci-dessus) - voir
  [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)
  pour la configuration SMTP
- **Volumes** : Persistance des données et logs
- **Ports** : 5000 exposé

### Makefile
- **Commandes simplifiées** : build, up, down, logs, shell
- **Mode production** : `FLASK_ENV=production` dans `docker/.env`, puis
  `up` comme d'habitude (pas de cible séparée)

---

## 🎯 Commandes

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile build` | Construire l'image |
| `make -f docker/Makefile up` | Démarrer (dev ou prod selon `FLASK_ENV` dans `docker/.env`) |
| `make -f docker/Makefile down` | Arrêter |
| `make -f docker/Makefile logs` | Voir les logs |
| `make -f docker/Makefile shell` | Shell dans le conteneur |

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

- Mettre `FLASK_ENV=production` dans `docker/.env`, puis `make -f docker/Makefile up`
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

### Problème : Le conteneur ne démarre pas

**Vérifier les logs :**
```bash
docker compose logs web
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

### Mettre à jour l'application

```bash
# Arrêter
docker compose down

# Mettre à jour le code
git pull origin main

# Reconstruire et redémarrer
docker compose build --no-cache
docker compose up -d
```

### Mettre à jour les dépendances

```bash
# Dans le conteneur
make -f docker/Makefile shell

# Mettre à jour requirements.txt
pip freeze > requirements.txt

# Reconstruire
docker compose build --no-cache
```

---

## 📚 Exemples

### Déploiement local rapide

```bash
# Cloner le projet
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule

# Configurer (docker/.env, pas .env à la racine - voir section
# "Configurer l'environnement" plus haut)
cp .env.example docker/.env
nano docker/.env  # Modifier SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, TALISMAN_FORCE_HTTPS

# Démarrer
make -f docker/Makefile up

# Accéder à l'application
# http://localhost:5000
```

### Déploiement en production simple

```bash
# Configurer pour la production
cp .env.example docker/.env
nano docker/.env  # Modifier SECRET_KEY, DEFAULT_ADMIN_PASSWORD, DATABASE_URL, FLASK_ENV=production

# Démarrer (le mode production - Gunicorn - est piloté par FLASK_ENV
# dans docker/.env, pas par une cible Make séparée)
make -f docker/Makefile up

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
