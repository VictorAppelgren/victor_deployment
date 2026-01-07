# Saga MCP Server

Remote development access for Claude Code. Gives AI assistants direct access to the production server for debugging, deployment, and monitoring.

## Quick Start

### Deploy to Server

```bash
# On the server, pull changes and rebuild
cd /opt/saga-graph/victor_deployment
git pull
docker compose build mcp-server
docker compose up -d mcp-server
docker compose restart nginx
```

### Test the Connection

```bash
# Health check (no auth required)
curl https://sagalabs.world/mcp/health

# Status check (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" https://sagalabs.world/mcp/status
```

## Available Tools

### Log Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/read_log` | POST | Read logs from a Docker service |
| `/mcp/tools/search_logs` | POST | Search logs for a pattern across services |
| `/mcp/tools/tail_logs/{service}` | GET | Get most recent logs (for polling) |

**Example: Read Worker Logs**
```bash
curl -X POST https://sagalabs.world/mcp/tools/read_log \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"service": "worker-main", "lines": 200}'
```

**Example: Search for Errors**
```bash
curl -X POST https://sagalabs.world/mcp/tools/search_logs \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "ERROR|Exception", "since": "1h"}'
```

### File Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/read_file` | POST | Read a file from the server |
| `/mcp/tools/search_files` | POST | Search for files by name pattern |
| `/mcp/tools/grep` | POST | Search file contents for a pattern |
| `/mcp/tools/list_directory` | POST | List directory contents |

**Example: Read a Config File**
```bash
curl -X POST https://sagalabs.world/mcp/tools/read_file \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"path": "/opt/saga-graph/graph-functions/src/llm/config.py"}'
```

**Example: Search for Python Files**
```bash
curl -X POST https://sagalabs.world/mcp/tools/search_files \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "*.py", "path": "/opt/saga-graph/graph-functions/src/agents"}'
```

**Example: Grep for a Pattern**
```bash
curl -X POST https://sagalabs.world/mcp/tools/grep \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "def ingest_article", "path": "/opt/saga-graph", "file_pattern": "*.py"}'
```

### Deployment Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/deploy_service` | POST | Git pull + build + restart a service |
| `/mcp/tools/restart_service` | POST | Restart a Docker service |
| `/mcp/tools/docker_status` | GET | Get status of all Docker containers |

**Example: Deploy Frontend**
```bash
curl -X POST https://sagalabs.world/mcp/tools/deploy_service \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"service": "frontend", "pull": true, "no_cache": true}'
```

**Example: Restart a Service**
```bash
curl -X POST https://sagalabs.world/mcp/tools/restart_service \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"service": "apis"}'
```

**Example: Check Docker Status**
```bash
curl https://sagalabs.world/mcp/tools/docker_status \
  -H "X-API-Key: YOUR_KEY"
```

### Git Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/git` | POST | Run git operations on a repo |

**Example: Check Git Status**
```bash
curl -X POST https://sagalabs.world/mcp/tools/git \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"repo": "saga-fe", "command": "status"}'
```

**Example: View Recent Commits**
```bash
curl -X POST https://sagalabs.world/mcp/tools/git \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"repo": "graph-functions", "command": "log"}'
```

### Database Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/query_neo4j` | POST | Execute a Cypher query (read-only) |

**Example: Count Topics**
```bash
curl -X POST https://sagalabs.world/mcp/tools/query_neo4j \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (t:Topic) RETURN count(t) as count"}'
```

**Example: Get Recent Articles**
```bash
curl -X POST https://sagalabs.world/mcp/tools/query_neo4j \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (a:Article) RETURN a.title, a.published_at ORDER BY a.published_at DESC LIMIT 10"}'
```

### Graph Inspection Tools

High-level tools for exploring the knowledge graph without writing Cypher.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/graph_stats` | GET | Get overview stats (topics, articles, relationships) |
| `/mcp/tools/all_topics` | GET | List all topics with article counts |
| `/mcp/tools/topic_details` | POST | Get full topic info with context |
| `/mcp/tools/topic_articles` | POST | Get articles for a topic with perspectives |
| `/mcp/tools/recent_articles` | GET | Get recently ingested articles |

**Example: Get Graph Stats**
```bash
curl https://sagalabs.world/mcp/tools/graph_stats \
  -H "X-API-Key: YOUR_KEY"
```

**Example: List All Topics**
```bash
curl https://sagalabs.world/mcp/tools/all_topics \
  -H "X-API-Key: YOUR_KEY"
```

**Example: Get Topic Details**
```bash
curl -X POST https://sagalabs.world/mcp/tools/topic_details \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic_id": "topic_us_monetary_policy"}'
```

**Example: Get Articles for Topic**
```bash
curl -X POST https://sagalabs.world/mcp/tools/topic_articles \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic_id": "topic_us_monetary_policy", "limit": 10}'
```

**Example: Get Recent Articles**
```bash
curl "https://sagalabs.world/mcp/tools/recent_articles?limit=20&hours=24" \
  -H "X-API-Key: YOUR_KEY"
