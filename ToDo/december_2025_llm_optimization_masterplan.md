# LLM Cost Optimization Master Plan - December 2025

> **Status**: PHASES 1, 2, 3, 4, 5 COMPLETE - All Done!
> **Priority**: CRITICAL - Direct cost savings + quality improvement
> **Owner**: Victor + AI Agent
> **Estimated Effort**: 8-10 hours total
> **Expected Savings**: 85-95% reduction in LLM API costs

---

## Executive Summary

This plan addresses **catastrophic over-writing** of analyses. Current system rewrites ALL topics continuously, burning LLM resources on unchanged content. The fix is surgical: **only rewrite when new information exists**, and **use cheaper models for writing tasks**.

### Key Metrics

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Topic rewrites/day | ~700-1000 | ~50-100 | **90%** |
| Strategy rewrites/day | ~138 | 2-4 | **97%** |
| DeepSeek calls/day | ~200+ | ~30 | **85%** |
| Useful rewrites | ~50-100 | Same | 100% useful |

---

## The Problem

### Current Behavior (Wasteful)
```
write_all.py (continuous loop):
  For each topic:
    → Run full 8-section analysis (40-60 LLM calls)
    → Even if NO new articles since last analysis
    → Even if we just rewrote 10 minutes ago
```

### Desired Behavior (Smart)
```
write_all.py (continuous loop):
  For each topic:
    → Check: Are there NEW Tier 3 articles since last analysis?
    → Check: Have we rewritten in the last 24 hours?
    → If NO new articles OR recently rewritten → SKIP
    → If YES new articles AND >24h since last rewrite → REWRITE
    → When rewriting: HIGHLIGHT new articles to agents
```

---

## Implementation Plan

### PHASE 1: Smart Rewrite Logic (write_all.py) - COMPLETE
**Priority**: CRITICAL - Biggest impact
**Effort**: 2-3 hours
**Files**: `graph-functions/entrypoints/write_all.py`, new `src/analysis/rewrite_policy.py`
**Status**: DONE - Created rewrite_policy.py, added last_analyzed timestamp, 24h cooldown

### PHASE 2: New Article Highlighting (orchestrator.py) - COMPLETE
**Priority**: HIGH - Quality improvement
**Effort**: 2 hours
**Files**: `graph-functions/src/analysis_agents/orchestrator.py`, material builders
**Status**: DONE - Implemented in article_material.py:
- `build_material_for_synthesis_section()` accepts `new_article_ids` parameter
- Articles marked with `[NEW]` tag in headers when they're new since last analysis
- Header shows count of NEW articles with instruction to focus on them
- Orchestrator passes `new_article_ids` through to material builder

### PHASE 3: Section Complexity Routing (section_config.py) - COMPLETE
**Priority**: MEDIUM - Cost savings
**Effort**: 1-2 hours
**Files**: `graph-functions/src/analysis_agents/section_config.py`, writer/agent.py, agents
**Status**: DONE - Implemented section-based routing:
- Writer: MEDIUM for 5 sections (chain_reaction_map, structural_threats, tactical_scenarios, immediate_intelligence, macro_cascade)
- Writer: COMPLEX for 3 sections (trade_intelligence, house_view, risk_monitor)
- SynthesisScout: MEDIUM (was COMPLEX)
- DepthFinder: MEDIUM (was COMPLEX)
- ContrarianFinder: COMPLEX (kept)
- Critic: COMPLEX (kept)

### PHASE 4: Strategy Analysis Fix (write_all.py) - COMPLETE
**Priority**: HIGH - Prevent duplicate work
**Effort**: 1-2 hours
**Files**: `graph-functions/entrypoints/write_all.py`
**Status**: DONE - Implemented smart strategy rewrite:
- Added `strategy_needs_update()` function that checks if linked topics have newer `last_analyzed`
- Strategy only rewrites if ANY linked topic was analyzed AFTER strategy's `last_analyzed_at`
- Prevents duplicate rewrites even after process restart (uses persisted timestamps)
- Added tracking: `strategy_analysis_triggered`, `strategy_analysis_skipped`
- Logs show skip reason: `no_topic_updates`, `never_analyzed`, `no_linked_topics`

### PHASE 5: Dashboard Stats Update (admin) - COMPLETE
**Priority**: LOW - Visibility
**Effort**: 1-2 hours
**Files**: `saga-fe/src/routes/admin/`, `saga-be/src/api/routes/admin.py`
**Status**: DONE - Added skipped_no_new, skipped_cooldown stats to dashboard

