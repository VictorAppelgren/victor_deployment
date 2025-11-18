# 🛠️ Local Development Guide

Two ways to develop: **Python workers** (fast) or **Full Docker** (testing).

---

## 🚀 Quick Start - Local Development (Recommended)

**Single command - instant code changes:**

```bash
cd victor_deployment
./dev.sh
```

**What it does:**
- ✅ Starts local Neo4j backup (Docker)
- ✅ Starts background sync from server
- ✅ Sets up Python venv
- ✅ Drops you in terminal ready to code

**Run your worker:**
```bash
python main.py
```

**Make changes:**
- Edit code → Ctrl+C → `python main.py` → Changes apply instantly!

**View synced data:**
```bash
ls -lh master_stats/              # Stats from server
tail -f master_logs/*.log         # Logs from server
tail -f ../victor_deployment/sync.log  # Sync status
```

**Switch target:**
```bash
# Edit .env.local
WORKER_TARGET=server  # Work on production (default)
WORKER_TARGET=local   # Work on local backup

# Restart
./dev.sh
```

---

## 🐳 Full Docker Stack (Testing Only)

**When to use:** Testing complete system, debugging frontend/backend integration.

**Start everything:**
```bash
cd victor_deployment
docker compose up -d
```

**Access:**
- App: http://localhost
- Neo4j: http://localhost:7474
- Backend API: http://localhost:8000

**Rebuild after changes:**
```bash
# Backend/Graph API
docker compose build --no-cache saga-apis
docker compose restart saga-apis

# Frontend
docker compose build --no-cache frontend
docker compose restart frontend

# Workers
docker compose build --no-cache saga-worker-main
docker compose restart saga-worker-main
```

**Stop:**
```bash
docker compose down
```

---

## 🔄 Background Sync

**What gets synced from server:**
- Neo4j graph (full backup)
- Articles (bidirectional)
- Stats files
- Log files (last 7 days)

**Frequency:** Every 5 minutes

**Monitor:**
```bash
tail -f ../victor_deployment/sync.log
```

**Stop sync:**
```bash
kill $(cat ../victor_deployment/sync.pid)
```

---

## 📊 Access Points

**Local Development (dev.sh):**
- Worker connects to: Production server (167.172.185.204)
- Local backup Neo4j: http://localhost:7475
- Stats/Logs: Direct filesystem (`master_stats/`, `master_logs/`)

**Full Docker Stack:**
- App: http://localhost
- Neo4j: http://localhost:7474
- Backend API: http://localhost:8000

---

## 🐛 Quick Troubleshooting

**Sync not working:**
```bash
tail -f ../victor_deployment/sync.log
kill $(cat ../victor_deployment/sync.pid)
./dev.sh
```

**Worker can't connect:**
```bash
# Check target
cat ../victor_deployment/.env.local | grep WORKER_TARGET

# Verify server
curl http://167.172.185.204/api/health
```

**Port conflict:**
```bash
lsof -i :7688  # Local Neo4j
docker stop saga-local-neo4j
./dev.sh
```

---

## ✅ Summary

**Daily Development:**
```bash
./dev.sh → python main.py
```

**Testing Full Stack:**
```bash
docker compose up -d
```

**Simple, fast, matches production!** 🚀
