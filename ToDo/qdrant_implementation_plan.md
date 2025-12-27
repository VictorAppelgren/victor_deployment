# Qdrant Implementation Plan - Complete Details

> **Goal**: Local vector search for OUR Tier 3 articles
> **Philosophy**: SIMPLE - one file does one thing, automatic sync, zero maintenance

---

## WHY QDRANT?

We already have Perigon vector search (external news). Qdrant adds:
- Search OUR curated Tier 3 articles (higher quality than raw Perigon)
- Filter by topic, timeframe, perspective
- No API rate limits - it's local
- Combined search: Local first, Perigon fallback

---

## ARCHITECTURE

```
User Query
    ↓
1. Search Qdrant (our Tier 3 articles, 14 days)
    ↓
2. If < 3 results → Also search Perigon
    ↓
3. Deduplicate by URL
    ↓
4. Return combined results
```

**Sync Strategy**: Index article when it becomes Tier 3. That's it.

---

## STEP 1: Docker Setup

**File: `victor_deployment/docker-compose.yml`**

Add after neo4j service:

```yaml
  # Vector Search Database
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    networks:
      - network
```

Add to volumes section:

```yaml
volumes:
  qdrant_data:
    driver: local
```

**File: `victor_deployment/.env`**

Add:

```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
OPENAI_API_KEY=sk-xxx  # For embeddings
```

---

## STEP 2: Create Vector Module

### File Structure

```
graph-functions/src/vector/
├── __init__.py
├── client.py      # Qdrant connection + CRUD
├── embedder.py    # OpenAI embeddings
├── indexer.py     # Index Tier 3 articles
└── search.py      # Search with Perigon fallback
```

---

### File: `graph-functions/src/vector/__init__.py`

```python
"""Vector search module for Saga articles."""
from .search import search_articles
from .indexer import index_article

__all__ = ["search_articles", "index_article"]
```

---

### File: `graph-functions/src/vector/client.py`

```python
"""Qdrant client - connection and basic operations."""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, Range
)
from utils.app_logging import get_logger

logger = get_logger(__name__)

# Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION = "saga_articles"
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small

_client = None


def get_client() -> QdrantClient:
    """Get or create Qdrant client."""
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        _ensure_collection()
    return _client


def _ensure_collection():
    """Create collection if not exists."""
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
        logger.info(f"Created Qdrant collection: {COLLECTION}")


def upsert(article_id: str, vector: List[float], payload: Dict) -> bool:
    """Insert or update article vector."""
    client = get_client()

    # Use hash of article_id as point ID (Qdrant needs int)
    point_id = abs(hash(article_id)) % (2**63)

    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=point_id,
            vector=vector,
            payload={**payload, "article_id": article_id}
        )]
    )
    return True


def search(
    vector: List[float],
    limit: int = 10,
    days_back: int = 14,
    topic_id: Optional[str] = None,
    min_score: float = 0.6
) -> List[Dict]:
    """Search for similar articles."""
    client = get_client()

    # Time filter
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    filters = [
        FieldCondition(key="indexed_at", range=Range(gte=cutoff.isoformat()))
    ]

    # Optional topic filter
    if topic_id:
        filters.append(FieldCondition(key="topics", match={"value": topic_id}))

    results = client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        query_filter=Filter(must=filters) if filters else None,
        limit=limit,
        with_payload=True,
        score_threshold=min_score
    )

    return [
        {**hit.payload, "score": hit.score, "source_type": "local"}
        for hit in results
    ]


def delete_old(days_to_keep: int = 30) -> int:
    """Delete articles older than X days. Run weekly."""
    client = get_client()
    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)

    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(must=[
            FieldCondition(key="indexed_at", range=Range(lt=cutoff.isoformat()))
        ])
    )
    logger.info(f"Deleted articles older than {days_to_keep} days")
    return 0


def count() -> int:
    """Count vectors in collection."""
    client = get_client()
    info = client.get_collection(COLLECTION)
    return info.points_count
```

---

### File: `graph-functions/src/vector/embedder.py`

