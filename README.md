# 🚀 Saga Graph Deployment

**Docker Compose deployment for Saga Graph - real-time news intelligence platform with graph database, AI analysis, and premium source monitoring.**

---

## 📋 Quick Reference

| Scenario | Commands |
|----------|----------|
| **First time setup** | Step 1 (clone) → Step 2 (fresh start) → Step 3 (build & start) |
| **Daily shutdown** | Step 4 (safe shutdown) |
| **Daily startup** | Step 5 (safe startup) |
| **Changed nginx/env** | Step 6 (restart config) |
| **Changed code** | Step 7 (rebuild code) |
| **Major issues** | Step 2 (fresh start) → Step 3 (build & start) |

---

## 📋 Setup Instructions

### **Prerequisites**
- Git installed
- Docker & Docker Compose installed
- For DigitalOcean: Ubuntu 22.04 droplet with SSH access

---

## 🚀 Deploy Locally (Mac) or on Server

### **Step 1: Clone All Repos**

```bash
# Create project directory
mkdir saga-graph-project
cd saga-graph-project

# Clone all 4 repositories
git clone <saga-graph-repo-url> saga-graph
git clone <saga-be-repo-url> saga-be
git clone <frontend-repo-url> frontend
git clone <deployment-repo-url> deployment

# Verify structure
ls
# Should show: saga-graph  saga-be  frontend  deployment
```

**Final structure:**
```
saga-graph-project/
├── saga-graph/        # Worker code (main.py, main_top_sources.py)
├── saga-be/    # Backend API code
├── frontend/          # Svelte UI code
└── deployment/        # Docker configs (this folder)
```

---

### **Step 2: Fresh Start (Complete Reset)**

Use when: Neo4j password issues, major problems, or starting completely fresh.

```bash
cd deployment

# Stop and remove everything
docker-compose down -v --remove-orphans

# Remove all images
docker rmi deployment-saga-worker-main deployment-saga-worker-sources deployment-saga-apis deployment-frontend -f 2>/dev/null || true

# Clean build cache
docker builder prune -f

# Remove Neo4j data volume (resets password)
docker volume rm deployment_neo4j_data 2>/dev/null || true
```

---

### **Step 3: Build and Start (After Fresh Start)**

```bash
cd deployment

# Build all images from scratch
docker-compose build --no-cache --pull

# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

---

### **Step 4: Safe Shutdown**

```bash
cd deployment
docker-compose down
```

---

### **Step 5: Safe Startup**

```bash
cd deployment
docker-compose up -d
docker-compose ps
```

---

### **Step 6: Restart After Config Changes**

Use when: Changed nginx.conf, .env, or docker-compose.yml (no code changes).

```bash
cd deployment

# Restart specific service
docker-compose restart nginx              # After nginx.conf changes
docker-compose restart frontend           # After frontend env changes

# Or restart everything
docker-compose restart
```

---

### **Step 7: Rebuild After Code Changes**

Use when: Changed Python/JavaScript code in saga-graph, saga-be, or frontend.

```bash
cd deployment

# Rebuild specific service
docker-compose build saga-worker-main     # After saga-graph changes
docker-compose build saga-apis            # After saga-be changes
docker-compose build frontend             # After frontend changes

# Restart the rebuilt service
docker-compose up -d saga-worker-main

# Or rebuild everything
docker-compose build
docker-compose up -d
```

---

### **Step 8: Access Your System**

**Local (Mac):**
- Frontend: `http://localhost` (redirects to `/dashboard`)
- Neo4j Browser: `http://localhost:7474`
- Backend API: `http://localhost/api/`

**Server (DigitalOcean):**
- Frontend: `http://YOUR-DROPLET-IP` (redirects to `/dashboard`)
- Neo4j Browser: `http://YOUR-DROPLET-IP:7474`
- Backend API: `http://YOUR-DROPLET-IP/api/`

**Credentials:**
- Neo4j: `neo4j` / `SagaGraph2025!Demo`
- API Keys: See `nginx/nginx.conf` (lines 9-11)

---