### PHASE 6: Per-Section Rewrite Check - CANCELLED
**Priority**: Was HIGH
**Status**: CANCELLED - Decided against due to cumulative chain architecture.
Sections build on each other, so partial rewrites would cause inconsistency.
Current approach (rewrite all 8 or none) is simpler and safer.

---

## PHASE 1: Smart Rewrite Logic

### 1.1 Create New File: `src/analysis/rewrite_policy.py`

This module determines whether a topic should be rewritten.

```python
# graph-functions/src/analysis/rewrite_policy.py
"""
Rewrite Policy - Determines when topic analysis should be rewritten.

Core Rules:
1. Only rewrite if there are NEW Tier 3 articles since last analysis
2. Never rewrite more than once per MIN_REWRITE_INTERVAL_HOURS
3. When rewriting, provide list of NEW article IDs to highlight

This prevents wasteful rewrites when no new information exists.
"""

from datetime import datetime, timedelta
from typing import Tuple, List, Optional
from src.graph.neo4j_client import run_cypher
from src.observability.stats_client import track
from utils import app_logging

logger = app_logging.get_logger(__name__)

# Configuration
MIN_REWRITE_INTERVAL_HOURS = 24  # Never rewrite faster than this (can reduce later: 12h, 4h, etc.)


def should_rewrite_topic(topic_id: str) -> Tuple[bool, str, List[str]]:
    """
    Determine if topic analysis should be rewritten.

    Logic:
    1. Get topic's last_analyzed timestamp from Neo4j
    2. Get NEW Tier 3 articles linked since last_analyzed
    3. If no new articles → SKIP
    4. If new articles exist BUT we rewrote < MIN_REWRITE_INTERVAL_HOURS ago → SKIP (cooldown)
    5. If new articles exist AND cooldown passed → REWRITE with highlighted article IDs

    Args:
        topic_id: The topic to check

    Returns:
        Tuple of:
        - should_rewrite: bool - True if we should run analysis
        - reason: str - Why we're rewriting or skipping (for logging/stats)
        - new_article_ids: List[str] - Article IDs that are NEW since last analysis
    """
    # Get topic's last_analyzed timestamp and new articles in one query
    query = """
    MATCH (t:Topic {id: $topic_id})
    OPTIONAL MATCH (t)<-[r:ABOUT]-(a:Article)
    WHERE r.tier = 3
      AND (t.last_analyzed IS NULL OR r.created_at > t.last_analyzed)
    RETURN
        t.last_analyzed AS last_analyzed,
        collect(DISTINCT a.id) AS new_article_ids
    """
    result = run_cypher(query, {"topic_id": topic_id})

    if not result:
        logger.warning(f"Topic {topic_id} not found in graph")
        return False, "topic_not_found", []

    row = result[0]
    last_analyzed = row.get("last_analyzed")
    new_article_ids = [aid for aid in row.get("new_article_ids", []) if aid]  # Filter None values

    # RULE 1: No new articles → SKIP
    if not new_article_ids:
        track("analysis.skipped.no_new_articles")
        logger.info(f"⏭️ SKIP {topic_id}: No new Tier 3 articles since last analysis")
        return False, "no_new_articles", []

    # RULE 2: Check cooldown (have we rewritten recently?)
    if last_analyzed:
        try:
            # Handle both string and datetime types from Neo4j
            if isinstance(last_analyzed, str):
                last_analyzed_dt = datetime.fromisoformat(last_analyzed.replace('Z', '+00:00'))
                last_analyzed_dt = last_analyzed_dt.replace(tzinfo=None)
            else:
                # Neo4j datetime object
                last_analyzed_dt = datetime(
                    last_analyzed.year, last_analyzed.month, last_analyzed.day,
                    last_analyzed.hour, last_analyzed.minute, last_analyzed.second
                )

            hours_since = (datetime.utcnow() - last_analyzed_dt).total_seconds() / 3600

            if hours_since < MIN_REWRITE_INTERVAL_HOURS:
                track("analysis.skipped.cooldown")
                logger.info(
                    f"⏭️ SKIP {topic_id}: Cooldown active "
                    f"({hours_since:.1f}h < {MIN_REWRITE_INTERVAL_HOURS}h) - "
                    f"{len(new_article_ids)} new articles waiting"
                )
                return False, "cooldown", new_article_ids
        except Exception as e:
            logger.warning(f"Could not parse last_analyzed for {topic_id}: {e}")
            # Continue to rewrite if we can't parse the timestamp

    # RULE 3: New articles exist AND cooldown passed → REWRITE
    track("analysis.triggered.new_articles")
    logger.info(
        f"✅ REWRITE {topic_id}: {len(new_article_ids)} new articles found, cooldown passed"
    )
    return True, "new_articles", new_article_ids


def get_articles_for_analysis(topic_id: str, new_article_ids: List[str]) -> dict:
    """
    Get all Tier 3 articles for topic, split into NEW vs EXISTING.

    This enables agents to focus on what's changed since last analysis.

    Args:
        topic_id: Topic ID
        new_article_ids: List of article IDs that are NEW since last analysis

    Returns:
        dict with:
        - new_articles: List of article dicts (these are NEW - agents focus here)
        - existing_articles: List of article dicts (already in previous analysis)
        - new_count: Number of new articles
        - total_count: Total articles
    """
    new_ids_set = set(new_article_ids)

    # Get all Tier 3 articles for this topic
    query = """
    MATCH (t:Topic {id: $topic_id})<-[r:ABOUT]-(a:Article)
    WHERE r.tier = 3
    RETURN a.id AS id, a.title AS title, a.summary AS summary,
           a.url AS url, a.published_date AS published_date,
           r.created_at AS linked_at
    ORDER BY r.created_at DESC
    """
    articles = run_cypher(query, {"topic_id": topic_id})

    new_articles = []
    existing_articles = []

    for article in articles:
        if article["id"] in new_ids_set:
            new_articles.append(article)
        else:
            existing_articles.append(article)

    return {
        "new_articles": new_articles,
        "existing_articles": existing_articles,
        "new_count": len(new_articles),
        "total_count": len(articles),
    }


def update_last_analyzed(topic_id: str) -> None:
    """
    Update topic's last_analyzed timestamp after successful rewrite.

    Called after analysis_rewriter_with_agents completes successfully.
    """
    query = """
    MATCH (t:Topic {id: $topic_id})
    SET t.last_analyzed = datetime()
    RETURN t.id
    """
    run_cypher(query, {"topic_id": topic_id})
    logger.info(f"📝 Updated last_analyzed for {topic_id}")
```

