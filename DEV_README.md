# 🛠️ Local Development Guide

Simple Docker-based local development that matches production exactly.

---

## 🚀 Quick Start

### 1. Start Dev Environment
```bash
cd victor_deployment
chmod +x dev-start.sh
./dev-start.sh
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
./dev-start.sh
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