## 📁 What's in This Directory

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates all 6 containers |
| `Dockerfile.workers` | Builds worker containers |
| `Dockerfile.apis` | Builds API container |
| `Dockerfile.frontend` | Builds frontend container |
| `start-main.sh` | Entry point for main worker |
| `start-top-sources.sh` | Entry point for sources worker |
| `start-apis.sh` | Entry point for APIs |
| `.env` | Environment variables (pre-configured) |
| `nginx/nginx.conf` | Reverse proxy + API keys (lines 9-11) |

---

## 🔄 Daily Operations

### **Start**
```bash
cd deployment
docker-compose up -d
```

### **Stop**
```bash
cd deployment
docker-compose down
```

### **Restart**
```bash
cd deployment
docker-compose restart
```

### **View Logs**
```bash
cd deployment

# All services
docker-compose logs -f

# Individual services
docker-compose logs -f saga-worker-main      # Main worker
docker-compose logs -f saga-worker-sources   # Sources worker
docker-compose logs -f saga-apis             # Backend + Graph APIs
docker-compose logs -f frontend              # Svelte frontend
docker-compose logs -f nginx                 # Nginx proxy
docker-compose logs -f neo4j                 # Neo4j database

# Multiple services
docker-compose logs -f saga-worker-main saga-worker-sources

# Last 50 lines only
docker-compose logs --tail=50 nginx
```

### **Check Status**
```bash
cd deployment
docker-compose ps
```

---

## 📊 System Architecture

### **6 Containers**

| Container | Purpose | Ports |
|-----------|---------|-------|
| **saga-neo4j** | Graph database | 7687 (Bolt), 7474 (Browser) |
| **saga-apis** | Backend + Graph APIs | 8000, 8001 |
| **saga-worker-main** | Main pipeline (main.py) | - |
| **saga-worker-sources** | Top sources (main_top_sources.py) | - |
| **saga-frontend** | Svelte UI | 5173 |
| **saga-nginx** | Reverse proxy + auth | 80 |

### **Why Two Workers?**

- **saga-worker-main**: 24/7 topic processing
- **saga-worker-sources**: Premium source ingestion

Separate containers allow independent scaling, isolated logs, and independent restarts

---

## 🔐 Authentication & Routing

### **How Requests Flow**

```
External Request
    ↓
Nginx (port 80) ← Checks X-API-Key
    ↓
Backend API (port 8000) ← No auth needed
    ↑
Workers ← Direct access, no key needed
```

### **Credentials (Single Source of Truth)**

**API Keys** - Configured in `nginx/nginx.conf` (lines 9-11):
```
785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12
a017a1af6fe167bdfcc554debb1c9a39e2ec75b93adde5a06d11e9a1361344f5
646b3c9454024ac1f4a2abad35cf1b8d02678b7c98d84059bde4109956adeeec
```

**Neo4j Password** - Configured in `.env`:
```
Username: neo4j
Password: SagaGraph2025!Demo
```

**Test API:**
```bash
curl -H "X-API-Key: 785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12" \
  http://localhost/api/articles
```

---

## 📊 Port Reference

| Port | Service | Access |
|------|---------|--------|
| 80 | Nginx | `http://localhost` |
| 7474 | Neo4j Browser | `http://localhost:7474` |
| 7687 | Neo4j Bolt | `bolt://localhost:7687` |
| 8000 | Backend API | Internal only |
| 8001 | Graph API | Internal only |
| 5173 | Frontend | Internal only |

---

## 🔌 Connect Neo4j Desktop

```
Protocol:    bolt://
URL:         localhost:7687
Username:    neo4j
Password:    SagaGraph2025!Demo
Database:    neo4j
```

After connecting, select `neo4j` database from dropdown (not `system`)

---

## 📝 Notes

- **API Keys**: `nginx/nginx.conf` lines 9-11 (single source of truth)
- **Neo4j Password**: `.env` file (`SagaGraph2025!Demo`)
- **Environment**: All config in `deployment/.env` (pre-configured)
- **Logs**: `docker-compose logs -f` to debug issues
- **Rebuild**: Run full rebuild commands if containers fail to start

---

**That's it! Simple, minimal, robust deployment.**