---

### 1.2 Modify `write_all.py` - Add Smart Rewrite Check

**File**: `graph-functions/entrypoints/write_all.py`

#### CHANGE 1: Add import at top of file

```python
# ADD after other imports (around line 40)
from src.analysis.rewrite_policy import should_rewrite_topic, update_last_analyzed
```

#### CHANGE 2: Modify `write_single_topic()` function

**CURRENT CODE** (lines 49-58):
```python
def write_single_topic(topic_id: str) -> bool:
    """Run full analysis for a single topic. Returns True if successful."""
    try:
        logger.info(f"🎯 Writing analysis for: {topic_id}")
        analysis_rewriter_with_agents(topic_id)
        logger.info(f"✅ Completed: {topic_id}")
        return True
    except Exception as e:
        logger.error(f"Failed {topic_id}: {e}")
        return False
```

**NEW CODE** (replace entire function):
```python
def write_single_topic(topic_id: str, new_article_ids: Optional[List[str]] = None) -> bool:
    """
    Run full analysis for a single topic. Returns True if successful.

    Args:
        topic_id: Topic to analyze
        new_article_ids: Optional list of NEW article IDs to highlight to agents.
                        If provided, agents will focus on these new articles.
    """
    try:
        logger.info(f"🎯 Writing analysis for: {topic_id}")
        if new_article_ids:
            logger.info(f"   📰 Highlighting {len(new_article_ids)} NEW articles to agents")

        # Pass new_article_ids to orchestrator so agents know what's new
        analysis_rewriter_with_agents(topic_id, new_article_ids=new_article_ids)

        # Update last_analyzed timestamp
        update_last_analyzed(topic_id)

        logger.info(f"✅ Completed: {topic_id}")
        return True
    except Exception as e:
        logger.error(f"Failed {topic_id}: {e}")
        return False
```

#### CHANGE 3: Modify `write_all_topics()` function

