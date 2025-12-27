# Saga Feature Master Plan - January 2026

> **Status**: IN PROGRESS
> **Priority**: HIGH - Core feature completion
> **Philosophy**: MAXIMUM SIMPLICITY - No new infrastructure unless absolutely necessary

---

## COMPLETED FEATURES

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard Questions Bug | **DONE** | Removed `.slice(0, 3)` limit |
| Topic Findings Storage | **DONE** | `topic_findings.py` + Neo4j JSON properties |
| Exploration Trigger | **DONE** | `write_all.py` integration, runs BEFORE analysis |
| Model Tier Change | **DONE** | Exploration uses MEDIUM (120B) instead of COMPLEX |

---

## FEATURE 3: Vector Search (Qdrant + Perigon)

### Why Qdrant Over ChromaDB?

| Criteria | Qdrant | ChromaDB | Winner |
|----------|--------|----------|--------|
| **Filtering** | Excellent built-in filters (time, tier, topic) | Limited, requires workarounds | Qdrant |
| **Production Readiness** | Used by Discord, Dailymotion, Scale AI | More experimental, frequent breaking changes | Qdrant |
| **Persistence** | Native disk storage, ACID compliant | Requires sqlite config, has had data loss issues | Qdrant |
| **REST API** | Built-in, well-documented | Needs wrapper, inconsistent | Qdrant |
| **Performance at Scale** | Optimized for 10M+ vectors, HNSW index | Slower, designed for <1M vectors | Qdrant |
| **Memory Efficiency** | Supports on-disk storage + mmap | Primarily in-memory | Qdrant |
| **Time-based Queries** | Native datetime filtering | Requires workaround | Qdrant |
| **Docker Support** | Official image, production-ready | Works but less mature | Qdrant |

**Decision: Qdrant** - We need time-based filtering (recent articles) and reliable persistence.

### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Chat/Query    │────▶│  Saga Vector    │────▶│     Qdrant      │
│   Interface     │     │    Search       │     │   (Our Data)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │ Fallback if <3 results
                                 ▼
                        ┌─────────────────┐
                        │   Perigon API   │
                        │ (External Data) │
                        └─────────────────┘
```

### Docker Setup

**File: `victor_deployment/docker-compose.yml`**

Add Qdrant service to existing docker-compose:

```yaml
  # Vector Search Database
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: qdrant
    ports:
      - "6333:6333"   # REST API
      - "6334:6334"   # gRPC (optional, for performance)
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    networks:
      - network

# Add to volumes section:
volumes:
  qdrant_data:
    driver: local
```

**Environment variables to add:**
```bash
# .env
QDRANT_HOST=qdrant      # Docker service name
QDRANT_PORT=6333
OPENAI_API_KEY=xxx      # For embeddings (text-embedding-3-small)
```

### What Data Goes Into Qdrant?

**Only HIGH-QUALITY data (Tier 3 articles):**

```python
# Indexing criteria:
# 1. Article must be Tier 3 (relevant to at least one topic)
# 2. Article must have content (not just title)
# 3. Article linked within last 30 days (freshness)

# Schema stored in Qdrant:
{
    "id": "article_uuid",
    "vector": [0.1, 0.2, ...],  # 1536 dimensions (OpenAI)
    "payload": {
        "article_id": "uuid",
        "title": "Article Title",
        "summary": "Brief summary...",
        "content": "Full article text",  # For search context
        "url": "https://...",
        "source": "bloomberg.com",
        "published_date": "2026-01-15T10:00:00Z",
        "topics": ["US_Monetary_Policy", "Inflation"],
        "tier": 3,
        "indexed_at": "2026-01-15T12:00:00Z"
    }
}
```

**NOT indexed:**
- Tier 1 articles (just scraped, no topic relevance)
- Tier 2 articles (topic relevant but not high quality)
- Articles older than 30 days (archival, not active context)

### Code Structure

```
graph-functions/src/vector/
├── __init__.py
├── config.py           # Qdrant connection, OpenAI embedder config
├── embedder.py         # OpenAI text-embedding-3-small wrapper
├── qdrant_client.py    # Qdrant CRUD operations
├── indexer.py          # Index Tier 3 articles on ingestion
├── search.py           # High-level search (local + Perigon fallback)
└── test.py             # Tests
```

### File 1: `config.py`

```python
"""Vector search configuration."""
import os

# Qdrant settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "saga_articles"

# OpenAI Embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"  # $0.02/1M tokens, 1536 dims
EMBEDDING_DIMENSIONS = 1536