```

### Strategy Tools

Tools for reading user strategies via the internal API.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/list_users` | GET | List all users |
| `/mcp/tools/user_strategies` | POST | Get strategies for a user |
| `/mcp/tools/strategy_analysis` | POST | Get analysis for a strategy |
| `/mcp/tools/strategy_topics` | POST | Get topics for a strategy |

**Example: List Users**
```bash
curl https://sagalabs.world/mcp/tools/list_users \
  -H "X-API-Key: YOUR_KEY"
```

**Example: Get User Strategies**
```bash
curl -X POST https://sagalabs.world/mcp/tools/user_strategies \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"username": "victor"}'
```

**Example: Get Strategy Analysis**
```bash
curl -X POST https://sagalabs.world/mcp/tools/strategy_analysis \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "strategy_123"}'
```

**Example: Get Strategy Topics**
```bash
curl -X POST https://sagalabs.world/mcp/tools/strategy_topics \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "strategy_123"}'
```

### Action Tools (Guarded)

Tools that modify data. Require confirmation and log all actions.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/hide_article` | POST | Soft-delete an article (sets status=hidden) |
| `/mcp/tools/trigger_analysis` | POST | Trigger re-analysis for a topic |

**Example: Hide an Article**
```bash
curl -X POST https://sagalabs.world/mcp/tools/hide_article \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"article_id": "art_abc123", "reason": "Irrelevant to topic", "confirm": true}'
```

**Example: Trigger Topic Analysis**
```bash
curl -X POST https://sagalabs.world/mcp/tools/trigger_analysis \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic_id": "topic_us_monetary_policy", "confirm": true}'
```

**Note on Action Tools:**
- `confirm: true` is required for all action tools
- All actions are logged with timestamp and reason
- `hide_article` is a soft-delete (article can be restored)
- `trigger_analysis` uses the existing analysis pipeline

### System Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/system_health` | GET | Get CPU, memory, disk status |
| `/mcp/tools/daily_stats` | GET | Get daily stats from backend API |
| `/mcp/tools/run_command` | POST | Run limited safe commands |

**Example: System Health**
```bash
curl https://sagalabs.world/mcp/tools/system_health \
  -H "X-API-Key: YOUR_KEY"
```

**Example: Daily Stats**
```bash
curl https://sagalabs.world/mcp/tools/daily_stats \
  -H "X-API-Key: YOUR_KEY"
```

## Allowed Services

The following Docker services can be managed:
- `frontend` - SvelteKit frontend
- `apis` - FastAPI backend
- `worker-main` - Main article ingestion worker
- `worker-sources` - Top sources worker
- `neo4j` - Neo4j database
- `nginx` - Reverse proxy
- `qdrant` - Vector database
- `mcp-server` - This server

## Allowed Repos

Git operations work on:
- `saga-fe` - Frontend
- `saga-be` - Backend
- `graph-functions` - Core engine
- `victor_deployment` - Deployment configs

## Security

### Authentication
Uses the same API keys as the rest of the system (X-API-Key header).

### File Access
- Read-only access to `/opt/saga-graph`
- Blocked patterns: `.env`, `credentials`, `secrets`, `.pem`, `.key`, `password`, `.ssh`

### Database Access
- Read-only Cypher queries only
- Write operations (CREATE, MERGE, DELETE, SET) are blocked

### Command Restrictions
Only whitelisted commands allowed via `run_command`:
- `docker ps`, `docker logs`, `docker inspect`, `docker stats`
- `df -h`, `free`, `uptime`, `ps aux`, `netstat -tlnp`
- `ls`, `head`, `tail`, `cat /proc/`, `wc -l`

## Troubleshooting

### MCP Server Not Starting
```bash
# Check logs
docker logs mcp-server

# Check if Docker socket is accessible
docker exec mcp-server docker ps
```

### 401 Unauthorized
- Verify API key is correct
- Check NGINX is routing `/mcp/` correctly
- Test with: `curl -v -H "X-API-Key: YOUR_KEY" https://sagalabs.world/mcp/status`

### File Access Denied
- File may be outside `/opt/saga-graph`
- File may match blocked pattern (e.g., `.env`)
- Check path is absolute

### Deployment Timeout
- Build operations can take up to 10 minutes
- NGINX proxy_read_timeout is set to 600s
- Check `docker_status` to see if build is still running

## Architecture

```
Your Mac (Claude Code)
    │
    │ HTTPS + X-API-Key header
    ▼
NGINX (Port 443)
    │ /mcp/* routes
    ▼
MCP Server (Port 8002)
    │
    ├── Docker Socket (/var/run/docker.sock)
    ├── Codebase (/opt/saga-graph) [read-only]
    └── Backend API (http://apis:8000)
```

## Adding New Tools

Edit `server.py` and add:
1. A Pydantic model for the request (if needed)
2. A new endpoint function with `@app.post("/mcp/tools/your_tool")`
3. Add the `dependencies=[Depends(verify_api_key)]` decorator
4. Document it in this README

Then rebuild:
```bash
docker compose build mcp-server && docker compose up -d mcp-server
```
