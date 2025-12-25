# Check Architecture Compliance (Bidirectional)

**Version**: 2025-12-25-v2
**Estimated Time**: 10-15 minutes
**Output**: Code violations AND architecture documentation gaps

---

## Task

**BIDIRECTIONAL COMPLIANCE CHECK:**

1. **Code → Rules**: Find code that violates CLAUDE.md principles
2. **Rules → Reality**: Find where ARCHITECTURE.md is outdated vs actual code structure

This ensures both code quality AND documentation accuracy.

---

## Scope

**Code:**
- `graph-functions/src/` - all Python code
- `saga-be/src/` - all Python code
- `saga-fe/src/` - TypeScript/Svelte code

**Documentation:**
- `/CLAUDE.md` - coding principles
- `victor_deployment/docs/ARCHITECTURE.md` - system structure
- `victor_deployment/docs/INDEX.md` - file index

---

## Principles to Check

### 1. Simplest Possible Code
**Rule**: No unnecessary abstractions, design patterns, or clever code

**Check For:**
- Abstract base classes with only one implementation
- Factory patterns for simple object creation
- Overly generic code that's only used once
- Inheritance hierarchies >2 levels

**Good:**
```python
def process_article(article: Article) -> ProcessedArticle:
    classified = classify_article(article)
    topics = find_topics(classified)
    return ProcessedArticle(article, topics)
```

**Bad:**
```python
class ArticleProcessorFactory:
    def create_processor(self, type: str) -> AbstractProcessor:
        return self._registry[type]()
```

**Output**: Files with unnecessary abstractions

---

### 2. Fail Fast - No Hidden Errors
**Rule**: No bare `except:` blocks, only catch exceptions you can handle

**Check For:**
- `except:` or `except Exception:` without re-raising
- Try/except wrapping large blocks of code
- Exceptions caught but not logged

**Good:**
```python
try:
    return db.query(id)
except ConnectionError as e:
    logger.error(f"DB unavailable: {e}")
    raise DatabaseUnavailable(f"Cannot reach DB: {e}")
# Let other exceptions propagate
```

**Bad:**
```python
try:
    return db.query(id)
except:
    return None  # Silent failure
```

**Output**: Files with silent error handling

---

### 3. Types Everywhere (Especially LLM)
**Rule**: All LLM responses must use Pydantic models, function signatures must have type hints

**Check For:**
- LLM calls returning `dict` instead of Pydantic model
- Functions missing type hints (especially public APIs)
- Use of `Any` type where specific type is known

**Good:**
```python
class ArticleClassification(BaseModel):
    category: str
    confidence: float

def classify_article(text: str) -> ArticleClassification:
    return llm.complete(prompt, response_model=ArticleClassification)
```

**Bad:**
```python
def classify_article(text: str) -> dict:
    return llm.complete(prompt)  # Untyped dict
```

**Output**: Functions violating type requirements

---

### 4. Co-located Code
**Rule**: Prompts live with functions, tests live with code

**Check For:**
- Prompts in `src/llm/prompts/` that belong to specific functions
- Test files far from code they test
- Helpers scattered across multiple directories

**Good:**
```
src/functions/evaluate_relevance/
├── __init__.py      # Main function + if __name__ test
├── prompt.py        # Prompt right here
└── helpers.py       # Optional helpers
```

**Bad:**
```
src/functions/evaluate_relevance/__init__.py  # Function here
src/llm/prompts/relevance_prompt.py           # Prompt far away
tests/test_relevance.py                        # Test far away
```

**Output**: Files that should be moved

---

### 5. Function Template Compliance
**Rule**: Functions should follow the template structure

**Check For:**
- Functions missing `if __name__ == "__main__":` tests
- Functions without docstrings (Input → Process → Output format)
- Functions missing co-located prompts when they use LLMs

**Template:**
```python
"""
Function Name

Input: What it receives
Process: What it does
Output: What it returns
"""

from pydantic import BaseModel

class OutputModel(BaseModel):
    field: str

def my_function(input: InputType) -> OutputModel:
    """Brief description"""
    from .prompt import MY_PROMPT

    llm = get_llm(complexity="simple")
    result = llm.complete(MY_PROMPT, response_model=OutputModel)
    return result

if __name__ == "__main__":
    # Quick test
    result = my_function(test_input)
    assert result.field == "expected"
    print("✅ Tests passed")
```

