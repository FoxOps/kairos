# Configuration Kubernetes pour Leviia Schedule

Ce dossier contient les fichiers nécessaires pour déployer Leviia Schedule sur un cluster Kubernetes.

## Prérequis

- Un cluster Kubernetes (Minikube, EKS, AKS, GKE, etc.)
- `kubectl` configuré pour accéder au cluster
- Un registry Docker accessible (pour l'image de l'application)
- Un gestionnaire de secrets (optionnel mais recommandé)

## Structure

```
k8s/
├── namespace.yaml          # Namespace dédié pour l'application
├── configmap.yaml         # Configuration de l'application
├── secret.yaml            # Secrets (à ne pas commiter !)
├── deployment.yaml        # Déploiement de l'application
├── service.yaml           # Service pour exposer l'application
├── ingress.yaml           # Routage HTTP (optionnel)
├── hpa.yaml               # Auto-scaling horizontal (optionnel)
└── pdb.yaml               # Pod Disruption Budget (optionnel)
```

## Déploiement

### 1. Créer le namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Configurer les secrets

**⚠️ IMPORTANT : Ne pas commiter le fichier `secret.yaml` avec des valeurs réelles !**

Créer le fichier `secret.yaml` à partir du template :

```bash
cp secret.yaml.template secret.yaml
# Éditer secret.yaml avec vos valeurs
```

Ou créer les secrets directement avec kubectl :

```bash
kubectl create secret generic leviia-secrets \
  --namespace=leviia-schedule \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL=postgresql://user:pass@postgres:5432/leviia \
  --from-literal=ADMIN_PASSWORD=your-admin-password
```

### 3. Déployer l'application

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 4. (Optionnel) Configurer l'ingress

```bash
kubectl apply -f ingress.yaml
```

### 5. (Optionnel) Configurer l'auto-scaling

```bash
kubectl apply -f hpa.yaml
```

## Vérification

### Voir les pods

```bash
kubectl get pods -n leviia-schedule
```

### Voir les logs

```bash
kubectl logs -n leviia-schedule deployment/leviia-schedule -f
```

### Accéder à l'application

Si vous utilisez l'ingress :
```bash
kubectl get ingress -n leviia-schedule
```

Sinon, utiliser le port-forward :
```bash
kubectl port-forward -n leviia-schedule svc/leviia-schedule 5000:5000
# Puis accéder à http://localhost:5000
```

## Mise à jour

Pour mettre à jour l'application :

```bash
# Mettre à jour l'image dans le deployment
kubectl set image -n leviia-schedule deployment/leviia-schedule leviia-schedule=your-registry/leviia-schedule:latest

# Voir le statut du rollout
kubectl rollout status -n leviia-schedule deployment/leviia-schedule
```

## Nettoyage

```bash
kubectl delete -f k8s/ --ignore-not-found
```

## Configuration recommandée

### Ressources
- CPU : 500m - 1000m
- Mémoire : 512Mi - 1Gi

### Réplicas
- Minimum : 2 (pour la haute disponibilité)
- Maximum : 10 (selon la charge)

### Auto-scaling
- CPU target : 70%
- Minimum replicas : 2
- Maximum replicas : 5
