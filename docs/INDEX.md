# Saga Labs - Index

> **4-Repo System**: graph-functions, saga-be, saga-fe, victor_deployment  
> Quick lookup: "I want to do X" → "Look in Y"  
> **Keep this updated** when adding new functions or moving files.

---

## Quick Navigation

### I want to...

| Task | Location |
|------|----------|
| **Add a new API endpoint** | `saga-be/src/routes/` |
| **Add a new frontend page** | `saga-fe/src/routes/` |
| **Add a new agent** | `graph-functions/src/agents/analysis/` or `/strategy/` |
| **Add a new system function** | `graph-functions/src/functions/[name]/` |
| **Add a new LLM prompt** | With its function/agent, NOT in `/llm/prompts/` |
| **Query Neo4j** | `graph-functions/src/graph/ops/` |
| **Configure LLM routing** | `graph-functions/src/llm/router.py` |
| **Add external API client** | `graph-functions/src/clients/` |
| **Run a one-off script** | `graph-functions/scripts/` |
| **Deploy changes** | `victor_deployment/` |

---

## System Functions

These are the major capabilities of the system. Each lives in `graph-functions/src/functions/`.

| Function | Location | Description |
|----------|----------|-------------|
| **Ingest Article** | `src/articles/ingest_article.py` | Parse and store article in graph |
| **Classify Article** | `src/llm/classify_article.py` | Determine article category/relevance |
| **Find Related Topics** | `src/analysis/policies/topic_identifier.py` | Map article to relevant topics |
| **Evaluate Relevance** | `src/analysis/policies/relevance_gate.py` | Gate check for topic relevance |
| **Generate Analysis** | `src/agents/analysis/orchestrator.py` | Full analysis pipeline |
| **Generate Strategy** | `src/agents/strategy/orchestrator.py` | Strategy recommendations |

> **TODO**: Migrate these to `src/functions/` structure with co-located prompts/tests

---

## Agents

### Analysis Agents (`graph-functions/src/analysis_agents/`)

| Agent | Purpose |
|-------|---------|
| `critic/` | Critiques and improves analysis quality |
| `writer/` | Generates written analysis |
| `depth_finder/` | Finds deeper connections |
| `contrarian_finder/` | Identifies opposing viewpoints |
| `synthesis_scout/` | Synthesizes multiple sources |
| `source_checker/` | Validates source quality |
| `improvement_analyzer/` | Suggests improvements |

### Strategy Agents (`graph-functions/src/strategy_agents/`)

| Agent | Purpose |
|-------|---------|
| `risk_assessor/` | Evaluates risk factors |
| `opportunity_finder/` | Identifies opportunities |
| `position_analyzer/` | Analyzes current positions |
| `strategy_writer/` | Writes strategy recommendations |
| `topic_mapper/` | Maps topics to strategy |

---

## Graph Operations

All Neo4j operations live in `graph-functions/src/graph/`.

| File | Purpose |
|------|---------|
| `client.py` | Neo4j connection management |
| `models.py` | Graph node/relationship models |
| `ops/article.py` | Article CRUD operations |
| `ops/topic.py` | Topic CRUD operations |
| `ops/link.py` | Relationship operations |
| `ops/user_strategy.py` | User strategy storage |

---

## API Routes

### Public API (`saga-be/src/routes/`)

| Route | File | Purpose |
|-------|------|---------|
| `/articles` | `articles.py` | Article endpoints |
| `/strategies` | `strategies.py` | Strategy endpoints |
| `/users` | `users.py` | User management |
| `/admin` | `admin.py` | Admin operations |
| `/stats` | `stats.py` | System statistics |

### Internal API (`graph-functions/API/`)

| File | Purpose | Called By |
|------|---------|-----------|
| `graph_api.py` | Graph query endpoints | saga-be |
| `admin_api.py` | Admin graph operations | saga-be |

---

## LLM Configuration

| File | Purpose |
|------|---------|
| `src/llm/router.py` | Routes to appropriate model by task complexity |
| `src/llm/config.py` | Model configurations and endpoints |
| `src/llm/models.py` | Response type definitions |

### Prompt Locations

**Rule**: Prompts live WITH their function, not centralized.

| Type | Location |
|------|----------|
| Agent prompts | `src/agents/[type]/[agent]/prompt.py` |
| Function prompts | `src/functions/[name]/prompt.py` |
| Generic/shared only | `src/llm/prompts/` |

---

## External Clients

| Client | Location | Purpose |
|--------|----------|---------|
| Perigon | `src/clients/perigon/` | News API ingestion |
| AlphaVantage | `src/market_data/alphavantage_provider.py` | Market data |
| Yahoo Finance | `src/market_data/yahoo_provider.py` | Market data |

---

## Entrypoints (Main Workers)

Location: `graph-functions/entrypoints/` - Scripts that run continuously on servers.

| Script | Server | Purpose |
|--------|--------|---------|
| `ingest_articles.py` | 1 & 2 | Fetch & ingest articles from news APIs |
| `ingest_top_sources.py` | 1 & 2 | Premium source monitoring |
| `write_all.py` | 3 | Write topics + strategies (6am daily) |

**WORKER_MODE** env var controls behavior:
- `WORKER_MODE=ingest` - Servers 1 & 2: Only ingest, no writing
- `WORKER_MODE=write` - Server 3: Only write (use `write_all.py`)
- Unset - Local dev: Do everything

## Scripts (One-off Utilities)

Location: `graph-functions/scripts/` - Run manually when needed.

| Script | Purpose |
|--------|---------|
| `update_market_data.py` | Refresh market data for all topics |
| `maintenance/` | Cleanup & migration scripts |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `graph-functions/requirements.txt` | Python dependencies |
| `saga-be/requirements.txt` | Backend dependencies |
| `saga-fe/package.json` | Frontend dependencies |
| `victor_deployment/docker-compose.yml` | Container orchestration |

---

## Finding Things

### By file pattern

```bash
# Find all agents
find . -path "*/agents/*/agent.py"

# Find all prompts
find . -name "prompt.py"

# Find all tests
find . -name "test.py" -o -name "test_*.py"

# Find graph operations
ls graph-functions/src/graph/ops/
```

### By functionality

- **Anything Neo4j**: Start in `src/graph/`
- **Anything LLM**: Start in `src/llm/` or check agent's `prompt.py`
- **Anything user-facing**: Start in `saga-be/src/routes/`
- **Anything UI**: Start in `saga-fe/src/`

---

## Updating This Index

**When to update**:
- Adding new functions, agents, or routes
- Moving or renaming files
- Adding new external clients

**Format**: Keep tables aligned, descriptions brief.
