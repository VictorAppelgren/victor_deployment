# Target Project Structure

This is what the project should look like after cleanup.

```
Saga_full_v2/
│
├── .gitignore                # Includes plans/
├── windsurfrules             # AI assistant coding rules
│
├── plans/                    # .gitignored - working documents
│   └── [dated-plan-files].md
│
├── graph-functions/          # ══════════ CORE ENGINE ══════════
│   ├── requirements.txt
│   ├── paths.py              # Path configuration
│   │
│   ├── entrypoints/          # ── Main worker scripts (run continuously) ──
│   │   ├── ingest_articles.py    # Server 1 & 2: Fetch & ingest articles
│   │   ├── ingest_top_sources.py # Server 1 & 2: Premium source monitoring
│   │   └── write_all.py          # Server 3: Write topics + strategies (6am daily)
│   │
│   ├── scripts/              # ── One-off utilities ──
│   │   ├── update_market_data.py # Refresh market data for topics
│   │   └── maintenance/          # Cleanup & migration scripts
│   │
│   ├── API/                  # ── Internal API (called by saga-be) ──
│   │   ├── graph_api.py
│   │   └── admin_api.py
│   │
│   └── src/
│       │
│       ├── agents/           # ── AI Agents ──
│       │   ├── analysis/     # Analysis agents
│       │   │   ├── critic/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── agent.py
│       │   │   │   ├── prompt.py
│       │   │   │   └── test.py        # Optional, for large tests
│       │   │   ├── writer/
│       │   │   ├── depth_finder/
│       │   │   ├── contrarian_finder/
│       │   │   ├── synthesis_scout/
│       │   │   ├── source_checker/
│       │   │   ├── improvement_analyzer/
│       │   │   ├── base_agent.py      # Analysis-specific base
│       │   │   └── orchestrator.py
│       │   │
│       │   └── strategy/     # Strategy agents
│       │       ├── risk_assessor/
│       │       ├── opportunity_finder/
│       │       ├── position_analyzer/
│       │       ├── strategy_writer/
│       │       ├── topic_mapper/
│       │       ├── base_agent.py      # Strategy-specific base
│       │       └── orchestrator.py
│       │
│       ├── functions/        # ── System Functions ──
│       │   │                 # (Major capabilities, co-located)
│       │   ├── ingest_article/
│       │   │   ├── __init__.py        # Main function + if __name__ test
│       │   │   ├── prompt.py          # LLM prompt
│       │   │   └── helpers.py         # Optional subfunctions
│       │   ├── classify_article/
│       │   ├── evaluate_relevance/
│       │   ├── find_topics/
│       │   ├── generate_analysis/
│       │   └── ...
│       │
│       ├── graph/            # ── Neo4j Operations ──
│       │   ├── __init__.py
│       │   ├── neo4j_client.py
│       │   ├── models.py
│       │   ├── config.py
│       │   ├── relationship_types.py
│       │   ├── ops/                   # CRUD operations
│       │   │   ├── article.py
│       │   │   ├── topic.py
│       │   │   ├── link.py
│       │   │   └── user_strategy.py
│       │   ├── policies/              # Business logic for graph
│       │   │   ├── link.py
│       │   │   ├── priority.py
│       │   │   └── topic.py
│       │   └── scheduling/
│       │       └── query_overdue.py
│       │
│       ├── llm/              # ── LLM Router & Config ──
│       │   ├── __init__.py
│       │   ├── llm_router.py          # Intelligence-based routing
│       │   ├── config.py
│       │   ├── models.py
│       │   ├── health_check.py
│       │   ├── sanitizer.py
│       │   └── prompts/               # ONLY generic/shared prompts
│       │       ├── system_prompts.py
│       │       └── citation_rules.py
│       │
│       ├── clients/          # ── External API Clients ──
│       │   └── perigon/
│       │       ├── __init__.py
│       │       ├── config.py
│       │       ├── news_api_client.py
│       │       ├── news_ingestion_orchestrator.py
│       │       └── test.py
│       │
│       ├── market_data/      # ── Market Data ──
│       │   ├── alphavantage_provider.py
│       │   ├── yahoo_provider.py
│       │   ├── models.py
│       │   ├── loader.py
│       │   └── neo4j_updater.py
│       │
│       ├── analysis/         # ── Analysis Utilities ──
│       │   ├── types.py
│       │   ├── citations/
│       │   ├── material/
│       │   ├── persistance/
│       │   ├── policies/
│       │   └── utils/
│       │
│       ├── articles/         # ── Article Processing ──
│       │   ├── ingest_article.py
│       │   ├── load_article.py
│       │   ├── article_text_formatter.py
│       │   └── orchestration/
│       │
│       ├── observability/    # ── Logging & Stats ──
│       │   └── stats_client.py
│       │
│       └── api/              # ── Internal utilities ──
│           └── backend_client.py
│
├── saga-be/                  # ══════════ BACKEND API ══════════
│   │                         # (FastAPI - PUBLIC facing)
│   ├── requirements.txt      # Python deps
│   ├── main.py               # FastAPI entrypoint
│   │
│   └── src/
│       ├── __init__.py
│       ├── routes/           # ── API Endpoints ──
│       │   ├── __init__.py
│       │   ├── articles.py
│       │   ├── strategies.py
│       │   ├── users.py
│       │   ├── admin.py
│       │   └── stats.py
│       │
│       └── storage/          # ── Data Layer ──
│           ├── __init__.py
│           ├── article_manager.py
│           ├── strategy_manager.py
│           └── user_manager.py
│
├── saga-fe/                  # ══════════ FRONTEND ══════════
│   │                         # (SvelteKit - standard structure)
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   │
│   └── src/
│       ├── lib/
│       │   ├── api/          # API client functions
│       │   ├── components/   # Svelte components
│       │   ├── stores/       # State management
│       │   └── utils/
│       │
│       └── routes/           # SvelteKit pages
│           ├── +layout.svelte
│           ├── +page.svelte
│           ├── dashboard/
│           ├── admin/
│           └── login/
│
└── victor_deployment/        # ══════════ DEPLOYMENT & CONFIG ══════════
    ├── .env.local            # ⭐ SINGLE SOURCE OF TRUTH - edit this!
    ├── dev.sh                # Generates .env files from .env.local
    ├── docker-compose.yml
    ├── README.md
    └── docs/                 # All documentation lives here
        ├── ARCHITECTURE.md
        ├── INDEX.md
        ├── NETWORKING.md
        └── TARGET_STRUCTURE.md
```

## Key Differences from Current State

| Current | Target | Why |
|---------|--------|-----|
| Scripts in `graph-functions/` root | `graph-functions/entrypoints/` | Clean root, clear what's runnable |
| `analysis_agents/` and `strategy_agents/` separate | `agents/analysis/` and `agents/strategy/` | Unified location |
| Prompts in `src/llm/prompts/` | With each function/agent | Co-location principle |
| Tests in `tests/` folder | `if __name__` or `test.py` co-located | Tests near code |
| TS files in `saga-be/` | Deleted | Python-only backend |
| No `plans/` directory | `plans/` (gitignored) | Structured planning |

## File Organization Rules

```
function_name/
├── __init__.py     # Main logic + docstring + if __name__ test
├── prompt.py       # LLM prompt (if uses LLM)
├── helpers.py      # Optional: subfunctions
└── test.py         # Optional: if tests are large

agent_name/
├── __init__.py     # Exports
├── agent.py        # Agent class
├── prompt.py       # Agent's prompt
├── graph_strategy.py  # Optional: graph queries
└── test.py         # Optional: if tests are large
```
