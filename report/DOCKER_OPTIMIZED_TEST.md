# Guide de test pour le Dockerfile optimisé

## 🐳 Tester le Dockerfile optimisé localement

### 1. Construire l'image

```bash
cd /workspace/FoxOps__leviia-schedule
docker build -t leviia-schedule:optimized -f docker/Dockerfile.optimized .
```

**Si vous obtenez une erreur de permission sur /var/run/docker.sock :**

```bash
# Sur Linux
sudo usermod -aG docker $USER
newgrp docker

# Ou utiliser sudo
sudo docker build -t leviia-schedule:optimized -f docker/Dockerfile.optimized .
```

### 2. Exécuter le conteneur

```bash
docker run -d \
  --name leviia-test \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e FLASK_ENV=production \
  -e DATABASE_URL=sqlite:////app/data/app.db \
  leviia-schedule:optimized
```

### 3. Vérifier que le conteneur fonctionne

```bash
# Voir les logs
docker logs leviia-test

# Vérifier le statut
docker ps

# Tester l'application
curl http://localhost:5000/health
```

### 4. Accéder à l'application

Ouvrez votre navigateur à : http://localhost:5000

### 5. Tester les endpoints de monitoring

```bash
# Métriques Prometheus
curl http://localhost:5000/metrics

# Statut de santé
curl http://localhost:5000/health

# Statut de prêt
curl http://localhost:5000/ready
```

## 🔍 Comparaison avec le Dockerfile actuel

### Construire avec le Dockerfile actuel

```bash
docker build -t leviia-schedule:current -f docker/Dockerfile .
```

### Comparer les tailles

```bash
# Voir la taille des images
docker images | grep leviia-schedule

# Ou plus détaillé
docker image inspect leviia-schedule:optimized | grep -i size
docker image inspect leviia-schedule:current | grep -i size
```

### Exemple de sortie attendue

```
REPOSITORY              TAG        IMAGE ID       CREATED         SIZE
leviia-schedule        optimized  abc123...   2 minutes ago   120MB
leviia-schedule        current    def456...   2 minutes ago   150MB
```

## ⚠️ Problèmes courants et solutions

### Problème 1: "No such file or directory: 'docker/requirements.txt'"

**Cause :** Le chemin dans le Dockerfile était incorrect.

**Solution :** Ce problème a été corrigé dans la version actuelle du Dockerfile.optimized. Assurez-vous d'utiliser la dernière version.

### Problème 2: "Permission denied" lors de la construction

**Solution :**
```bash
# Donner les permissions sur le Dockerfile
chmod +x docker/Dockerfile.optimized

# Ou utiliser sudo
sudo docker build -t leviia-schedule:optimized -f docker/Dockerfile.optimized .
```

### Problème 3: "ERROR: Could not open requirements file"

**Cause :** Le fichier requirements.txt n'existe pas dans le contexte de build.

**Solution :** Vérifiez que vous êtes dans le bon répertoire et que le fichier existe :
```bash
ls -la docker/requirements.txt
```

### Problème 4: Erreurs d'installation de dépendances

**Solution :** Certaines dépendances peuvent nécessiter des dépendances système. Le Dockerfile optimisé inclut déjà :
- gcc
- musl-dev
- libpq-dev
- postgresql-dev

Si vous avez besoin d'autres dépendances, modifiez le Dockerfile :
```dockerfile
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libpq-dev \
    postgresql-dev \
    # Ajoutez ici d'autres dépendances si nécessaire
```

## 📊 Vérification de l'optimisation

### 1. Vérifier le multi-stage build

```bash
# Voir les layers de l'image
docker history leviia-schedule:optimized
```

Vous devriez voir que l'image finale ne contient pas les dépendances de build (gcc, etc.).

### 2. Vérifier le health check

```bash
# Voir le statut de santé
docker inspect --format='{{json .State.Health}}' leviia-test
```

### 3. Vérifier l'utilisateur

```bash
# Vérifier que le conteneur s'exécute avec l'utilisateur non-root
docker exec leviia-test whoami
# Doit afficher : appuser
```

## 🎯 Prochaines étapes

Une fois que vous avez validé que le Dockerfile optimisé fonctionne correctement :

1. **Remplacer le Dockerfile actuel** (optionnel) :
   ```bash
   cp docker/Dockerfile.optimized docker/Dockerfile
   ```

2. **Mettre à jour le Makefile** pour utiliser le nouveau Dockerfile

3. **Pousser les changements** et merger la PR

## 📝 Notes

- Le Dockerfile optimisé utilise **Alpine Linux** pour une image plus légère
- Le **multi-stage build** réduit la taille finale en ne gardant que les fichiers nécessaires
- Le **health check** permet à Kubernetes de surveiller la santé du conteneur
- L'**utilisateur non-root** améliore la sécurité

Si vous avez des questions ou des problèmes, n'hésitez pas à demander !
