# GitHub Cloud Lab — Docker Exercise

A multi-container web application built with Flask + Redis, designed to run inside GitHub Codespaces.

## Project Structure

```
.
├── docker-compose.yml
└── webapp/
    ├── app.py
    ├── requirements.txt
    └── Dockerfile
```

## Quickstart

### Part A — Single container (no Redis)

```bash
docker build -t webapp:v1 webapp/
docker run -d --name my-webapp -p 5000:5000 webapp:v1
curl http://localhost:5000/
curl http://localhost:5000/info
curl http://localhost:5000/health
docker stop my-webapp && docker rm my-webapp
```

### Part B — Full stack with Docker Compose

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:5000/
curl http://localhost:5000/health
```

Visit counter increments with each request — data persists in the Redis named volume.

### Part C — Inspect network and volumes

```bash
# List networks
docker network ls
docker network inspect $(docker network ls --filter name=default -q | head -1)

# List volumes
docker volume ls
docker volume inspect $(docker volume ls -q | grep redis)

# Restart just the web service (Redis keeps running, counter preserved)
docker compose restart web
curl http://localhost:5000/
```

Tear down:

```bash
docker compose down        # keeps volume
docker compose down -v     # removes volume (full reset)
```

### Part D — Multi-stage build

The `webapp/Dockerfile` already uses a multi-stage build. Compare image sizes:

```bash
docker build -t webapp:v1-single webapp/
docker image ls webapp
docker image history webapp:v1-single
```

---

## Exercise 4: Kubernetes with Minikube

### Part A — Start Minikube

```bash
minikube start --driver=docker
kubectl cluster-info
kubectl get nodes
kubectl get all --all-namespaces
kubectl get pods -n kube-system
```

### Part B — Deploy to Kubernetes

Build the image inside Minikube's Docker daemon:

```bash
eval $(minikube docker-env)
docker build -t webapp:v1 webapp/
docker image ls webapp
```

Apply all manifests:

```bash
kubectl apply -f k8s/
kubectl get pods --watch
kubectl rollout status deployment/webapp
kubectl rollout status deployment/redis
```

Test the app:

```bash
URL=$(minikube service webapp --url)
curl $URL/
curl $URL/health
```

### Part C — Self-healing

```bash
POD=$(kubectl get pods -l app=webapp -o name | head -1)
kubectl delete $POD
kubectl get pods --watch
```

Kubernetes immediately replaces the deleted pod to maintain 2 replicas.

### Part D — Scale

```bash
kubectl scale deployment webapp --replicas=4
kubectl get pods
# Traffic spreads across pods — hostname changes per request
URL=$(minikube service webapp --url)
for i in $(seq 1 10); do curl -s $URL/info | python3 -m json.tool; done
# Scale back down
kubectl scale deployment webapp --replicas=2
```

### Part E — Rolling update

```bash
sed -i 's/GitHub Cloud Lab/GitHub Cloud Lab v2/' webapp/app.py
docker build -t webapp:v2 webapp/
sed -i 's/GitHub Cloud Lab v2/GitHub Cloud Lab/' webapp/app.py

kubectl set image deployment/webapp webapp=webapp:v2
kubectl rollout status deployment/webapp
kubectl rollout history deployment/webapp

# Rollback
kubectl rollout undo deployment/webapp
kubectl rollout history deployment/webapp
```

### Part F — Helm (NGINX)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install my-nginx bitnami/nginx --set replicaCount=2 --set service.type=NodePort
helm list
curl $(minikube service my-nginx --url)

# Upgrade to 3 replicas
helm upgrade my-nginx bitnami/nginx --set replicaCount=3 --set service.type=NodePort

# Uninstall
helm uninstall my-nginx
```

### Part G — Diagnostics

```bash
kubectl describe deployment webapp
POD=$(kubectl get pods -l app=webapp -o name | head -1)
kubectl describe $POD
kubectl logs $POD --follow
kubectl logs -l app=webapp --follow

# Resource usage
minikube addons enable metrics-server
sleep 30
kubectl top pods
kubectl top nodes
```

---

---

## Exercise 5: GitHub Actions CI/CD Pipeline

### Pipeline overview

`lint → test → build & push (ghcr.io) → deploy to staging`

The workflow lives at `.github/workflows/pipeline.yml` and triggers on every push or PR to `main`.

### Part A — Linting

`setup.cfg` configures flake8 tolerances (max line length 100). Run locally:

```bash
pip install flake8 --break-system-packages
flake8 webapp/ --max-line-length=100
```

### Part B — Tests

Tests live in `tests/test_app.py` and use `pytest` with Redis mocked out:

```bash
pip install pytest flask redis
python -m pytest tests/ -v --tb=short
```

### Part C — Trigger the pipeline

```bash
git add .
git commit -m "Add full CI/CD pipeline"
git push origin main
```

Watch progress in **Actions** tab:
- ✅ Lint
- ✅ Test (results uploaded as artifact)
- ✅ Build and Push Image → pushed to `ghcr.io`, Trivy scan runs
- ⏸ Deploy to Staging → waits for manual approval

### Part D — Create the staging Environment

1. Go to **Settings → Environments → New environment**
2. Name it `staging`
3. Enable **Required reviewers**, add yourself
4. Click **Save protection rules**

### Part E — Approve deployment

In the Actions tab, click the paused `deploy-staging` job → **Review deployments → staging → Approve and deploy**.

### Part F — Pull the published image

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
docker pull ghcr.io/YOUR_USERNAME/github-cloud-lab/webapp:latest
docker run --rm ghcr.io/YOUR_USERNAME/github-cloud-lab/webapp:latest python -c "print('Image pulled successfully!')"
```

Image tags produced per run:
- `sha-<commit_sha>` — unique per commit
- `main` — tracks the branch
- `latest` — newest main build

---

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Homepage with visit counter |
| `GET /info` | Hostname and environment info |
| `GET /health` | Health check including Redis status |