```python
"""OpenAI embeddings - simple wrapper."""
import os
from typing import List
from openai import OpenAI
from utils.app_logging import get_logger

logger = get_logger(__name__)

MODEL = "text-embedding-3-small"  # $0.02/1M tokens, 1536 dims
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def embed(text: str) -> List[float]:
    """Embed single text."""
    response = _get_client().embeddings.create(input=text, model=MODEL)
    return response.data[0].embedding


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts (max 2048)."""
    response = _get_client().embeddings.create(input=texts, model=MODEL)
    return [item.embedding for item in response.data]
```

---

### File: `graph-functions/src/vector/indexer.py`

```python
"""Index Tier 3 articles into Qdrant."""
from datetime import datetime
from typing import Optional
from .embedder import embed
from .client import upsert, count
from src.graph.neo4j_client import run_cypher
from utils.app_logging import get_logger

logger = get_logger(__name__)


def index_article(article_id: str) -> bool:
    """
    Index article if it's Tier 3. Call this after Tier 3 promotion.

    Returns True if indexed, False if skipped.
    """
    # Get article with Tier 3 relationship
    query = """
    MATCH (a:Article {id: $article_id})-[r:ABOUT]->(t:Topic)
    WHERE r.tier = 3
    RETURN a.id AS id, a.title AS title, a.summary AS summary,
           a.content AS content, a.url AS url,
           a.source AS source, a.published_date AS pub_date,
           collect(DISTINCT t.id) AS topics
    LIMIT 1
    """
    result = run_cypher(query, {"article_id": article_id})

    if not result:
        return False  # Not Tier 3

    article = result[0]

    # Need content to embed
    content = article.get("content") or article.get("summary") or ""
    if not content:
        logger.debug(f"Article {article_id} has no content, skipping")
        return False

    # Create embedding text: title + summary + content snippet
    embed_text = f"{article.get('title', '')}. {article.get('summary', '')}. {content[:1000]}"

    try:
        vector = embed(embed_text)

        payload = {
            "title": article.get("title"),
            "summary": article.get("summary"),
            "content": content[:2000],  # First 2000 chars for context
            "url": article.get("url"),
            "source": article.get("source"),
            "pub_date": str(article.get("pub_date", "")),
            "topics": article.get("topics", []),
            "indexed_at": datetime.utcnow().isoformat()
        }

        upsert(article_id, vector, payload)
        logger.info(f"Indexed article {article_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to index {article_id}: {e}")
        return False


def reindex_all(batch_size: int = 50) -> dict:
    """
    Reindex ALL Tier 3 articles. Run once after Qdrant setup.
    """
    from .embedder import embed_batch
    from .client import upsert

    query = """
    MATCH (a:Article)-[r:ABOUT]->(t:Topic)
    WHERE r.tier = 3
    WITH a, collect(DISTINCT t.id) AS topics
    RETURN a.id AS id, a.title AS title, a.summary AS summary,
           a.content AS content, a.url AS url,
           a.source AS source, a.published_date AS pub_date, topics
    """
    articles = run_cypher(query, {})

    stats = {"indexed": 0, "skipped": 0, "failed": 0}

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]

        texts = []
        valid = []

        for article in batch:
            content = article.get("content") or article.get("summary") or ""
            if not content:
                stats["skipped"] += 1
                continue

            text = f"{article.get('title', '')}. {article.get('summary', '')}. {content[:1000]}"
            texts.append(text)
            valid.append(article)

        if not texts:
            continue

        try:
            vectors = embed_batch(texts)

            for article, vector in zip(valid, vectors):
                payload = {
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "content": (article.get("content") or "")[:2000],
                    "url": article.get("url"),
                    "source": article.get("source"),
                    "pub_date": str(article.get("pub_date", "")),
                    "topics": article.get("topics", []),
                    "indexed_at": datetime.utcnow().isoformat()
                }
                upsert(article["id"], vector, payload)
                stats["indexed"] += 1

        except Exception as e:
            logger.error(f"Batch failed: {e}")
            stats["failed"] += len(valid)

    logger.info(f"Reindex complete: {stats}")
    return stats


if __name__ == "__main__":
    # Test / initial reindex
    from utils.env_loader import load_env
    load_env()

    print(f"Current count: {count()}")
    print("Reindexing all Tier 3 articles...")
    result = reindex_all()
    print(f"Done: {result}")
    print(f"New count: {count()}")
```