# Search settings
MAX_RESULTS = 10
MIN_SCORE = 0.7  # Minimum similarity score
FALLBACK_TO_PERIGON_THRESHOLD = 3  # If <3 local results, also search Perigon
```

### File 2: `embedder.py`

```python
"""OpenAI embeddings wrapper."""
from openai import OpenAI
from typing import List
from .config import OPENAI_API_KEY, EMBEDDING_MODEL

_client = None

def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def embed_text(text: str) -> List[float]:
    """Embed a single text string."""
    response = get_client().embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts in one API call (max 2048 texts)."""
    response = get_client().embeddings.create(
        input=texts,
        model=EMBEDDING_MODEL
    )
    return [item.embedding for item in response.data]
```

### File 3: `qdrant_client.py`

```python
"""Qdrant vector database operations."""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, Range
)
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBEDDING_DIMENSIONS

_client = None

def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client

def ensure_collection():
    """Create collection if it doesn't exist."""
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE
            )
        )

def upsert_article(article_id: str, vector: List[float], payload: Dict) -> bool:
    """Insert or update an article vector."""
    client = get_client()
    ensure_collection()

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(
            id=hash(article_id) % (2**63),  # Convert UUID to int
            vector=vector,
            payload={**payload, "article_id": article_id}
        )]
    )
    return True

def search(
    vector: List[float],
    limit: int = 10,
    topic_filter: Optional[str] = None,
    days_back: int = 30
) -> List[Dict]:
    """Search for similar articles."""
    client = get_client()

    # Build filters
    must_conditions = []

    # Time filter: only recent articles
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    must_conditions.append(
        FieldCondition(
            key="published_date",
            range=Range(gte=cutoff.isoformat())
        )
    )

    # Topic filter (optional)
    if topic_filter:
        must_conditions.append(
            FieldCondition(
                key="topics",
                match=MatchValue(value=topic_filter)
            )
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        query_filter=Filter(must=must_conditions) if must_conditions else None,
        limit=limit,
        with_payload=True
    )

    return [
        {**hit.payload, "score": hit.score}
        for hit in results
    ]

def delete_old_articles(days_to_keep: int = 30) -> int:
    """Delete articles older than X days."""
    client = get_client()
    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)

    # Count before
    # Delete using filter
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(
                key="published_date",
                range=Range(lt=cutoff.isoformat())
            )]
        )
    )
    return 0  # Qdrant doesn't return delete count easily
```

### File 4: `indexer.py`

```python
"""Index Tier 3 articles into Qdrant."""
from typing import Optional
from .embedder import embed_text
from .qdrant_client import upsert_article
from src.graph.neo4j_client import run_cypher
from utils import app_logging

logger = app_logging.get_logger(__name__)

def index_article(article_id: str) -> bool:
    """
    Index a single article if it's Tier 3.
    Called after article gets promoted to Tier 3.
    """
    # Get article details from Neo4j
    query = """
    MATCH (a:Article {id: $article_id})<-[r:ABOUT]-(t:Topic)
    WHERE r.tier = 3
    RETURN a.id AS id, a.title AS title, a.summary AS summary,
           a.content AS content, a.url AS url, a.source AS source,
           a.published_date AS published_date,
           collect(t.id) AS topics
    LIMIT 1
    """
    result = run_cypher(query, {"article_id": article_id})

    if not result:
        logger.debug(f"Article {article_id} not Tier 3, skipping index")
        return False

    article = result[0]

    # Skip if no content
    content = article.get("content") or article.get("summary") or ""
    if not content:
        logger.warning(f"Article {article_id} has no content, skipping")
        return False

    # Create embedding from title + summary + content snippet
    text_to_embed = f"{article.get('title', '')}. {article.get('summary', '')}. {content[:1000]}"

    try:
        vector = embed_text(text_to_embed)

        payload = {
            "title": article.get("title"),
            "summary": article.get("summary"),
            "content": content[:2000],  # Store first 2000 chars for context
            "url": article.get("url"),
            "source": article.get("source"),
            "published_date": str(article.get("published_date")),
            "topics": article.get("topics", []),
            "tier": 3
        }

        upsert_article(article_id, vector, payload)
        logger.info(f"Indexed article {article_id} into Qdrant")
        return True

    except Exception as e:
        logger.error(f"Failed to index article {article_id}: {e}")
        return False