**Output**: Functions not following template

---

---

## PART 2: Reality → Architecture (Find Documentation Gaps)

### Check 1: Missing Components in ARCHITECTURE.md

**What**: Find directories/components that exist but aren't documented

**Method:**
1. List all directories in `graph-functions/src/`
2. Check if each is mentioned in ARCHITECTURE.md
3. Find undocumented components

**Example:**
```
Found: graph-functions/src/exploration_agent/
ARCHITECTURE.md: No mention of exploration agent
→ GAP: exploration_agent needs to be added to docs
```

**Output**: List of undocumented components

---

### Check 2: Outdated Structure in ARCHITECTURE.md

**What**: Find documentation that describes code that no longer exists

**Method:**
1. Read ARCHITECTURE.md structure diagrams
2. Verify each mentioned file/directory exists
3. Flag outdated references

**Example:**
```
ARCHITECTURE.md mentions: "src/old_classifier/"
Reality: Directory doesn't exist (moved to src/functions/classify/)
→ OUTDATED: Update ARCHITECTURE.md
```

**Output**: Outdated documentation references

---

### Check 3: Missing in INDEX.md

**What**: Functions, agents, routes not listed in INDEX.md

**Method:**
1. List all directories in `src/functions/`, `src/agents/`, etc.
2. Check if each appears in INDEX.md tables
3. Report missing entries

**Output**: Components to add to INDEX.md

---

### Check 4: Architecture Should Evolve

**What**: Find patterns in code suggesting architecture should change

**Examples:**
- Many functions doing similar things → Should create shared abstraction
- Component has grown too large → Should split
- New pattern emerged → Should document it

**Look For:**
- Repeated code patterns (3+ occurrences)
- Directories with >10 files (might need splitting)
- New integration patterns not in ARCHITECTURE.md

**Output**: Suggested architecture improvements

---

## Output Format

```markdown
# Bidirectional Architecture Compliance Report
**Date**: YYYY-MM-DD
**Scan**: Code ↔ Architecture Docs
**Files Scanned**: [N]

---

## EXECUTIVE SUMMARY

### Code Quality
- ✅ **Compliant**: [N] files
- ⚠️ **Minor Issues**: [N] files
- ❌ **Major Violations**: [N] files
- **Code Compliance**: [X]%

### Documentation Quality
- ✅ **Current**: [N] components documented
- ⚠️ **Outdated**: [N] references need updates
- ❌ **Missing**: [N] components undocumented
- **Doc Completeness**: [X]%

---

## PART A: CODE VIOLATIONS (Code → Rules)

---

## 1. Simplest Possible Code
**Status**: [✅ | ⚠️ | ❌]
**Violations**: [N]

### Issues Found

**src/graph/ops/base.py**
- **Line 15-50**: Abstract base class `BaseOperation` with only one implementation
- **Why Bad**: Adds complexity without benefit
- **Fix**: Remove base class, make `ArticleOperation` a concrete class

**src/functions/process_data/factory.py**
- **Line 23-45**: Factory pattern for creating simple processor objects
- **Why Bad**: Only one processor type, factory not needed
- **Fix**: Remove factory, directly instantiate processor

### Compliant Examples
- ✅ `src/functions/evaluate_relevance/__init__.py` - Simple function, no over-engineering

---

## 2. Fail Fast - No Hidden Errors
**Status**: [✅ | ⚠️ | ❌]
**Violations**: [N]

### Critical Issues

**src/graph/ops/article.py:145**
```python
try:
    result = client.run(query)
except:  # ❌ Bare except
    return None
```
- **Fix**: Catch specific exception, log, and re-raise

**src/api/backend_client.py:89**
```python
try:
    response = requests.post(url)
except Exception as e:  # ❌ Caught but not logged
    return {}
```
- **Fix**: Log error before returning default

---

## 3. Types Everywhere
**Status**: [✅ | ⚠️ | ❌]
**Violations**: [N]

### Missing Pydantic Models

**src/functions/classify_article/__init__.py:34**
```python
def classify(text: str) -> dict:  # ❌ Should return Pydantic model
    return llm.complete(prompt)