---

### File: `graph-functions/src/vector/search.py`

```python
"""
Vector search with Perigon fallback.

1. Search local Qdrant (our Tier 3 articles)
2. If < 3 results, also search Perigon
3. Deduplicate and return
"""
from typing import List, Dict, Optional
from .embedder import embed
from .client import search as qdrant_search
from src.clients.perigon.news_api_client import NewsApiClient
from src.llm.prompts.query_to_statement import convert_query_to_statement
from utils.app_logging import get_logger

logger = get_logger(__name__)

PERIGON_FALLBACK_THRESHOLD = 3


def search_articles(
    query: str,
    limit: int = 10,
    topic_id: Optional[str] = None,
    include_perigon: bool = True
) -> List[Dict]:
    """
    Search for articles. Local first, Perigon fallback.

    Args:
        query: Natural language query
        limit: Max results
        topic_id: Optional topic filter (local only)
        include_perigon: Whether to fallback to Perigon

    Returns:
        List of articles with score and source_type
    """
    results = []

    # Convert question to statement for better search
    statement = convert_query_to_statement(query)

    # Step 1: Search local Qdrant
    try:
        query_vector = embed(statement)
        local = qdrant_search(
            vector=query_vector,
            limit=limit,
            topic_id=topic_id
        )
        results.extend(local)
        logger.info(f"Local search: {len(local)} results")

    except Exception as e:
        logger.warning(f"Local search failed: {e}")

    # Step 2: Perigon fallback if needed
    if include_perigon and len(results) < PERIGON_FALLBACK_THRESHOLD:
        try:
            perigon = NewsApiClient()
            perigon_results = perigon.vector_search(statement, max_results=limit)

            for article in perigon_results.get("articles", []):
                article["source_type"] = "perigon"

            results.extend(perigon_results.get("articles", []))
            logger.info(f"Perigon fallback: {len(perigon_results.get('articles', []))} results")

        except Exception as e:
            logger.warning(f"Perigon search failed: {e}")

    # Step 3: Deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    return unique[:limit]


if __name__ == "__main__":
    from utils.env_loader import load_env
    load_env()

    print("Testing vector search...")
    results = search_articles("Federal Reserve interest rate policy impact")

    print(f"\nFound {len(results)} articles:")
    for i, r in enumerate(results, 1):
        source = r.get("source_type", "unknown")
        title = r.get("title", "N/A")[:60]
        score = r.get("score", 0)
        print(f"  {i}. [{source}] [{score:.2f}] {title}")
```

---

## STEP 3: Auto-Sync on Tier 3 Promotion

**File: `graph-functions/src/graph/ops/link.py`**

Find where Tier 3 relationships are created and add:

```python
# After creating Tier 3 relationship:
from src.vector.indexer import index_article
index_article(article_id)
```

**Specifically, find the function that sets `r.tier = 3` and add the index call after it.**

---

## STEP 4: Update Chat to Use Combined Search

**File: `graph-functions/src/chat/news_search.py`**

Replace the current implementation:

```python
"""
News Search for Chat - Local + Perigon combined.
"""
import threading
from typing import List, Dict, Any

from src.vector.search import search_articles  # NEW: uses Qdrant + Perigon
from src.api.backend_client import ingest_article
from utils.app_logging import get_logger

logger = get_logger(__name__)


def search_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search news for chat. Returns immediately, adds to DB in background.

    Now searches:
    1. Local Qdrant (our Tier 3 articles)
    2. Perigon (external, if local has < 3 results)
    """
    # Combined search
    articles = search_articles(query, limit=max_results, include_perigon=True)

    logger.info(f"Chat search: '{query[:40]}...' -> {len(articles)} results")

    # Background add Perigon articles to DB
    perigon_articles = [a for a in articles if a.get("source_type") == "perigon"]
    if perigon_articles:
        threading.Thread(
            target=_background_add_articles,
            args=(perigon_articles,),
            daemon=True
        ).start()

    return articles


def _background_add_articles(articles: List[Dict[str, Any]]) -> None:
    """Add Perigon articles to DB in background."""
    added = 0
    for article in articles:
        url = article.get("url")
        if not url:
            continue
        try:
            article_data = {
                "url": url,
                "title": article.get("title", ""),
                "description": article.get("summary", ""),
                "pubDate": article.get("pubDate", ""),
                "source": {"domain": article.get("source", "")},
            }
            result = ingest_article(article_data)
            if result.get("status") == "created":
                added += 1
        except Exception as e:
            logger.warning(f"Failed to add {url[:50]}: {e}")

    logger.info(f"Background: added {added} Perigon articles")
```

