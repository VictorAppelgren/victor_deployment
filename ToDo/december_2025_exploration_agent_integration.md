# Exploration Agent Integration - December 2025 TODO

> **Status**: Planning Phase
> **Priority**: HIGH - Critical for delivering non-obvious insights to users
> **Owner**: Victor + AI Agent
> **Deadline**: End of December 2025

---

## 🎯 Mission

Integrate the Exploration Agent into the core workflow to automatically discover multi-hop, non-obvious risks and opportunities that traditional analysis misses. This is the core differentiator of Saga - finding hidden connections across the knowledge graph.

---

## 📋 Overview

### What Gets Exploration?
1. **Topics** (existing workflow enhancement):
   - Run BEFORE rewriting each topic section
   - 1 run for risks → populate `risk_1`, `risk_2`, `risk_3`
   - 1 run for opportunities → populate `opportunity_1`, `opportunity_2`, `opportunity_3`
   - Store in Neo4j topic node properties

2. **User Strategies** (NEW capability - PRIORITY):
   - Run until we have 3 risks + 3 opportunities per strategy
   - Store in backend JSON (strategy object)
   - More important than topics - direct user value

### Integration Points
- **Topic Writing**: `graph-functions/entrypoints/write_all.py` (Server 3)
- **Strategy Writing**: NEW workflow to be created
- **Research Input**: Findings feed into analysis agent orchestrator

---

## 🚀 Phase 1: Core Integration (Week 1)

### 1.1 Neo4j Schema Updates
**File**: `graph-functions/src/graph/models.py`

**Add to Topic Node:**
```python
# Risk findings from exploration
risk_1: Optional[dict] = None  # {headline, rationale, flow_path, evidence[]}
risk_2: Optional[dict] = None
risk_3: Optional[dict] = None

# Opportunity findings from exploration
opportunity_1: Optional[dict] = None
opportunity_2: Optional[dict] = None
opportunity_3: Optional[dict] = None
catalyst_1: Optional[dict] = None
catalyst_2: Optional[dict] = None
catalyst_3: Optional[dict] = None
```

**Evidence Format:**
```json
{
  "headline": "China Stimulus → Copper → Fed Inflation → EURUSD Downside",
  "rationale": "2-3 sentence explanation of the chain",
  "flow_path": "china_stimulus → copper_demand → inflation_pressure → fed_hawkish → eurusd",
  "evidence": [
    {
      "excerpt": "Actual text from article or section",
      "source_id": "art_ABC123 or sec_eurusd_executive_summary",
      "source_type": "article or section",
      "why_relevant": "How this supports the chain",
      "saved_at_topic": "copper_demand",
      "saved_at_step": 5
    }
  ],
  "exploration_steps": 12,
  "confidence": 0.85,
  "created_at": "2025-12-25T10:30:00Z"
}
```

**Tasks:**
- [ ] Update `Topic` model in `models.py`
- [ ] Create migration script to add fields to existing topics
- [ ] Create graph operations in `src/graph/ops/topic.py`:
  - [ ] `save_topic_exploration_finding(topic_id, finding_type, slot_number, finding_data)`
  - [ ] `get_topic_exploration_findings(topic_id, finding_type=None)`
  - [ ] `replace_topic_exploration_finding(topic_id, finding_type, slot_number, finding_data)`
- [ ] Write tests for graph operations

---

### 1.2 Backend API Extensions (Strategy Findings)
**File**: `saga-be/src/routes/strategies.py`

**New Endpoints:**
```python
# Get exploration findings for a strategy
GET /api/strategies/{strategy_id}/explorations?username=X
Response: {
  "risks": [finding1, finding2, finding3],
  "opportunities": [finding1, finding2, finding3]
}

# Save exploration finding to strategy
POST /api/strategies/{strategy_id}/explorations
Body: {
  "username": "victor",
  "finding_type": "risk",  # or "opportunity"
  "finding": {<exploration_result>}
}
Response: {
  "slot_assigned": 1,  # which risk_1/opportunity_1 it went to
  "replaced": null  # or slot number if it replaced existing
}

# Delete exploration finding
DELETE /api/strategies/{strategy_id}/explorations/{finding_type}/{slot_number}?username=X
```

**Storage Manager Updates:**
**File**: `saga-be/src/storage/strategy_manager.py`

```python
def save_exploration_finding(username: str, strategy_id: str, finding_type: str, finding: dict) -> dict:
    """Save exploration finding to next available slot or replace lowest quality"""

def get_exploration_findings(username: str, strategy_id: str, finding_type: str = None) -> dict:
    """Get all exploration findings for a strategy"""

def delete_exploration_finding(username: str, strategy_id: str, finding_type: str, slot: int):
    """Delete a specific exploration finding"""
```