def reindex_all_tier3(batch_size: int = 100) -> dict:
    """
    Reindex all Tier 3 articles. Run once after Qdrant setup.
    """
    from .embedder import embed_batch

    query = """
    MATCH (a:Article)<-[r:ABOUT]-(t:Topic)
    WHERE r.tier = 3
    WITH a, collect(DISTINCT t.id) AS topics
    RETURN a.id AS id, a.title AS title, a.summary AS summary,
           a.content AS content, a.url AS url, a.source AS source,
           a.published_date AS published_date, topics
    """
    articles = run_cypher(query, {})

    stats = {"indexed": 0, "skipped": 0, "failed": 0}

    # Process in batches for efficiency
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]

        texts = []
        valid_articles = []

        for article in batch:
            content = article.get("content") or article.get("summary") or ""
            if not content:
                stats["skipped"] += 1
                continue

            text = f"{article.get('title', '')}. {article.get('summary', '')}. {content[:1000]}"
            texts.append(text)
            valid_articles.append(article)

        if not texts:
            continue

        try:
            vectors = embed_batch(texts)

            for article, vector in zip(valid_articles, vectors):
                payload = {
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "content": (article.get("content") or "")[:2000],
                    "url": article.get("url"),
                    "source": article.get("source"),
                    "published_date": str(article.get("published_date")),
                    "topics": article.get("topics", []),
                    "tier": 3
                }
                upsert_article(article["id"], vector, payload)
                stats["indexed"] += 1

        except Exception as e:
            logger.error(f"Batch indexing failed: {e}")
            stats["failed"] += len(valid_articles)

    logger.info(f"Reindex complete: {stats}")
    return stats
```

### File 5: `search.py`

```python
"""High-level vector search with Perigon fallback."""
from typing import List, Dict, Optional
from .embedder import embed_text
from .qdrant_client import search as qdrant_search
from .config import MIN_SCORE, FALLBACK_TO_PERIGON_THRESHOLD
from src.clients.perigon.news_api_client import NewsApiClient
from utils import app_logging

logger = app_logging.get_logger(__name__)

def search_articles(
    query: str,
    limit: int = 10,
    topic_filter: Optional[str] = None,
    include_perigon: bool = True
) -> List[Dict]:
    """
    Search for articles using vector similarity.

    1. Search local Qdrant (our Tier 3 articles)
    2. If <3 results, also search Perigon (external articles)
    3. Deduplicate and return combined results

    Args:
        query: Natural language search query
        limit: Max results to return
        topic_filter: Optional topic ID to filter by
        include_perigon: Whether to fallback to Perigon

    Returns:
        List of article dicts with score
    """
    results = []

    # Step 1: Search local Qdrant
    try:
        query_vector = embed_text(query)
        local_results = qdrant_search(
            vector=query_vector,
            limit=limit,
            topic_filter=topic_filter
        )

        # Filter by minimum score
        local_results = [r for r in local_results if r.get("score", 0) >= MIN_SCORE]
        results.extend(local_results)

        logger.info(f"Local search found {len(local_results)} articles")

    except Exception as e:
        logger.warning(f"Local search failed: {e}")

    # Step 2: Fallback to Perigon if needed
    if include_perigon and len(results) < FALLBACK_TO_PERIGON_THRESHOLD:
        try:
            perigon = NewsApiClient()
            perigon_results = perigon.vector_search(query, max_results=limit)
            external_articles = perigon_results.get("articles", [])

            # Add source marker and normalize format
            for article in external_articles:
                article["source_type"] = "perigon"
                article["score"] = article.get("relevance", 0.8)  # Default score

            results.extend(external_articles)
            logger.info(f"Perigon search found {len(external_articles)} articles")

        except Exception as e:
            logger.warning(f"Perigon search failed: {e}")

    # Step 3: Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    return unique_results[:limit]
```

### Integration Point: When to Index

**Option A: Index on Tier 3 promotion (recommended)**

In `src/articles/ingest_article.py`, after article is linked as Tier 3:

```python
# After: create_about_relationship(article_id, topic_id, tier=3)
from src.vector.indexer import index_article
index_article(article_id)
```

**Option B: Batch index periodically**

Add to daily maintenance (e.g., 5am before analysis):

```python
from src.vector.indexer import reindex_all_tier3
reindex_all_tier3()
```

### Chat Tool Integration

```python
# In chat tool definitions:
{
    "name": "search_more_context",
    "description": "Search for additional articles when existing context doesn't answer the question",
    "parameters": {
        "query": {"type": "string", "description": "What to search for"}
    }
}

