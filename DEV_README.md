# 🛠️ Local Development Guide

Simple Docker-based local development that matches production exactly.

---

## 📁 Which Docker Compose File?

**Two separate stacks:**

| File | Purpose | Command |
|------|---------|---------|
| `docker-compose.yml` | **Development/Server** | `docker compose up -d` |
| `docker-compose.local.yml` | **Local Backup** | `docker compose -f docker-compose.local.yml --env-file .env.local up -d` |

**Use `docker-compose.yml` for development, `docker-compose.local.yml` for backup.**

---

## 🚀 Quick Start

### 1. Start Dev Environment
```bash
cd victor_deployment
docker compose up -d neo4j saga-apis frontend nginx
```

This starts:
- ✅ Neo4j (database)
- ✅ Backend API (saga-apis)
- ✅ Frontend
- ✅ NGINX (routing)

### 2. Run Your Workers
```bash
# Terminal 1 - Main worker
cd graph-functions
python main.py

# Terminal 2 - Top sources worker (optional)
cd graph-functions
python main_top_sources.py
```

### 3. Access Your App
- **App:** http://localhost
- **Neo4j Browser:** http://localhost:7474

---

## 🔧 Rebuild Commands

### Backend + Graph API Changes (saga-apis)
```bash
# After editing saga-be OR graph-functions/API code:
docker compose build --no-cache saga-apis
docker compose restart saga-apis

# Verify new code loaded:
docker exec saga-apis grep "@app.post" /app/saga-be/main.py
docker exec saga-apis grep "admin_router" /app/graph-functions/API/graph_api.py

# View logs:
docker compose logs -f saga-apis
```

**Note:** `saga-apis` container runs BOTH Backend (port 8000) AND Graph API (port 8001)

### Frontend Changes (saga-frontend)
```bash
# After editing saga-fe code:
docker compose build --no-cache frontend
docker compose restart frontend

# View logs:
docker compose logs -f frontend
```

### Worker Changes (saga-worker-main)
```bash
# After editing graph-functions worker code:
docker compose build --no-cache saga-worker-main
docker compose restart saga-worker-main

# View logs:
docker compose logs -f saga-worker-main
```

### NGINX Changes (saga-nginx)
```bash
# After editing nginx/nginx.conf:
docker compose build --no-cache nginx
docker compose restart nginx

# View logs:
docker compose logs -f nginx
```

### Neo4j (saga-neo4j)
```bash
# Restart Neo4j:
docker compose restart neo4j

# View logs:
docker compose logs -f neo4j
```

**Note:** Code is baked into Docker images (no volume mounts), so always use `--no-cache` to ensure fresh build!

### Complete Rebuild (All Services)
```bash
# Stop everything
docker compose down

# Rebuild all images from scratch
docker compose build --no-cache

# Start all services
docker compose up -d

# Verify all running
docker compose ps
```

### Complete Rebuild + Local Backup Sync
```bash
# Rebuild main services
docker compose down
docker compose build --no-cache
docker compose up -d

# Start local backup sync (separate stack)
docker compose -f docker-compose.local.yml --env-file .env.local down
docker compose -f docker-compose.local.yml --env-file .env.local up -d

# Verify both stacks
docker compose ps
docker logs -f saga-sync
```

---

## 📝 Useful Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f saga-apis
docker compose logs -f frontend
docker compose logs -f neo4j
```

### Restart Without Rebuild
```bash
# Faster if no code changes, just restart
docker compose restart saga-apis
docker compose restart frontend
```

### Stop Everything
```bash
docker compose down
```

### Clean Restart (removes data)
```bash
docker compose down -v
docker compose up -d neo4j saga-apis frontend nginx
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using ports
lsof -i :80    # NGINX
lsof -i :8000  # Backend
lsof -i :7474  # Neo4j

# Stop conflicting services or change ports in docker-compose.yml
```

### Backend Not Responding
```bash
docker compose logs saga-apis
docker compose restart saga-apis
```

### Frontend Not Loading
```bash
docker compose logs frontend
docker compose restart frontend
```

### Neo4j Connection Issues
```bash
docker compose logs neo4j
# Wait a few seconds for Neo4j to fully start
```

### Clean Slate
```bash
docker compose down -v
docker system prune -f
./dev-start.sh
```

---

## ✅ This Setup Matches Production

Same:
- ✅ Docker images
- ✅ NGINX config
- ✅ Environment variables
- ✅ Network setup

**What works locally will work on the server!**

---

## 🔄 Local Backup Setup

**Purpose:** Mirror your production server to your local Mac for 100% backup.

### Why Docker-Managed Volumes?

We use **Docker-managed volumes** (NOT Mac filesystem mounts) because:

✅ **Mac-safe** - No permission issues with macOS filesystem  
✅ **Fast** - No macOS filesystem overhead  
✅ **Persistent** - Data survives rebuilds and `docker compose down`  
✅ **Clean** - No clutter in your Mac directories  

**How it works:**
- Docker stores volumes in its VM (not your Mac filesystem)
- Volumes persist even when containers are deleted
- Perfect for databases and large file storage

---

### Start Local Backup

```bash
# 1. Configure server IP (one-time)
cd victor_deployment
nano .env.local
# Set: SERVER_IP=your_server_ip