**Strategy JSON Schema Update:**
```json
{
  "id": "strategy_123",
  "name": "EURUSD Long-term Short",
  "user_input": {...},
  "topic_mapping": {...},
  "explorations": {
    "risks": {
      "risk_1": {<finding>},
      "risk_2": {<finding>},
      "risk_3": {<finding>}
    },
    "opportunities": {
      "opportunity_1": {<finding>},
      "opportunity_2": {<finding>},
      "opportunity_3": {<finding>}
    },
    "last_explored": "2025-12-25T10:30:00Z"
  }
}
```

**Tasks:**
- [ ] Add new API endpoints
- [ ] Update `strategy_manager.py` with finding management
- [ ] Update strategy JSON schema
- [ ] Write API tests
- [ ] Update frontend to display exploration findings (if needed)

---

### 1.3 Exploration Runner for Topics
**File**: `graph-functions/src/exploration_agent/topic_explorer_runner.py` (NEW)

```python
"""
Topic Exploration Runner - Finds 3 risks and 3 opportunities for a topic
"""

def explore_topic_fully(topic_id: str, max_steps_per_run: int = 15) -> dict:
    """
    Run exploration for a topic until we have 3 risks and 3 opportunities.

    Returns:
        {
            "risks": [finding1, finding2, finding3],
            "opportunities": [finding1, finding2, finding3],
            "total_runs": 6,
            "total_steps": 85,
            "success": True
        }
    """

def save_topic_findings(topic_id: str, findings: dict):
    """Save all findings to Neo4j topic node"""
```

**Strategy:**
1. Load existing findings from topic
2. Determine what's missing (need 3 risks, 3 opportunities)
3. Run exploration for each missing slot
4. Critic validates each finding
5. Only save if critic accepts
6. Retry if rejected (max 2 retries per slot)

**Tasks:**
- [ ] Create `topic_explorer_runner.py`
- [ ] Implement `explore_topic_fully()`
- [ ] Implement `save_topic_findings()`
- [ ] Add retry logic with quality threshold
- [ ] Add logging and error handling
- [ ] Write tests

---

### 1.4 Exploration Runner for Strategies
**File**: `graph-functions/src/exploration_agent/strategy_explorer_runner.py` (NEW)

```python
"""
Strategy Exploration Runner - Finds 3 risks and 3 opportunities for a user strategy
"""

def explore_strategy_fully(username: str, strategy_id: str, max_steps_per_run: int = 15) -> dict:
    """
    Run exploration for a strategy until we have 3 risks and 3 opportunities.

    Returns:
        {
            "risks": [finding1, finding2, finding3],
            "opportunities": [finding1, finding2, finding3],
            "total_runs": 6,
            "total_steps": 92,
            "success": True
        }
    """

def save_strategy_findings(username: str, strategy_id: str, findings: dict):
    """Save findings via backend API"""
```

**Strategy:**
1. Load strategy from backend
2. Ensure topic mapping exists (run TopicMapper if needed)
3. Load existing exploration findings
4. Determine what's missing
5. Run exploration for each missing slot
6. Critic validates
7. Save via backend API

**Tasks:**
- [ ] Create `strategy_explorer_runner.py`
- [ ] Implement `explore_strategy_fully()`
- [ ] Implement `save_strategy_findings()`
- [ ] Add quality ranking (replace worst if all 3 slots full and new finding is better)
- [ ] Add retry logic
- [ ] Write tests

---

## 🔄 Phase 2: Workflow Integration (Week 2)

### 2.1 Integrate into Topic Writing
**File**: `graph-functions/entrypoints/write_all.py`

**Current Flow:**
```
For each topic:
  1. Load topic from Neo4j
  2. Run analysis agents
  3. Write sections to Neo4j
```

**NEW Flow:**
```
For each topic:
  1. Load topic from Neo4j
  2. **RUN EXPLORATION** (if findings missing or outdated)
  3. Run analysis agents (now receive exploration findings as input)
  4. Write sections to Neo4j
```

**Implementation:**
```python
from src.exploration_agent.topic_explorer_runner import explore_topic_fully, save_topic_findings

def write_topic_analysis(topic_id: str):
    # Check if exploration needed
    findings = get_topic_exploration_findings(topic_id)

    needs_exploration = (
        len(findings.get("risks", [])) < 3 or
        len(findings.get("opportunities", [])) < 3 or
        is_outdated(findings.get("last_explored"))
    )

    if needs_exploration:
        logger.info(f"🔍 Running exploration for {topic_id}")
        exploration_results = explore_topic_fully(topic_id)
        save_topic_findings(topic_id, exploration_results)

    # Continue with normal analysis
    run_analysis_agents(topic_id)
```

**Tasks:**
- [ ] Update `write_all.py` to call exploration runner
- [ ] Add exploration results to analysis agent inputs
- [ ] Add `--skip-exploration` flag for testing
- [ ] Add `--force-exploration` flag to re-explore
- [ ] Update logging to show exploration progress
- [ ] Test full pipeline