---

## STEP 5: Initial Reindex Script

**File: `graph-functions/scripts/reindex_qdrant.py`**

```python
#!/usr/bin/env python3
"""
One-time script to reindex all Tier 3 articles into Qdrant.
Run after Qdrant is set up.

Usage:
    cd graph-functions
    python scripts/reindex_qdrant.py
"""
import sys
import os

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.env_loader import load_env
load_env()

from src.vector.indexer import reindex_all
from src.vector.client import count

print("=" * 60)
print("QDRANT REINDEX - All Tier 3 Articles")
print("=" * 60)

print(f"\nCurrent vectors in Qdrant: {count()}")
print("\nStarting reindex...")

result = reindex_all()

print(f"\nResults:")
print(f"  Indexed: {result['indexed']}")
print(f"  Skipped: {result['skipped']} (no content)")
print(f"  Failed:  {result['failed']}")

print(f"\nFinal count: {count()}")
print("=" * 60)
```

---

## STEP 6: Weekly Cleanup (Optional)

Add to cron or worker:

```python
from src.vector.client import delete_old

# Delete articles older than 30 days from Qdrant
delete_old(days_to_keep=30)
```

---

## DEPLOYMENT CHECKLIST

```bash
# 1. Add Qdrant to docker-compose
vim victor_deployment/docker-compose.yml

# 2. Add env vars
echo "QDRANT_HOST=qdrant" >> victor_deployment/.env
echo "QDRANT_PORT=6333" >> victor_deployment/.env
echo "OPENAI_API_KEY=sk-xxx" >> victor_deployment/.env

# 3. Start Qdrant
docker-compose up -d qdrant

# 4. Verify Qdrant is healthy
curl http://localhost:6333/health

# 5. Install qdrant-client in workers
pip install qdrant-client

# 6. Create vector module files (as above)

# 7. Run initial reindex
cd graph-functions
python scripts/reindex_qdrant.py

# 8. Add auto-index to Tier 3 promotion (in link.py)

# 9. Update chat search to use combined search

# 10. Test
python -m src.vector.search
```

---

## HOW IT STAYS IN SYNC

| Event | Action |
|-------|--------|
| Article becomes Tier 3 | `index_article(article_id)` called automatically |
| Chat searches | Local Qdrant first, Perigon fallback |
| Perigon article found | Added to DB in background (may become Tier 3 later) |
| Weekly cleanup | `delete_old(30)` removes stale vectors |

**No batch jobs needed. No manual sync. It just works.**

---

## COST ESTIMATE

| Item | Cost |
|------|------|
| OpenAI embeddings | ~$0.02 per 1M tokens (~50K articles) |
| Qdrant | Free (self-hosted) |
| Storage | ~1GB per 100K articles |

**Negligible cost.**

---

## FILES TO CREATE

1. `victor_deployment/docker-compose.yml` - Add qdrant service
2. `graph-functions/src/vector/__init__.py`
3. `graph-functions/src/vector/client.py`
4. `graph-functions/src/vector/embedder.py`
5. `graph-functions/src/vector/indexer.py`
6. `graph-functions/src/vector/search.py`
7. `graph-functions/scripts/reindex_qdrant.py`
8. Update `graph-functions/src/graph/ops/link.py` - Add index call
9. Update `graph-functions/src/chat/news_search.py` - Use combined search

---

## SUMMARY

- **5 new files** in `src/vector/`
- **1 script** for initial reindex
- **2 file updates** (link.py, news_search.py)
- **Docker compose** addition
- **Auto-sync** on Tier 3 promotion
- **Combined search** in chat (local + Perigon)
- **Zero maintenance** after setup