# 2. Start local backup stack
docker compose -f docker-compose.local.yml --env-file .env.local up -d

# 3. Watch sync (first sync takes 5-10 minutes)
docker logs -f saga-sync
```

**What gets backed up:**
- ✅ Neo4j graph database (all topics, articles, relationships, analysis)
- ✅ Article JSON files (full content)
- ✅ Master statistics
- ✅ Master logs

**Sync frequency:** Every 5 minutes automatically

---

### Access Local Backup

```bash
# Local Neo4j Browser
open http://localhost:7475
# Credentials: neo4j / SagaGraph2025!Demo

# Local Backend API
curl http://localhost:8002/api/health

# Check articles
curl http://localhost:8002/api/articles | jq length
```

---

### Manage Local Backup

```bash
# View logs
docker logs -f saga-sync
docker logs -f saga-local-neo4j
docker logs -f saga-local-backend

# Restart sync
docker compose -f docker-compose.local.yml restart saga-sync

# Stop backup (data persists)
docker compose -f docker-compose.local.yml down

# Restart backup (data intact)
docker compose -f docker-compose.local.yml --env-file .env.local up -d

# Check volume sizes
docker system df -v | grep local
```

---

### Persistent Data Volumes

**All data persists across rebuilds in Docker-managed volumes:**

| Volume | Contains | Size |
|--------|----------|------|
| `local_neo4j_data` | Graph database | ~100MB-1GB |
| `local_articles_data` | Article JSON files | ~10GB+ |
| `local_master_stats` | Statistics | ~10MB |
| `local_master_logs` | Pipeline logs | ~50MB |

**View volumes:**
```bash
docker volume ls | grep local
```

**Inspect volume:**
```bash
docker volume inspect victor_deployment_local_neo4j_data
```

---

### Backup Volumes to Mac

**Export volumes to Mac filesystem for external backup:**

```bash
cd ~/Desktop  # Or wherever you want backups

# Backup Neo4j database
docker run --rm \
  -v victor_deployment_local_neo4j_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/neo4j-backup-$(date +%Y%m%d).tar.gz /data

# Backup articles
docker run --rm \
  -v victor_deployment_local_articles_data:/articles \
  -v $(pwd):/backup \
  alpine tar czf /backup/articles-backup-$(date +%Y%m%d).tar.gz /articles

# Backup stats
docker run --rm \
  -v victor_deployment_local_master_stats:/stats \
  -v $(pwd):/backup \
  alpine tar czf /backup/stats-backup-$(date +%Y%m%d).tar.gz /stats
```

**Result:** Compressed `.tar.gz` files on your Desktop that you can:
- Copy to external drive
- Upload to cloud storage
- Archive for safekeeping

---

### Restore Volumes from Backup

**Restore from previously exported backups:**

```bash
cd ~/Desktop  # Where your backup files are

# Restore Neo4j database
docker run --rm \
  -v victor_deployment_local_neo4j_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/neo4j-backup-20250113.tar.gz -C /"

# Restore articles
docker run --rm \
  -v victor_deployment_local_articles_data:/articles \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /articles/* && tar xzf /backup/articles-backup-20250113.tar.gz -C /"

# Restart containers to use restored data
docker compose -f docker-compose.local.yml restart
```

---

### Clean Slate (Delete All Local Data)

**Warning:** This deletes all local backup data!

```bash
# Stop containers
docker compose -f docker-compose.local.yml down

# Delete volumes
docker volume rm victor_deployment_local_neo4j_data
docker volume rm victor_deployment_local_articles_data
docker volume rm victor_deployment_local_master_stats
docker volume rm victor_deployment_local_master_logs

# Restart (will create fresh empty volumes)
docker compose -f docker-compose.local.yml --env-file .env.local up -d

# Sync will repopulate from server
docker logs -f saga-sync
```

---

### Troubleshooting Local Backup

**Sync not working:**
```bash
# Check sync logs
docker logs saga-sync --tail 100

# Check if local Neo4j is running
docker ps | grep saga-local-neo4j

# Check if can connect to server
curl http://YOUR_SERVER_IP/api/health
```

**Neo4j connection issues:**
```bash
# Check Neo4j logs
docker logs saga-local-neo4j

# Check Neo4j is healthy
docker inspect saga-local-neo4j | grep Health -A 10

# Restart Neo4j
docker compose -f docker-compose.local.yml restart local-neo4j
```

**Articles not syncing:**
```bash
# Check backend logs
docker logs saga-local-backend

# Test backend API
curl http://localhost:8002/api/health

# Restart backend
docker compose -f docker-compose.local.yml restart local-backend
```

---

### Port Reference

**Server (Production):**
- Neo4j: `7687` (Bolt), `7474` (Browser)
- Backend: `8000` (API), `8001` (Graph API)

**Local Backup:**
- Neo4j: `7688` (Bolt), `7475` (Browser)
- Backend: `8002` (API), `8003` (Graph API)

**No port conflicts!** Both can run simultaneously.