```
- **Fix**: Create `ArticleClassification(BaseModel)` and use as response_model

### Missing Type Hints

- `src/agents/analysis/writer/agent.py:67` - `_format_output()` missing return type
- `src/graph/ops/topic.py:123` - `get_topics()` missing parameter types

---

## 4. Co-located Code
**Status**: [✅ | ⚠️ | ❌]
**Violations**: [N]

### Misplaced Prompts

These prompts should be moved to live with their functions:

| Current Location | Should Be | Function |
|-----------------|-----------|----------|
| `src/llm/prompts/relevance_prompt.py` | `src/functions/evaluate_relevance/prompt.py` | `evaluate_relevance()` |
| `src/llm/prompts/classification_prompt.py` | `src/functions/classify_article/prompt.py` | `classify_article()` |

### Scattered Tests

- `tests/test_relevance.py` should be `src/functions/evaluate_relevance/test.py`

---

## 5. Function Template Compliance
**Status**: [✅ | ⚠️ | ❌]
**Violations**: [N]

### Missing if __name__ == "__main__" Tests

- `src/functions/process_data/__init__.py`
- `src/functions/generate_summary/__init__.py`

### Missing Docstrings

- `src/functions/analyze_sentiment/__init__.py` - No module-level docstring
- `src/agents/strategy/risk_assessor/agent.py` - No Input→Process→Output format

---

## Recommendations

### Critical (Fix Immediately)
1. Fix all bare `except:` blocks (2 found) - **Security/Reliability**
2. Add Pydantic models for LLM responses (3 functions) - **Type Safety**

### High Priority (Fix This Week)
1. Move misplaced prompts to functions (5 prompts) - **Code Organization**
2. Remove unnecessary abstractions (2 base classes) - **Simplicity**
3. Add type hints to public functions (8 functions) - **Type Safety**

### Medium Priority (Fix This Month)
1. Add `if __name__` tests to functions (12 functions) - **Testing**
2. Update docstrings to Input→Process→Output format (6 functions) - **Documentation**

---

## Metrics

| Principle | Compliance | Target |
|-----------|-----------|--------|
| Simplest Code | 85% | 95% |
| Fail Fast | 70% | 100% |
| Types Everywhere | 80% | 95% |
| Co-located Code | 75% | 95% |
| Template Compliance | 65% | 90% |
| **Overall** | **75%** | **95%** |

---

## PART B: DOCUMENTATION GAPS (Reality → Architecture)

### 1. Missing Components in ARCHITECTURE.md
**Status**: [✅ | ⚠️ | ❌]
**Missing**: [N]

**Undocumented Components:**

**graph-functions/src/exploration_agent/**
- **Current State**: Fully implemented with explorer, critic, orchestrator
- **In ARCHITECTURE.md**: ❌ Not mentioned
- **Should Add**:
  ```markdown
  ## Exploration Agent
  Autonomous graph explorer that discovers multi-hop risks/opportunities
  - explorer/ - Main exploration loop with tool calling
  - critic/ - Validates findings for quality
  - orchestrator.py - Entry point for exploration runs
  ```

**saga-be/src/routes/strategies.py - exploration endpoints**
- **Current State**: May have /explorations endpoints (check logs)
- **In ARCHITECTURE.md**: ❌ Not listed in API routes
- **Should Add**: To backend routes section if exists

---

### 2. Outdated References in ARCHITECTURE.md
**Status**: [✅ | ⚠️ | ❌]
**Outdated**: [N]

**Found Outdated:**

**Line 150: Repository structure mentions...**
- Example: If ARCHITECTURE.md shows old directory but it's been moved
- **Fix**: Update structure diagram

---

### 3. Missing from INDEX.md
**Status**: [✅ | ⚠️ | ❌]
**Missing**: [N]

**Should Add to INDEX.md:**

| Component | Type | Current Status | Should Be Listed Under |
|-----------|------|----------------|----------------------|
| `exploration_agent/` | Agent | ❌ Missing | Agents section |
| `exploration_agent/explorer/` | Sub-agent | ❌ Missing | Agents section |
| `exploration_agent/critic/` | Sub-agent | ❌ Missing | Agents section |
| `topic_explorer_runner.py` | Function | ❌ Missing | System Functions (if created) |
| `strategy_explorer_runner.py` | Function | ❌ Missing | System Functions (if created) |

---

### 4. Suggested Architecture Evolution
**Status**: Observations
**Suggestions**: [N]

**Pattern: Exploration Integration**
- **Observation**: Exploration agent is standalone, not integrated into write_all.py workflow
- **Suggest**: ARCHITECTURE.md should document exploration as part of topic/strategy writing flow
- **Impact**: Makes system design clearer
- **Proposed Addition**:
  ```markdown
  ## Topic Writing Flow (UPDATED)
  1. Load topic from Neo4j
  2. **Run exploration** (find 3 risks + 3 opportunities)
  3. Run analysis agents (receive exploration findings)
  4. Write sections to Neo4j
  ```

**Pattern: Finding Storage**
- **Observation**: No documented strategy for storing exploration findings
- **Suggest**: ARCHITECTURE.md should document:
  - Neo4j properties for topic findings (risk_1, risk_2, etc.)
  - Backend JSON structure for strategy findings
- **Impact**: Clarifies data model

---

## COMBINED RECOMMENDATIONS

### Critical Actions (This Week)

**Code Fixes:**
1. [From Part A - Critical code violations]

**Documentation Updates:**
1. Add exploration_agent to ARCHITECTURE.md structure
2. Add exploration components to INDEX.md
3. Update topic writing flow in ARCHITECTURE.md

### High Priority (This Month)

**Code:**
1. [From Part A - High priority violations]

**Documentation:**
1. Document exploration findings data model
2. Add exploration API endpoints to docs (if they exist)
3. Create "How to Run Exploration" guide

### Architecture Evolution Suggestions

**Consider:**
1. Should exploration be part of core workflow or on-demand?
2. Should findings be versioned (track changes over time)?
3. Should we document quality thresholds for exploration?

---

## Action Plan

1. **Fix Critical Code Issues** (security/reliability) → Immediate
2. **Update ARCHITECTURE.md** → This week
3. **Update INDEX.md** → This week
4. **Address Code Quality Issues** → This month
5. **Re-run this audit** → After fixes

---

## Documentation Update Draft

### For ARCHITECTURE.md

**Add to "Repository Structure" section:**
```markdown
├── exploration_agent/    # Autonomous graph explorer
│   ├── explorer/         # Main exploration agent
│   │   ├── agent.py      # Exploration loop with tool calling
│   │   ├── tools.py      # Graph queries and navigation
│   │   └── prompt.py     # Exploration system prompt
│   ├── critic/           # Finding validation
│   │   ├── agent.py      # Critic evaluation
│   │   ├── models.py     # Verdict models
│   │   └── prompt.py     # Critic system prompt
│   ├── orchestrator.py   # Entry point CLI
│   └── models.py         # Shared data models
```

**Add to "Data Flow Examples" section:**
```markdown
### 4. Exploration Agent Discovery
User triggers exploration → exploration_agent/orchestrator.py
                        → ExplorationAgent explores graph
                        → CriticAgent validates finding
                        → Saves to Neo4j (topics) or Backend (strategies)
```

### For INDEX.md

**Add to "Agents" section:**
```markdown
### Exploration Agent (`src/exploration_agent/`)
| Component | Purpose |
|-----------|---------|
| `explorer/` | Autonomous graph navigation and finding discovery |
| `critic/` | Validates exploration findings for quality |
| `orchestrator.py` | CLI entry point for exploration runs |
```
```

---

## Deliverable

Provide the **full bidirectional report** with:

### Part A: Code Violations
- Specific files, line numbers, and fixes
- Prioritized by severity

### Part B: Documentation Gaps
- What's missing from ARCHITECTURE.md
- What's missing from INDEX.md
- Outdated references to fix
- Suggested architecture evolutions

### Combined Action Plan
- Clear priorities (critical → high → medium)
- Proposed documentation updates (copy-pasteable)
- Timeline for fixes
