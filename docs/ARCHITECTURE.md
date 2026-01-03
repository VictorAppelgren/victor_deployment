# Saga Labs - System Architecture

> **4-Repo System**: graph-functions, saga-be, saga-fe, victor_deployment  
> **Last Updated**: 2025-12-18  
> **For AI Assistants**: Read this file AND `INDEX.md` before any code changes

---

## Mission

Saga scales human intuition beyond human limits. We build intelligence infrastructure that maps global risks and opportunities through a knowledge graph, powered by AI agents that read, analyze, and surface chain reactions others miss.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL WORLD                               │
│  (News APIs, Market Data, User Requests)                            │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        saga-fe (SvelteKit)                          │
│  Frontend - Dashboard, Admin, User Interface                        │
│  Location: /saga-fe                                                 │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      saga-be (FastAPI) - PUBLIC API                 │
│  Routes: /articles, /strategies, /users, /admin, /stats             │
│  Location: /saga-be                                                 │
│  This is the ONLY external-facing API                               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ Internal calls (Python imports)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  graph-functions - CORE ENGINE                      │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Agents    │  │  Functions  │  │    LLM      │                 │
│  │  /agents/   │  │ /functions/ │  │   Router    │                 │
│  │             │  │             │  │   /llm/     │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          ▼                                          │
│                   ┌─────────────┐                                   │
│                   │    Graph    │                                   │
│                   │   /graph/   │                                   │
│                   │   Neo4j     │                                   │
│                   └─────────────┘                                   │
│                                                                     │
│  Internal API: /API/ (graph_api.py, admin_api.py)                  │
│  These are called BY saga-be, not externally                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      victor_deployment                              │
│  Docker Compose, deployment configs                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

### `/saga-fe` - Frontend (SvelteKit)
```
saga-fe/
├── src/
│   ├── lib/
│   │   ├── api/           # API client functions
│   │   ├── components/    # Svelte components
│   │   └── stores/        # State management
│   └── routes/            # SvelteKit routes (pages + API endpoints)
├── svelte.config.js
└── package.json
```
**Status**: Clean, follows SvelteKit conventions.

---

### `/saga-be` - Backend API (FastAPI)
```
saga-be/
├── main.py                # FastAPI app entrypoint
├── requirements.txt       # Python dependencies
└── src/
    ├── routes/            # API route handlers
    │   ├── articles.py
    │   ├── strategies.py
    │   ├── users.py
    │   ├── admin.py
    │   └── stats.py
    └── storage/           # Data persistence layer
        ├── article_manager.py
        ├── strategy_manager.py
        └── user_manager.py
```
**Role**: Public-facing API. Calls `graph-functions` internally.

**Status**: Clean Python-only repo.

---

### `/graph-functions` - Core Engine
```
graph-functions/
├── requirements.txt
│
├── entrypoints/              # Main worker scripts (run continuously)
│   ├── ingest_articles.py    # Server 1 & 2: Fetch & ingest articles
│   ├── ingest_top_sources.py # Server 1 & 2: Premium source monitoring
│   └── write_all.py          # Server 3: Write topics + strategies (6am daily)
│
├── scripts/                  # One-off utilities
│   ├── update_market_data.py
│   └── maintenance/
│
├── API/                      # INTERNAL API (called by saga-be)
│   ├── graph_api.py
│   └── admin_api.py
│
└── src/
    ├── agents/               # AI Agents
    │   ├── analysis/         # Analysis agents (critic, writer, etc.)
    │   │   └── [agent]/
    │   │       ├── agent.py
    │   │       ├── prompt.py
    │   │       └── test.py   # if __name__ == "__main__" tests
    │   ├── strategy/         # Strategy agents
    │   │   └── [agent]/
    │   │       ├── agent.py
    │   │       ├── prompt.py
    │   │       └── test.py
    │   └── orchestrator.py
    │
    ├── functions/            # System Functions (major capabilities)
    │   └── [function_name]/
    │       ├── __init__.py   # Main logic + if __name__ test
    │       ├── prompt.py     # LLM prompt if needed
    │       └── helpers.py    # Optional subfunctions
    │
    ├── graph/                # Neo4j operations
    │   ├── client.py         # Neo4j connection
    │   ├── models.py         # Graph data models
    │   ├── config.py
    │   └── ops/              # Graph operations
    │       ├── article.py
    │       ├── topic.py
    │       ├── link.py
    │       └── user_strategy.py
    │
    ├── llm/                  # LLM Router & Config
    │   ├── router.py         # Intelligence-based routing
    │   ├── config.py         # Model configs
    │   ├── models.py         # Response types
    │   └── prompts/          # ONLY generic/shared prompts
    │       └── system_prompts.py
    │
    ├── clients/              # External API clients
    │   └── perigon/          # News API
    │
    ├── market_data/          # Market data ingestion
    │
    └── scripts/              # One-off maintenance scripts
        └── maintenance/
```

