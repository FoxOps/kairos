# Kubernetes Configuration for Kairos

This folder contains the files needed to deploy Kairos on a Kubernetes cluster.

## Requirements

- A Kubernetes cluster (Minikube, EKS, AKS, GKE, etc.)
- `kubectl` configured to access the cluster
- An accessible Docker registry (for the application image)
- A secrets manager (optional but recommended)

## Structure

```
k8s/
├── namespace.yaml          # Dedicated namespace for the application
├── configmap.yaml         # Application configuration
├── secret.yaml            # Secrets (do not commit!)
├── deployment.yaml        # Application deployment
├── service.yaml           # Service exposing the application
├── ingress.yaml           # HTTP routing (optional)
├── hpa.yaml               # Horizontal auto-scaling (optional)
└── pdb.yaml               # Pod Disruption Budget (optional)
```

## Deployment

### 1. Create the namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Configure the secrets

**⚠️ IMPORTANT: Do not commit the `secret.yaml` file with real values!**

Create the `secret.yaml` file from the template:

```bash
cp secret.yaml.template secret.yaml
# Edit secret.yaml with your values
```

Or create the secrets directly with kubectl:

```bash
kubectl create secret generic kairos-secrets \
  --namespace=kairos \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL=postgresql://user:pass@postgres:5432/kairos \
  --from-literal=ADMIN_PASSWORD=your-admin-password
```

### 3. Deploy the application

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 4. (Optional) Configure the ingress

```bash
kubectl apply -f ingress.yaml
```

### 5. (Optional) Configure auto-scaling

```bash
kubectl apply -f hpa.yaml
```

## Verification

### View the pods

```bash
kubectl get pods -n kairos
```

### View the logs

```bash
kubectl logs -n kairos deployment/kairos -f
```

### Access the application

If you're using the ingress:
```bash
kubectl get ingress -n kairos
```

Otherwise, use port-forward:
```bash
kubectl port-forward -n kairos svc/kairos 5000:5000
# Then access http://localhost:5000
```

## Updating

To update the application:

```bash
# Update the image in the deployment
kubectl set image -n kairos deployment/kairos kairos=your-registry/kairos:latest

# View the rollout status
kubectl rollout status -n kairos deployment/kairos
```

## Cleanup

```bash
kubectl delete -f k8s/ --ignore-not-found
```

## Recommended configuration

### Resources
- CPU: 500m - 1000m
- Memory: 512Mi - 1Gi

### Replicas
- Minimum: 2 (for high availability)
- Maximum: 10 (depending on load)

### Auto-scaling
- CPU target: 70%
- Minimum replicas: 2
- Maximum replicas: 5
