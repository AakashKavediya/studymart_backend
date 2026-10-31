# Production Docker & AWS Deployment Guide: StudyMart Backend

This guide outlines the production Dockerization of the **StudyMart FastAPI Backend** and provides step-by-step instructions for local execution and deployment on **AWS EC2** (and container orchestration services such as Amazon ECS).

---

## 1. Architecture & Container Design

The container configuration is built using production-grade best practices tailored to the StudyMart FastAPI and MongoDB stack:

- **Base Image**: `python:3.13-slim` (matches runtime environment; minimal attack surface, ~150 MB base).
- **Multi-Stage Build**:
  - `builder` stage: Compiles packages and builds Python virtual environment (`/opt/venv`).
  - `runner` stage: Ships only the pre-built `/opt/venv`, application source code (`/app`), and minimal runtime libraries (`curl`, `ca-certificates`).
- **Non-Root Execution**: Runs under an unprivileged system user (`appuser`, UID/GID 1001) to protect the host against container breakout vulnerabilities.
- **Signal Handling & Graceful Shutdown**: `docker-entrypoint.sh` executes Uvicorn as `PID 1` using POSIX `exec`, ensuring immediate delivery of `SIGTERM` / `SIGINT` signals for graceful socket draining.
- **Port Flexibility**: The container port defaults to `8000` but is fully configurable via the `PORT` environment variable.
- **Native Health Checks**: Direct Docker `HEALTHCHECK` periodically probes the non-blocking root endpoint (`http://localhost:${PORT:-8000}/`) using `curl`.
- **Database Networking**: Pre-installs `ca-certificates` to support secure TLS handshakes with MongoDB Atlas (`mongodb+srv://`).

---

## 2. Generated Files & Purpose

| File | Purpose |
| :--- | :--- |
| `Dockerfile` | Multi-stage, production-hardened container specification with non-root security and healthcheck. |
| `.dockerignore` | Prevents local virtualenvs (`.venv`), git metadata, secrets (`.env`), and test caches from entering the build context. |
| `docker-entrypoint.sh` | Shell script ensuring environment variable evaluation (`PORT`), signal handling, and execution of `uvicorn app.main:app`. |
| `docker-compose.yml` | Multi-container orchestration specification for local development and staging environments. |
| `.env.example` | Complete environment variable template with documented safe placeholder values. |
| `DOCKER_DEPLOYMENT.md` | Comprehensive operational and AWS deployment documentation. |

---

## 3. Local Development & Testing

### Prerequisites
- Docker Engine 20.10+ & Docker Compose v2+
- Valid credentials in `.env` (copy from `.env.example`)

### Option A: Running with Docker Compose (Recommended)
```bash
# 1. Prepare environment variables
cp .env.example .env
# Edit .env and supply your MONGO_URI, SECRET_KEY, and GOOGLE_CLIENT_ID

# 2. Build and start in background
docker compose up -d --build

# 3. View real-time container logs
docker compose logs -f backend

# 4. Check container health status
docker compose ps

# 5. Stop containers and cleanup network
docker compose down
```

### Option B: Building & Running with Docker CLI Directly
```bash
# 1. Build the production image
docker build -t studymart-backend:latest .

# 2. Run the container with environment file
docker run -d \
  --name studymart-backend \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  studymart-backend:latest

# 3. Verify health status
docker ps --filter "name=studymart-backend"

# 4. Test endpoints
curl -I http://localhost:8000/
curl -s http://localhost:8000/products-test | jq .

# 5. Stop and remove container
docker stop studymart-backend && docker rm studymart-backend
```

---

## 4. Deploying to AWS EC2

### Step 1: Launch and Configure EC2 Instance
1. Launch an **Ubuntu 24.04 LTS** or **Amazon Linux 2023** instance (e.g. `t3.small` or `t3.medium`).
2. Configure **Security Group** inbound rules:
   - **SSH**: Port 22 (restricted to your IP).
   - **HTTP**: Port 80 (Anywhere `0.0.0.0/0`).
   - **HTTPS**: Port 443 (Anywhere `0.0.0.0/0`).
   - **Custom TCP (Optional direct test)**: Port 8000 (restricted to your IP).

### Step 2: Install Docker on EC2
SSH into the EC2 instance and install Docker Engine:
```bash
# Ubuntu
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow ec2-user / ubuntu to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Build & Push Image via AWS ECR (Elastic Container Registry)

From your local machine (or CI/CD runner):
```bash
# 1. Log in to your AWS ECR Registry (replace <account-id> and <region>)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Create the repository (if not already created)
aws ecr create-repository --repository-name studymart-backend --region us-east-1

# 3. Build multi-platform or target linux/amd64
docker build --platform linux/amd64 -t studymart-backend:latest .

# 4. Tag and push image
docker tag studymart-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/studymart-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/studymart-backend:latest
```

### Step 4: Run the Image on EC2

On your EC2 instance:
```bash
# 1. Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Pull the latest image
docker pull <account-id>.dkr.ecr.us-east-1.amazonaws.com/studymart-backend:latest

# 3. Create production .env directory (do not commit to Git)
mkdir -p /opt/studymart
cd /opt/studymart
nano .env   # Securely paste production credentials

# 4. Restrict .env permissions
chmod 600 .env

# 5. Start the production container
docker run -d \
  --name studymart-backend \
  --restart always \
  -p 127.0.0.1:8000:8000 \
  --env-file /opt/studymart/.env \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/studymart-backend:latest
```

---

## 5. HTTPS Termination & Reverse Proxy (Nginx + Let's Encrypt)

Exposing FastAPI directly to the internet is not recommended for production. Instead, bind the container to `127.0.0.1:8000` and use Nginx on the host for SSL/TLS termination and WebSocket proxying.

### 1. Install Nginx and Certbot
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 2. Configure Nginx (`/etc/nginx/sites-available/studymart`)
```nginx
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket & Socket.IO support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```
Enable the configuration:
```bash
sudo ln -s /etc/nginx/sites-available/studymart /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Issue SSL Certificate via Let's Encrypt
```bash
sudo certbot --nginx -d api.yourdomain.com
```

---

## 6. MongoDB Atlas Network Configuration

When deploying on AWS EC2:
1. Navigate to **MongoDB Atlas** -> **Network Access** -> **IP Access List**.
2. Add your EC2 Elastic IP address (or `0.0.0.0/0` with strong database user credentials and TLS enforced).
3. If using AWS VPC peering or AWS PrivateLink, add the dedicated VPC CIDR block.

---

## 7. Troubleshooting & Operational Runbook

### Inspecting Container Logs
```bash
# View last 100 log lines
docker logs --tail 100 studymart-backend

# Follow logs live
docker logs -f studymart-backend
```

### Container Health Probing
```bash
# Inspect container health JSON
docker inspect --format='{{json .State.Health}}' studymart-backend | jq .
```

### Common Issues & Resolutions

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| Container exits with code 1 | Missing mandatory environment variable (`SECRET_KEY`, `MONGO_URI`, or `GOOGLE_CLIENT_ID`) | Check `.env` and verify all required variables from `.env.example` are populated. |
| Healthcheck fails (`unhealthy`) | Uvicorn failing or port mismatch | Verify container port matches `PORT` env var (default `8000`). Inspect `docker logs studymart-backend`. |
| `pymongo.errors.ServerSelectionTimeoutError` | EC2 IP blocked by MongoDB Atlas | Whitelist the EC2 public Elastic IP in MongoDB Atlas Network Access. |
| Socket.IO messages not echoed | Running multiple uvicorn workers without Redis | Ensure single worker mode (`workers: 1`) or introduce Redis manager before horizontal scaling. |