---

### `/victor_deployment` - Deployment & Configuration
```
victor_deployment/
├── .env.local                # ⭐ SINGLE SOURCE OF TRUTH - edit this!
├── dev.sh                    # Generates .env files from .env.local
├── docker-compose.yml
├── README.md
└── docs/                     # All documentation
    ├── ARCHITECTURE.md
    ├── INDEX.md
    ├── NETWORKING.md
    └── TARGET_STRUCTURE.md
```

**Configuration Flow:**
1. Edit `.env.local` (change `SERVER_DOMAIN=sagalabs.world`)
2. Run `./dev.sh`
3. All `.env` files regenerated automatically

---

## API Layers (Important!)

| Layer | Location | Purpose | Called By |
|-------|----------|---------|-----------|
| **Public API** | `saga-be/src/routes/` | User-facing endpoints | Frontend, external clients |
| **Internal API** | `graph-functions/API/` | Graph operations | saga-be only |

**Rule**: External traffic → saga-be → graph-functions. Never call graph-functions directly from outside.

---

## Data Flow Examples

### 1. User Views Dashboard
```
Frontend → saga-be/routes/strategies.py → graph-functions/API/graph_api.py → Neo4j
```

### 2. Article Ingestion
```
Perigon API → graph-functions/src/clients/perigon/ 
           → graph-functions/src/functions/ingest_article/
           → graph-functions/src/graph/ops/article.py
           → Neo4j
```

### 3. Analysis Generation
```
User request → saga-be → graph-functions/src/agents/analysis/orchestrator.py
            → Multiple agents (critic, writer, etc.)
            → Each agent uses LLM router
            → Results saved to Neo4j
```

---

## Key Technologies

| Component | Technology |
|-----------|------------|
| Frontend | SvelteKit, TypeScript |
| Backend API | FastAPI, Python |
| Core Engine | Python |
| Graph Database | Neo4j (Cypher queries) |
| Vector Database | Qdrant |
| LLM | Multi-model router (local + cloud) |
| Deployment | Docker Compose |
| Configuration | `.env.local` → `dev.sh` → generated `.env` |

---

## Conventions

### File Organization
- **Prompts**: Live with their function/agent, NOT in central `/prompts/` folder
- **Tests**: `if __name__ == "__main__":` block in main file, OR `test.py` in same folder
- **Types**: Use Pydantic models for all LLM responses

### Naming
- Python: `snake_case` for files, functions, variables
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

### Code Style
- **Simplest possible code** - no clever abstractions
- **Fail fast** - no silent `try/except` unless absolutely necessary
- **Explicit over implicit** - clear variable names, obvious flow

---

## TODOs / Technical Debt

- [x] ~~Remove all `.ts` files from `saga-be/`~~ ✅ Done
- [ ] Consolidate `analysis_agents/base_agent.py` and `strategy_agents/base_agent.py` into single base
- [ ] Move root-level scripts in `graph-functions/` to `entrypoints/`
- [ ] Migrate remaining tests from `graph-functions/tests/` to co-located `test.py` files
- [ ] Move prompts from `src/llm/prompts/` to their respective functions/agents

---

## Updating This Document

**When to update**:
- Adding new repos or major folders
- Changing API boundaries
- Adding new agent types
- Changing data flow patterns

**AI Assistants**: After making structural changes, update this file and `INDEX.md`.
