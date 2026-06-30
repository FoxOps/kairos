# Dockerisation simplifiée de Leviia Schedule

## 📋 Structure simplifiée

```
leviia-schedule/
├── docker/
│   ├── Dockerfile          # Image Docker
│   ├── entrypoint.sh       # Script de démarrage
│   ├── docker-compose.yml  # Configuration de base
│   ├── docker-compose.dev.yml  # Développement
│   ├── docker-compose.prod.yml  # Production
│   └── Makefile.docker     # Commandes
│
├── .env                   # Variables d'environnement
├── data/                  # Données persistantes
└── logs/                  # Logs
```

---

## 🚀 Utilisation

### 1. Configurer l'environnement

```bash
# Copier l'exemple et modifier
cp .env.example .env
nano .env
```

**Variables importantes dans .env :**
```env
SECRET_KEY=votre_clé_secrète
FLASK_ENV=development  # ou production
DATABASE_URL=sqlite:///app/data/app.db
DEFAULT_ADMIN_PASSWORD=votre_mot_de_passe
```

### 2. Construire l'image

```bash
make -f docker/Makefile.docker build
```

### 3. Démarrer

**Développement :**
```bash
make -f docker/Makefile.docker up-dev
```

**Production (avec PostgreSQL) :**
```bash
make -f docker/Makefile.docker up-prod
```

---

## ⚙️ Configuration

### Développement vs Production

| Aspect | Développement | Production |
|--------|---------------|------------|
| Serveur | Flask (run.py) | Gunicorn |
| Workers | 1 | 4 (PostgreSQL) ou 1 (SQLite) |
| Base de données | SQLite | PostgreSQL |
| Cache | Non | Redis |
| Debug | Oui | Non |

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `FLASK_ENV` | Mode (development/production) | development |
| `SECRET_KEY` | Clé secrète Flask | requis |
| `DATABASE_URL` | URL de la base de données | sqlite:///app/data/app.db |
| `POSTGRES_*` | Config PostgreSQL | voir ci-dessous |

**Pour PostgreSQL en production :**
```env
DATABASE_URL=postgresql://leviia:leviia-pass@db:5432/leviia
POSTGRES_DB=leviia
POSTGRES_USER=leviia
POSTGRES_PASSWORD=leviia-pass
```

---

## 📦 Fichiers

### Dockerfile
- Multi-stage build pour optimiser la taille
- Virtual environment dans `/opt/venv`
- Gunicorn installé pour la production
- Utilisateur non-root (`appuser`)

### entrypoint.sh
- Détecte automatiquement le mode (dev/prod)
- Initialise la base de données en dev
- Attend PostgreSQL si nécessaire
- Lance le bon serveur automatiquement

### docker-compose.yml
- Configuration de base du service web
- Volumes pour les données et logs

### docker-compose.dev.yml
- Mode développement
- Montage du code source
- Désactive les protections de sécurité

### docker-compose.prod.yml
- Mode production
- PostgreSQL + Redis
- Gunicorn avec 4 workers

---

## 🎯 Commandes

| Commande | Description |
|----------|-------------|
| `make -f docker/Makefile.docker build` | Construire |
| `make -f docker/Makefile.docker up-dev` | Démarrer (dev) |
| `make -f docker/Makefile.docker up-prod` | Démarrer (prod) |
| `make -f docker/Makefile.docker down-dev` | Arrêter (dev) |
| `make -f docker/Makefile.docker down-prod` | Arrêter (prod) |
| `make -f docker/Makefile.docker logs` | Voir les logs |
| `make -f docker/Makefile.docker shell` | Shell dans le conteneur |

---

## 🔒 Sécurité

1. **Ne jamais commiter .env**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **En production :**
   - Utiliser PostgreSQL
   - Changer `SECRET_KEY` et `DEFAULT_ADMIN_PASSWORD`
   - Configurer HTTPS via un reverse proxy

3. **Générer une clé secrète :**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

---

## 🐛 Dépannage

### Problème de port
```bash
# Vérifier ce qui utilise le port 5000
sudo lsof -i :5000

# Tuer le processus
kill <PID>
```

### Base de données non prête
Le script d'entrée attend automatiquement PostgreSQL. Si ça bloque :
```bash
# Vérifier les logs de PostgreSQL
docker compose logs db
```

### Erreur de build
```bash
# Reconstruire sans cache
docker compose build --no-cache
```

---

## 📚 Exemples

### Développement local
```bash
# Démarrer
make -f docker/Makefile.docker up-dev

# Accéder à l'application
# http://localhost:5000
# admin@leviia.local / admin123
```

### Production avec PostgreSQL
```bash
# Configurer .env pour la production
cp .env.example .env
# Modifier DATABASE_URL, POSTGRES_*, SECRET_KEY, etc.

# Démarrer
make -f docker/Makefile.docker up-prod

# Accéder à l'application
# http://localhost:5000
```

---

## 🔄 Mises à jour

Pour mettre à jour l'application :
```bash
# Arrêter
make -f docker/Makefile.docker down-prod

# Mettre à jour le code
git pull origin main

# Reconstruire et redémarrer
make -f docker/Makefile.docker build --no-cache
make -f docker/Makefile.docker up-prod
```
