# Documentation Audit

**Version**: 2025-12-25
**Estimated Time**: 5-10 minutes
**Output**: Documentation completeness report

---

## Task

Check if documentation accurately reflects the current codebase structure and is complete.

This is NOT about code comments - this is about the **system-level documentation** in `/victor_deployment/docs/`.

---

## Scope

**Documentation Files:**
- `victor_deployment/docs/ARCHITECTURE.md`
- `victor_deployment/docs/INDEX.md`
- `victor_deployment/docs/CLAUDE.md`
- `victor_deployment/docs/NETWORKING.md`
- Root `CLAUDE.md` (coding rules)

**Codebase Structure:**
- `graph-functions/src/` - functions, agents, graph ops
- `saga-be/src/` - API routes, storage
- `saga-fe/src/` - frontend routes, components

---

## Checks to Perform

### 1. INDEX.md Accuracy
**What**: Verify INDEX.md lists all major functions, agents, and routes

**Check:**
- [ ] All functions in `src/functions/` are listed
- [ ] All agents in `src/agents/` are listed
- [ ] All API routes in `saga-be/src/routes/` are listed
- [ ] All graph operations in `src/graph/ops/` are listed

**Output**: List of missing or outdated entries

---

### 2. ARCHITECTURE.md Current
**What**: Verify ARCHITECTURE.md matches actual system structure

**Check:**
- [ ] Data flow diagrams are accurate
- [ ] Repository structure matches actual folders
- [ ] API layer boundaries are correctly described
- [ ] New components added in last month are documented

**Output**: Sections that need updates

---

### 3. Missing Function Documentation
**What**: Find functions that exist in code but aren't documented anywhere

**Check:**
```bash
# Find all function directories
ls graph-functions/src/functions/

# Cross-reference with INDEX.md and ARCHITECTURE.md
```

**Output**: List of undocumented functions

---

### 4. Outdated Information
**What**: Find documentation that refers to old/moved/deleted code

**Examples:**
- "See `src/old_file.py`" but file doesn't exist
- "API endpoint `/old/route`" but route was changed
- "Uses model X" but now uses model Y

**Output**: List of outdated references with corrections

---

### 5. Missing "How To" Guides
**What**: Check if common tasks are documented

**Should Have Guides For:**
- [ ] How to add a new function
- [ ] How to add a new agent
- [ ] How to add a new API endpoint
- [ ] How to run tests
- [ ] How to deploy changes
- [ ] How to debug common issues

**Output**: List of missing guides

---

## Output Format

```markdown
# Documentation Audit Report
**Date**: YYYY-MM-DD
**Files Checked**: ARCHITECTURE.md, INDEX.md, CLAUDE.md, NETWORKING.md

---

## Summary
- ✅ **Up to Date**: [N] sections
- ⚠️ **Needs Update**: [N] sections
- ❌ **Missing**: [N] critical docs

**Overall Status**: [Current | Needs Minor Updates | Needs Major Updates]

---

## INDEX.md

### Missing Entries
- [ ] `src/functions/explore_topic/` - not listed in System Functions table
- [ ] `src/agents/exploration/` - not listed in Agents section
- [ ] `/api/strategies/explorations` - not listed in API Routes

### Outdated Entries
- [ ] `src/functions/old_classify/` - listed but no longer exists
- [ ] Description for `ingest_article` doesn't mention new deduplication

### Correct Entries
- [x] All graph operations listed
- [x] All API routes accurate

**Status**: ⚠️ Needs updates (3 missing, 2 outdated)

---

## ARCHITECTURE.md

### Outdated Sections
1. **Data Flow Examples** (Line 200-230)
   - Current: Shows old 3-step flow
   - Should Be: Include exploration agent in topic writing flow

2. **Repository Structure** (Line 110-150)
   - Current: Missing `exploration_agent/` directory
   - Should Be: Add exploration_agent under src/

### Missing Information
- Exploration agent integration not documented
- Strategy exploration workflow not shown
- Backend exploration API endpoints not mentioned

**Status**: ⚠️ Needs significant updates

---

## CLAUDE.md

### Status
✅ Up to date - no issues found

---

## Missing Guides

### Critical (Should Add)
1. **How to Run Exploration Agent**
   - Current: Only CLI usage in code comments
   - Need: Full guide in docs/

2. **How to Add Exploration Findings to Analysis**
   - Current: Not documented
   - Need: Guide for analysis agent developers

### Nice to Have
1. How to tune exploration quality
2. How to monitor exploration costs
3. Troubleshooting exploration failures

---

## Recommendations

### High Priority
1. Update INDEX.md to include exploration agent components
2. Update ARCHITECTURE.md data flow to show exploration integration
3. Create "How to Run Exploration Agent" guide

### Medium Priority
1. Fix outdated references in INDEX.md
2. Add exploration agent to system diagram in ARCHITECTURE.md

### Low Priority
1. Create troubleshooting guide for exploration
2. Document exploration quality metrics

---

## Proposed Updates

### INDEX.md Changes

**Add to System Functions:**
```markdown
| **Explore Topic** | `src/exploration_agent/` | Find multi-hop risks/opportunities |
```

**Add to Agents:**
```markdown
### Exploration Agent (`src/exploration_agent/`)
| Agent | Purpose |
|-------|---------|
| `explorer/` | Autonomous graph exploration |
| `critic/` | Validates exploration findings |
```

---

### ARCHITECTURE.md Changes

**Update Data Flow - Topic Writing:**
```markdown
### Topic Analysis Generation (UPDATED)
User request → saga-be → graph-functions/src/agents/analysis/orchestrator.py
            → **Exploration Agent** (find risks/opportunities)
            → Multiple analysis agents (use exploration findings)
            → Results saved to Neo4j
```

**Add New Section:**
```markdown
### Exploration Agent
The exploration agent autonomously discovers multi-hop connections by:
1. Starting at a topic
2. Reading articles and analysis sections
3. Moving through connected topics
4. Saving evidence excerpts
5. Drafting findings validated by critic

Outputs 3 risks + 3 opportunities per topic/strategy.
```

---

## Next Steps

1. Review this report
2. Prioritize updates (start with INDEX.md)
3. Assign documentation tasks
4. Set deadline for completion
5. Re-run audit after updates
```

---

## Deliverable

Provide the full report in the format above.

Be specific about what's wrong and how to fix it.

Include proposed text for major updates.