**CURRENT CODE** (lines 61-93):
```python
def write_all_topics(shuffle: bool = True) -> dict:
    """
    Run full analysis for all topics.

    Returns:
        dict with success/failure counts
    """
    all_topics = get_all_topics(fields=["id", "name"])
    topic_ids = [t["id"] for t in all_topics]

    logger.info(f"{'='*60}")
    logger.info(f"📊 WRITE ALL TOPICS - Found {len(topic_ids)} topics")
    logger.info(f"{'='*60}")

    if shuffle:
        random.shuffle(topic_ids)
        logger.info("🎲 Shuffled order for balanced coverage")

    stats = {"success": 0, "failed": 0, "total": len(topic_ids)}

    for i, topic_id in enumerate(topic_ids, 1):
        logger.info(f"[{i}/{len(topic_ids)}] Processing {topic_id}")

        if write_single_topic(topic_id):
            stats["success"] += 1
        else:
            stats["failed"] += 1

    logger.info(f"{'='*60}")
    logger.info(f"🎉 TOPICS COMPLETE: {stats['success']}/{stats['total']} succeeded, {stats['failed']} failed")
    logger.info(f"{'='*60}")

    return stats
```

**NEW CODE** (replace entire function):
```python
def write_all_topics(shuffle: bool = True) -> dict:
    """
    Run full analysis for all topics that need updates.

    Smart rewrite logic:
    - Only rewrites topics with NEW Tier 3 articles since last analysis
    - Respects cooldown period (MIN_REWRITE_INTERVAL_HOURS)
    - Highlights new articles to agents for focused analysis

    Returns:
        dict with success/failure/skipped counts
    """
    all_topics = get_all_topics(fields=["id", "name"])
    topic_ids = [t["id"] for t in all_topics]

    logger.info(f"{'='*60}")
    logger.info(f"📊 WRITE ALL TOPICS - Checking {len(topic_ids)} topics")
    logger.info(f"{'='*60}")

    if shuffle:
        random.shuffle(topic_ids)
        logger.info("🎲 Shuffled order for balanced coverage")

    stats = {
        "success": 0,
        "failed": 0,
        "skipped_no_new": 0,
        "skipped_cooldown": 0,
        "total": len(topic_ids)
    }

    for i, topic_id in enumerate(topic_ids, 1):
        logger.info(f"[{i}/{len(topic_ids)}] Checking {topic_id}")

        # Smart rewrite check
        should_rewrite, reason, new_article_ids = should_rewrite_topic(topic_id)

        if not should_rewrite:
            if reason == "no_new_articles":
                stats["skipped_no_new"] += 1
            elif reason == "cooldown":
                stats["skipped_cooldown"] += 1
            continue

        # Rewrite with highlighted new articles
        if write_single_topic(topic_id, new_article_ids=new_article_ids):
            stats["success"] += 1
        else:
            stats["failed"] += 1

    logger.info(f"{'='*60}")
    logger.info(f"🎉 TOPICS COMPLETE:")
    logger.info(f"   ✅ Rewritten: {stats['success']}")
    logger.info(f"   ❌ Failed: {stats['failed']}")
    logger.info(f"   ⏭️ Skipped (no new articles): {stats['skipped_no_new']}")
    logger.info(f"   ⏸️ Skipped (cooldown): {stats['skipped_cooldown']}")
    logger.info(f"{'='*60}")

    return stats
```

---

## PHASE 2: New Article Highlighting in Agents

### 2.1 Modify `orchestrator.py` - Accept and Pass New Article IDs

**File**: `graph-functions/src/analysis_agents/orchestrator.py`

#### CHANGE 1: Modify function signature (around line 497)

**CURRENT CODE**:
```python
def analysis_rewriter_with_agents(
    topic_id: str,
    analysis_type: Optional[str] = None
) -> None:
```

**NEW CODE**:
```python
def analysis_rewriter_with_agents(
    topic_id: str,
    analysis_type: Optional[str] = None,
    new_article_ids: Optional[List[str]] = None
) -> None:
```

#### CHANGE 2: Add new article context to material building (around line 591-594)

**CURRENT CODE**:
```python
            else:
                print(f"📦 Building material from articles...")
                material, article_ids = build_material_for_synthesis_section(topic_id, section)
                if prior_context:
                    material = f"{material}\n\n{'='*80}\nPRIOR ANALYSIS:\n{'='*80}\n\n{prior_context}"
```