---

### 2.2 Integrate into Analysis Agents
**Files**:
- `graph-functions/src/analysis_agents/*/agent.py`
- `graph-functions/src/analysis_agents/orchestrator.py`

**Update Analysis Agent Inputs:**
Each analysis agent should receive exploration findings in context.

**Example for Chain Reaction Map Agent:**
```python
def generate_chain_reaction_map(topic_id: str) -> str:
    # Load exploration findings
    findings = get_topic_exploration_findings(topic_id)

    context = build_analysis_context(topic_id)
    context["exploration_findings"] = {
        "risks": findings.get("risks", []),
        "opportunities": findings.get("opportunities", [])
    }

    # Agent prompt now includes:
    # "The exploration agent found these multi-hop connections:
    #  Risk 1: China Stimulus → Copper → Fed → EURUSD
    #  Risk 2: ..."

    result = agent.run(context)
    return result
```

**Tasks:**
- [ ] Update analysis orchestrator to load exploration findings
- [ ] Update each agent prompt to include exploration findings in context
- [ ] Ensure agents cite exploration findings when relevant
- [ ] Test that agents use exploration findings intelligently
- [ ] Update `ARCHITECTURE.md` with new data flow

---

### 2.3 Create Strategy Exploration Entrypoint
**File**: `graph-functions/entrypoints/explore_strategies.py` (NEW)

```python
"""
Strategy Exploration Entrypoint - Runs exploration for user strategies

Usage:
    # Explore a specific strategy
    python -m entrypoints.explore_strategies --user victor --strategy STRATEGY_ID

    # Explore all strategies for a user
    python -m entrypoints.explore_strategies --user victor

    # Explore all strategies for all users
    python -m entrypoints.explore_strategies --all
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="Username to explore strategies for")
    parser.add_argument("--strategy", help="Specific strategy ID")
    parser.add_argument("--all", action="store_true", help="Explore all strategies")
    parser.add_argument("--force", action="store_true", help="Re-explore even if complete")

    args = parser.parse_args()

    # Get strategies to explore
    strategies = get_strategies_to_explore(args)

    for username, strategy_id in strategies:
        logger.info(f"🔍 Exploring strategy {strategy_id} for {username}")

        try:
            results = explore_strategy_fully(username, strategy_id)
            save_strategy_findings(username, strategy_id, results)
            logger.info(f"✅ Completed: {len(results['risks'])} risks, {len(results['opportunities'])} opportunities")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
```

**Tasks:**
- [ ] Create `explore_strategies.py` entrypoint
- [ ] Add command-line interface
- [ ] Add progress tracking (which strategies completed)
- [ ] Add error recovery (resume after crash)
- [ ] Schedule in docker-compose (weekly cron?)
- [ ] Write documentation

---

## 🧪 Phase 3: Testing & Validation (Week 2)

### 3.1 Unit Tests
**New Test Files:**
- `graph-functions/tests/exploration_agent/test_topic_explorer_runner.py`
- `graph-functions/tests/exploration_agent/test_strategy_explorer_runner.py`
- `saga-be/tests/test_strategy_explorations.py`

**Test Coverage:**
- [ ] Topic exploration finds 3 risks and 3 opportunities
- [ ] Strategy exploration finds 3 risks and 3 opportunities
- [ ] Critic rejects low-quality findings
- [ ] Findings saved correctly to Neo4j
- [ ] Findings saved correctly to backend JSON
- [ ] API endpoints work correctly
- [ ] Duplicate findings handled correctly
- [ ] Quality ranking works (replaces worst finding)

---

### 3.2 Integration Tests
**Test Scenarios:**
- [ ] Run full topic writing pipeline with exploration
- [ ] Verify analysis agents receive and use exploration findings
- [ ] Run strategy exploration end-to-end
- [ ] Test error recovery (what if exploration fails?)
- [ ] Test performance (time per exploration run)
- [ ] Test LLM costs (tokens per run)

---

### 3.3 Manual Testing
**Test Topics:**
- [ ] `eurusd` - well-connected topic, should find good chains
- [ ] `copper` - commodity, cross-sector connections
- [ ] `china_stimulus` - policy topic, macro connections

**Test Strategies:**
- [ ] Victor's EURUSD strategy
- [ ] Random user strategy
- [ ] Strategy with minimal topic mapping

**Quality Checks:**
- [ ] Are findings non-obvious? (not 1-2 hop chains)
- [ ] Are chains defensible? (each link makes sense)
- [ ] Are citations accurate? (check source_ids)
- [ ] Do analysis agents use findings intelligently?

---

## 📚 Phase 4: Documentation & Operations (Week 3)