# Handler:
def search_more_context(query: str) -> str:
    from src.vector.search import search_articles
    results = search_articles(query, limit=5)

    if not results:
        return "No additional articles found."

    context = "Additional articles found:\n\n"
    for i, article in enumerate(results, 1):
        context += f"{i}. {article.get('title')}\n"
        context += f"   {article.get('summary', '')[:200]}\n\n"

    return context
```

---

## FEATURE 6: Analysis Integration (Use Findings in Writer)

### Current State

The exploration agent now runs BEFORE analysis and saves findings to Neo4j. But the analysis writer doesn't use these findings yet.

### Implementation

**File: `src/analysis_agents/orchestrator.py`**

Add findings context to material builder:

```python
def build_findings_context(topic_id: str) -> str:
    """Get formatted risks/opportunities for analysis context."""
    from src.graph.ops.topic_findings import get_topic_findings

    output = []
    risks = get_topic_findings(topic_id, "risk")
    opps = get_topic_findings(topic_id, "opportunity")

    if risks:
        output.append("\n## IDENTIFIED RISKS (from Exploration Agent)")
        for i, r in enumerate(risks, 1):
            output.append(f"\n### Risk {i}: {r.get('headline', 'Untitled')}")
            output.append(r.get('rationale', ''))
            if r.get('flow_path'):
                output.append(f"\nCausal chain: {r.get('flow_path')}")

    if opps:
        output.append("\n## IDENTIFIED OPPORTUNITIES (from Exploration Agent)")
        for i, o in enumerate(opps, 1):
            output.append(f"\n### Opportunity {i}: {o.get('headline', 'Untitled')}")
            output.append(o.get('rationale', ''))
            if o.get('flow_path'):
                output.append(f"\nCausal chain: {o.get('flow_path')}")

    return "\n".join(output) if output else ""
```

Then include in writer prompt:

```python
findings_context = build_findings_context(topic_id)
if findings_context:
    material += f"\n\n{findings_context}"
```

**Effort: 1 hour**

---

## FEATURE 5: Frontend Findings Display

### Approach: Reuse `<details>` Pattern

Same pattern as existing analysis sections. Add to strategy page.

**File: `saga-fe/src/routes/dashboard/+page.svelte`**

```svelte
{#if strategy.exploration_findings?.risks?.length > 0}
  <details class="analysis-card findings-risks">
    <summary class="analysis-card-header">
      <span class="analysis-card-title">Identified Risks ({strategy.exploration_findings.risks.length})</span>
      <span class="analysis-card-chevron">></span>
    </summary>
    <div class="analysis-card-content">
      {#each strategy.exploration_findings.risks as risk, i}
        <div class="finding-item">
          <h4>{i + 1}. {risk.headline}</h4>
          <p>{risk.rationale}</p>
          {#if risk.flow_path}
            <p class="flow-path"><strong>Causal chain:</strong> {risk.flow_path}</p>
          {/if}
        </div>
      {/each}
    </div>
  </details>
{/if}
```

**For Topics:** Need API endpoint to fetch topic findings from Neo4j.

---

## PRIORITY ORDER (Updated)

| Priority | Feature | Effort | Status |
|----------|---------|--------|--------|
| **1** | Dashboard Questions Bug | 5 min | **DONE** |
| **2** | Topic Findings Storage | 2-3 hrs | **DONE** |
| **2b** | Exploration Trigger | 1 hr | **DONE** |
| **3** | Test Perigon Vector Search | 15 min | **DONE** - test file created |
| **4** | Analysis Integration (use findings) | 1 hr | TODO |
| **5** | Vector Search (Qdrant setup) | 4-6 hrs | TODO |
| **6** | Chat Tool Integration | 2-3 hrs | TODO (needs #5) |
| **7** | Frontend Findings Display | 2-3 hrs | TODO |

---

## TEST COMMANDS

### Test Perigon Vector Search

```bash
cd graph-functions
python -m src.clients.perigon.test_vector_search
```

### Test Topic Findings Storage

```bash
cd graph-functions
python -m src.graph.ops.topic_findings
```

### Test Exploration Agent

```bash
cd graph-functions
python -m src.exploration_agent.orchestrator
```

---

## NEXT IMMEDIATE STEPS

1. **Run Perigon vector search test** to see what data we get
2. **Implement Feature 6** (Analysis Integration) - use findings in writer
3. **Set up Qdrant** in docker-compose
4. **Create vector module** for local article search