**NEW CODE**:
```python
            else:
                print(f"📦 Building material from articles...")
                material, article_ids = build_material_for_synthesis_section(topic_id, section)

                # Highlight NEW articles if provided
                if new_article_ids and article_ids:
                    new_ids_in_material = [aid for aid in article_ids if aid in new_article_ids]
                    if new_ids_in_material:
                        new_article_header = (
                            "\n" + "="*80 + "\n"
                            "🆕 NEW ARTICLES SINCE LAST ANALYSIS\n"
                            "="*80 + "\n"
                            f"The following {len(new_ids_in_material)} article(s) are NEW since the last analysis.\n"
                            "PRIORITIZE integrating these into your analysis. Focus on:\n"
                            "- How does this new information change the narrative?\n"
                            "- What's the delta from the previous analysis?\n"
                            "- What new risks or opportunities does this reveal?\n\n"
                            f"NEW ARTICLE IDs: {', '.join(new_ids_in_material)}\n"
                            "="*80 + "\n"
                        )
                        material = new_article_header + material
                        logger.info(f"   🆕 Highlighted {len(new_ids_in_material)} NEW articles to agents")

                if prior_context:
                    material = f"{material}\n\n{'='*80}\nPRIOR ANALYSIS:\n{'='*80}\n\n{prior_context}"
```

---

## PHASE 3: Section Complexity Routing

### 3.1 Modify `section_config.py` - Add Complexity Mapping

**File**: `graph-functions/src/analysis_agents/section_config.py`

**ADD at the end of the file** (after line 79):

```python
# =============================================================================
# SECTION COMPLEXITY ROUTING
# =============================================================================
#
# Maps each section to the appropriate model tier.
#
# MEDIUM (120B): Writing/summarization tasks - your free GPU model
# COMPLEX (DeepSeek): Deep reasoning tasks - paid API, use sparingly
#
# Rationale:
# - chain_reaction_map: Mapping cause-effect from articles → MEDIUM (summarization)
# - structural_threats: Deep causal reasoning, multi-step analysis → COMPLEX
# - tactical_scenarios: Scenario building from prior context → MEDIUM
# - immediate_intelligence: Information extraction → MEDIUM
# - macro_cascade: Complex cross-asset synthesis → COMPLEX
# - trade_intelligence: Formatting trade ideas → MEDIUM
# - house_view: Final conviction judgment → COMPLEX (critical decision)
# - risk_monitor: Checklist generation → MEDIUM

from src.llm.llm_router import ModelTier

SECTION_COMPLEXITY = {
    # MEDIUM (120B) - Writing/summarization tasks (FREE - your GPU)
    "chain_reaction_map": ModelTier.MEDIUM,
    "tactical_scenarios": ModelTier.MEDIUM,
    "immediate_intelligence": ModelTier.MEDIUM,
    "trade_intelligence": ModelTier.MEDIUM,
    "risk_monitor": ModelTier.MEDIUM,

    # COMPLEX (DeepSeek) - Deep reasoning tasks (PAID - use sparingly)
    "structural_threats": ModelTier.COMPLEX,
    "macro_cascade": ModelTier.COMPLEX,
    "house_view": ModelTier.COMPLEX,
}


def get_section_complexity(section_id: str) -> ModelTier:
    """
    Get the appropriate model tier for a section.

    Returns COMPLEX by default for unknown sections (safe fallback).
    """
    return SECTION_COMPLEXITY.get(section_id, ModelTier.COMPLEX)
```

### 3.2 Modify Agent Initialization in Orchestrator

**File**: `graph-functions/src/analysis_agents/orchestrator.py`

This requires finding where agents get their LLM instances and updating them to use `get_section_complexity()`.

**Look for** WriterAgent initialization and update to pass section-specific tier:

```python
# Where WriterAgent is used, pass the section's complexity
from src.analysis_agents.section_config import get_section_complexity

# In the section loop:
section_tier = get_section_complexity(section)
writer = WriterAgent(model_tier=section_tier)  # If WriterAgent accepts this
# OR
llm = get_llm(section_tier)  # If you need to pass LLM directly
```

**Note**: The exact implementation depends on how WriterAgent currently gets its LLM. May need to trace through `WriterAgent.__init__()` to see how to inject the tier.

---

## PHASE 4: Strategy Analysis Fix