### 4.1 Code Documentation
**Files to Update:**
- [ ] `victor_deployment/docs/ARCHITECTURE.md` - Add exploration agent to data flow
- [ ] `victor_deployment/docs/INDEX.md` - Add new files and functions
- [ ] `graph-functions/README.md` - Document exploration runner usage
- [ ] In-code docstrings for all new functions

**New Documentation:**
- [ ] `victor_deployment/docs/EXPLORATION_AGENT.md` - Comprehensive guide
  - How exploration works
  - How findings are stored
  - How to trigger exploration
  - How to monitor quality
  - Troubleshooting guide

---

### 4.2 Operational Setup
**Monitoring:**
- [ ] Add exploration metrics to stats API
  - Topics explored count
  - Strategies explored count
  - Average quality scores
  - Rejection rates
  - Token usage

**Logging:**
- [ ] Structured logging for exploration runs
- [ ] Track exploration time per topic/strategy
- [ ] Log critic verdicts for quality analysis

**Scheduling:**
- [ ] Add strategy exploration to docker-compose
- [ ] Weekly cron: explore all user strategies
- [ ] Daily cron: explore new strategies
- [ ] On-demand: API endpoint to trigger exploration

---

## 🛠️ Phase 5: Project Management Setup (Week 3)

### 5.1 Lessons Learned System
**File**: `victor_deployment/Lessons/README.md`

```markdown
# Lessons Learned

This directory stores **lessons**, not summaries or status updates.

## Format

Each lesson should be:
- **Specific**: What exact problem/insight occurred
- **Actionable**: What should we do differently next time
- **Timestamped**: When did we learn this

## Template

Use `YYYY-MM-DD_lesson_name.md` format.

Example: `2025-12-25_llm_json_parsing_reliability.md`
```

**Tasks:**
- [ ] Create `Lessons/README.md`
- [ ] Create template: `Lessons/TEMPLATE.md`
- [ ] Document first lesson from exploration agent work

---

### 5.2 Project Agent Prompts
**File**: `victor_deployment/project_agent_prompts/README.md`

```markdown
# Project Agent Prompts

Quick commands for AI agents to maintain 10/10 code quality.

## Available Prompts

1. **code_quality_audit.md** - Find code quality issues
2. **find_improvements.md** - Suggest 1-3 improvements
3. **documentation_audit.md** - Check docs completeness
4. **test_coverage_audit.md** - Find missing tests
5. **security_audit.md** - Check for vulnerabilities
6. **architecture_review.md** - Validate structure consistency

## Usage

Copy prompt content and give to AI agent. Agent will analyze and report.
```

**Tasks:**
- [ ] Create `project_agent_prompts/README.md`
- [ ] Create `code_quality_audit.md` prompt
- [ ] Create `find_improvements.md` prompt
- [ ] Create `documentation_audit.md` prompt
- [ ] Create `test_coverage_audit.md` prompt
- [ ] Create `security_audit.md` prompt
- [ ] Create `architecture_review.md` prompt

---

## 📊 Success Metrics

### Code Quality
- [ ] All new code has docstrings
- [ ] All new code has type hints
- [ ] All new code has tests (>80% coverage)
- [ ] All prompts co-located with functions
- [ ] No silent try/except blocks

### Functionality
- [ ] Topics get 3 risks + 3 opportunities consistently
- [ ] Strategies get 3 risks + 3 opportunities consistently
- [ ] Critic acceptance rate > 70% (not too strict, not too loose)
- [ ] Findings are non-obvious (avg chain length > 3 hops)
- [ ] Analysis agents cite exploration findings

### Operations
- [ ] Exploration runs without manual intervention
- [ ] Errors logged and recoverable
- [ ] Token usage tracked and acceptable
- [ ] Run time < 5 min per topic/strategy
- [ ] Monitoring dashboard shows exploration status

---

## 🚨 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM costs too high | High | Add token budgets, use cheaper models for simple steps |
| Findings are low quality | High | Tune critic prompts, adjust chain length requirements |
| Integration breaks existing workflow | Medium | Feature flag, extensive testing before rollout |
| Exploration takes too long | Medium | Parallel runs, optimize graph queries |
| Storage grows too large | Low | Archive old findings, compress evidence |

---

## 🎯 Next Steps

1. **Week 1**: Complete Phase 1 (Core Integration)
2. **Week 2**: Complete Phase 2 (Workflow Integration) + Phase 3 (Testing)
3. **Week 3**: Complete Phase 4 (Documentation) + Phase 5 (Project Management)
4. **Week 4**: Buffer for polish, performance optimization, production rollout

---

## 📝 Notes

- Share exploration logs to tune prompts and critic
- Monitor token usage closely in first week
- Keep exploration findings separate from human-written analysis initially
- Plan for v2: user feedback on finding quality, active learning
