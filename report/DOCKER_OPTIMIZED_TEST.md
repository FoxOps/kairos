# Test guide for the optimized Dockerfile

## 🐳 Testing the optimized Dockerfile locally

### 1. Build the image

```bash
cd /workspace/FoxOps__leviia-schedule
docker build -t kairos:optimized -f docker/Dockerfile.optimized .
```

**If you get a permission error on /var/run/docker.sock:**

```bash
# On Linux
sudo usermod -aG docker $USER
newgrp docker

# Or use sudo
sudo docker build -t kairos:optimized -f docker/Dockerfile.optimized .
```

### 2. Run the container

```bash
docker run -d \
  --name kairos-test \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e FLASK_ENV=production \
  -e DATABASE_URL=sqlite:////app/data/app.db \
  kairos:optimized
```

### 3. Verify the container is running

```bash
# View logs
docker logs kairos-test

# Check status
docker ps

# Test the application
curl http://localhost:5000/health
```

### 4. Access the application

Open your browser at: http://localhost:5000

### 5. Test the monitoring endpoints

```bash
# Prometheus metrics
curl http://localhost:5000/metrics

# Health status
curl http://localhost:5000/health

# Readiness status
curl http://localhost:5000/ready
```

## 🔍 Comparison with the current Dockerfile

### Build with the current Dockerfile

```bash
docker build -t kairos:current -f docker/Dockerfile .
```

### Compare sizes

```bash
# View image sizes
docker images | grep kairos

# Or more detailed
docker image inspect kairos:optimized | grep -i size
docker image inspect kairos:current | grep -i size
```

### Expected output example

```
REPOSITORY   TAG        IMAGE ID       CREATED         SIZE
kairos       optimized  abc123...   2 minutes ago   120MB
kairos       current    def456...   2 minutes ago   150MB
```

## ⚠️ Common issues and solutions

### Issue 1: "No such file or directory: 'docker/requirements.txt'"

**Cause:** The path in the Dockerfile was incorrect.

**Solution:** This issue has been fixed in the current version of Dockerfile.optimized. Make sure you're using the latest version.

### Issue 2: "Permission denied" during the build

**Solution:**
```bash
# Grant permissions on the Dockerfile
chmod +x docker/Dockerfile.optimized

# Or use sudo
sudo docker build -t kairos:optimized -f docker/Dockerfile.optimized .
```

### Issue 3: "ERROR: Could not open requirements file"

**Cause:** The requirements.txt file doesn't exist in the build context.

**Solution:** Verify that you're in the right directory and that the file exists:
```bash
ls -la docker/requirements.txt
```

### Issue 4: Dependency installation errors

**Solution:** Some dependencies may require system libraries. The optimized Dockerfile already includes:
- gcc
- musl-dev
- libpq-dev
- postgresql-dev

If you need other dependencies, edit the Dockerfile:
```dockerfile
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libpq-dev \
    postgresql-dev \
    # Add other dependencies here if needed
```

## 📊 Verifying the optimization

### 1. Check the multi-stage build

```bash
# View the image layers
docker history kairos:optimized
```

You should see that the final image doesn't contain the build dependencies (gcc, etc.).

### 2. Check the health check

```bash
# View the health status
docker inspect --format='{{json .State.Health}}' kairos-test
```

### 3. Check the user

```bash
# Verify the container runs as the non-root user
docker exec kairos-test whoami
# Should display: appuser
```

## 🎯 Next steps

Once you've confirmed the optimized Dockerfile works correctly:

1. **Replace the current Dockerfile** (optional):
   ```bash
   cp docker/Dockerfile.optimized docker/Dockerfile
   ```

2. **Update the Makefile** to use the new Dockerfile

3. **Push the changes** and merge the PR

## 📝 Notes

- The optimized Dockerfile uses **Alpine Linux** for a lighter image
- The **multi-stage build** reduces the final size by keeping only the necessary files
- The **health check** allows Kubernetes to monitor the container's health
- The **non-root user** improves security

If you have any questions or issues, feel free to ask!