### 4.1 Strategy Analysis - Once Per Day Only

**File**: `graph-functions/entrypoints/write_all.py`

#### CHANGE: Add strategy "needs update" check

**ADD new function** (after `should_run_daily_strategies()`):

```python
def strategy_needs_update(username: str, strategy_id: str) -> Tuple[bool, str]:
    """
    Check if strategy needs reanalysis.

    A strategy needs update if ANY of its linked topics have been
    analyzed more recently than the strategy's last analysis.

    This ensures strategy analysis reflects the latest topic insights.

    Returns:
        Tuple of (needs_update: bool, reason: str)
    """
    from src.api.backend_client import get_strategy, get_strategy_topics
    from src.graph.ops.topic import get_topic_by_id

    strategy = get_strategy(username, strategy_id)
    if not strategy:
        return False, "strategy_not_found"

    strategy_last_analyzed = strategy.get("last_analyzed_at")
    if not strategy_last_analyzed:
        return True, "never_analyzed"

    # Get linked topics
    topics_data = get_strategy_topics(username, strategy_id)
    if not topics_data:
        return False, "no_linked_topics"

    topic_ids = topics_data.get("topics", [])
    if not topic_ids:
        return False, "no_linked_topics"

    # Check if any linked topic has newer analysis
    for topic_id in topic_ids:
        topic = get_topic_by_id(topic_id)
        if not topic:
            continue

        topic_last_analyzed = topic.get("last_analyzed")
        if topic_last_analyzed and topic_last_analyzed > strategy_last_analyzed:
            return True, f"topic_{topic_id}_updated"

    return False, "no_topic_updates"
```

#### CHANGE: Modify `write_all_strategies()` to use the check

**CURRENT CODE** (lines 96-134):
```python
def write_all_strategies() -> dict:
    """
    Run strategy analysis for all users.

    Returns:
        dict with success/failure counts
    """
    all_users = get_all_users()

    if not all_users:
        logger.warning("No users found, skipping strategy analysis")
        return {"success": 0, "failed": 0, "total": 0}

    # ... rest of function
```

**NEW CODE** (replace the inner loop):
```python
def write_all_strategies() -> dict:
    """
    Run strategy analysis for all users.

    Only analyzes strategies that have linked topics with newer analysis.
    This prevents rewriting strategies when no underlying data changed.

    Returns:
        dict with success/failure/skipped counts
    """
    all_users = get_all_users()

    if not all_users:
        logger.warning("No users found, skipping strategy analysis")
        return {"success": 0, "failed": 0, "skipped": 0, "total": 0}

    logger.info(f"{'='*60}")
    logger.info(f"📈 WRITE ALL STRATEGIES - Checking {len(all_users)} users")
    logger.info(f"{'='*60}")

    stats = {"success": 0, "failed": 0, "skipped": 0, "total": 0}

    for username in all_users:
        user_strategies = get_user_strategies(username)
        stats["total"] += len(user_strategies)
        logger.info(f"User {username}: {len(user_strategies)} strategies")

        for strategy in user_strategies:
            strategy_id = strategy['id']

            # Check if strategy needs update
            needs_update, reason = strategy_needs_update(username, strategy_id)

            if not needs_update:
                logger.info(f"  ⏭️ Skipping {username}/{strategy_id}: {reason}")
                stats["skipped"] += 1
                track("strategy_analysis_skipped", f"{username}/{strategy_id}:{reason}")
                continue

            try:
                logger.info(f"  🔄 Analyzing {username}/{strategy_id}: {reason}")
                analyze_user_strategy(username, strategy_id)
                stats["success"] += 1
                track("strategy_analysis_completed", f"{username}/{strategy_id}")
            except Exception as e:
                logger.error(f"  ❌ Failed {username}/{strategy_id}: {e}")
                stats["failed"] += 1

    logger.info(f"{'='*60}")
    logger.info(f"🎉 STRATEGIES COMPLETE:")
    logger.info(f"   ✅ Analyzed: {stats['success']}")
    logger.info(f"   ❌ Failed: {stats['failed']}")
    logger.info(f"   ⏭️ Skipped (no updates): {stats['skipped']}")
    logger.info(f"{'='*60}")

    return stats
```

---

## PHASE 5: Dashboard Stats Update

### 5.1 Add New Tracking Categories

**File**: `graph-functions/src/observability/stats_client.py`

**ADD** new stat categories to track:

```python
# New stat categories for smart rewriting
"analysis.triggered.new_articles"    # Topic rewritten because new articles
"analysis.skipped.no_new_articles"   # Topic skipped - no new Tier 3 articles
"analysis.skipped.cooldown"          # Topic skipped - rewritten too recently
"strategy_analysis_skipped"          # Strategy skipped - no topic updates
```

### 5.2 Update Admin Dashboard Display

**File**: `saga-fe/src/routes/admin/+page.svelte` (or wherever stats are displayed)

Update the Agent Analysis section to show new categories:

```
🤖 Agent Analysis
Triggered (new articles)  42   ← Topics with new articles
Skipped (cooldown)        89   ← Too recently rewritten
Skipped (no new info)    156   ← No new Tier 3 articles
Completed                 42   ← Analyses finished
Failed                     0   ← Errors
Sections Written         336   ← 42 topics × 8 sections

📊 Strategy Analysis
Triggered                  4   ← Strategies with topic updates
Skipped (no updates)       8   ← No linked topic changes
Completed                  4   ← Analyses finished
Last Run              6:15 AM  ← Daily run time
```

---

## Testing Checklist

### Phase 1 Tests
- [ ] Create new topic with no articles → should NOT trigger rewrite
- [ ] Add Tier 3 article to topic → should trigger rewrite
- [ ] Immediately try to rewrite again → should skip (cooldown)
- [ ] Wait 24+ hours → should allow rewrite
- [ ] Check logs show correct skip reasons

### Phase 2 Tests
- [ ] Rewrite with new articles → logs show "Highlighting X NEW articles"
- [ ] Check agent output mentions new articles
- [ ] Verify material includes new article header

### Phase 3 Tests
- [ ] Verify chain_reaction_map uses MEDIUM tier (check logs)
- [ ] Verify structural_threats uses COMPLEX tier
- [ ] Check LLM router logs show correct tier selection

### Phase 4 Tests
- [ ] Strategy with no topic updates → should skip
- [ ] Update linked topic → strategy should trigger
- [ ] Verify strategies only run at 6am window

---

## Rollback Plan

If issues arise, rollback is simple:

### Phase 1 Rollback
```python
# In write_all_topics(), replace smart logic with:
if write_single_topic(topic_id):  # No check, just write all
```

### Phase 3 Rollback
```python
# In section_config.py, make all sections COMPLEX:
SECTION_COMPLEXITY = {section: ModelTier.COMPLEX for section in AGENT_SECTIONS}
```

---

## Configuration Tuning

After deployment, you can tune these values based on observed behavior:

### `MIN_REWRITE_INTERVAL_HOURS` in `rewrite_policy.py`

| Value | Behavior | Use Case |
|-------|----------|----------|
| 24 | Once per day max | Initial deployment (recommended) |
| 12 | Twice per day max | After verifying stability |
| 4 | Six times per day max | High-activity markets |
| 1 | Hourly max | Breaking news scenarios |

### Complexity Routing

If 120B model quality is insufficient for certain sections, simply change the mapping:

```python
# Move a section to COMPLEX if quality is poor:
SECTION_COMPLEXITY["chain_reaction_map"] = ModelTier.COMPLEX
```

---

## Success Metrics

Track these metrics after deployment:

1. **DeepSeek API calls/day**: Should drop from ~200 to ~30
2. **Topic rewrites/day**: Should drop from ~700 to ~50-100
3. **Strategy rewrites/day**: Should drop from ~138 to ~2-4
4. **Analysis quality**: Should improve (agents focus on what's new)
5. **Dashboard skip counts**: Should show healthy skip ratios

---

## Future Enhancements

Once this is stable, consider:

1. **Priority Queue**: Topics with MORE new articles get processed first
2. **Incremental Sections**: Only rewrite sections that use changed articles
3. **Adaptive Cooldown**: Reduce cooldown for high-activity topics
4. **Burst Mode**: Lower cooldown during market hours, increase overnight

---

## Summary

This plan delivers:

1. **90% reduction** in unnecessary topic rewrites
2. **97% reduction** in unnecessary strategy rewrites
3. **85% reduction** in DeepSeek API usage
4. **Better quality** - agents focus on what's new
5. **Full visibility** - dashboard shows exactly what's happening

Total effort: ~8-10 hours
Expected savings: $1,400-2,900/month in API costs
