# Find Improvements

**Version**: 2025-12-25
**Estimated Time**: 5-10 minutes
**Output**: 1-3 specific, high-impact improvements

---

## Task

Analyze the codebase and suggest **1-3 specific improvements** that would have high impact on code quality, performance, or maintainability.

Focus on **quick wins** - things that can be done in 1-2 hours but provide significant value.

---

## Scope

**Primary Focus:**
- `graph-functions/src/` - Core engine code
- `saga-be/src/` - Backend API code
- `victor_deployment/docs/` - Documentation

**What to Check:**
1. Code that violates CLAUDE.md principles (found in root `/CLAUDE.md`)
2. Missing abstractions that cause duplication
3. Confusing naming or structure
4. Missing documentation for complex logic
5. Performance bottlenecks (obvious ones)
6. Error handling gaps

---

## Output Format

For each improvement:

```markdown
## Improvement N: [Short Title]

**Impact**: [High | Medium | Low]
**Effort**: [1-2 hours | 2-4 hours | 1 day]
**Category**: [Code Quality | Performance | Maintainability | Documentation]

### Problem
[What's wrong currently - be specific with file paths and line numbers if possible]

### Proposed Solution
[What to change - concrete steps]

### Why This Matters
[Impact on users, developers, or system quality]

### Files Affected
- `path/to/file.py` - [what changes]
- `path/to/other.py` - [what changes]
```

---

## Example Output

```markdown
## Improvement 1: Consolidate Duplicate Error Handling in Graph Operations

**Impact**: High
**Effort**: 1-2 hours
**Category**: Code Quality

### Problem
Files `graph-functions/src/graph/ops/article.py`, `topic.py`, and `link.py` all have
nearly identical try/except blocks for Neo4j connection errors. This is ~50 lines of
duplicated code that needs to be maintained in 3 places.

Example from article.py:142-156, topic.py:89-103, link.py:67-81.

### Proposed Solution
Create `src/graph/utils/error_handling.py`:
```python
def with_neo4j_error_handling(func):
    """Decorator for consistent Neo4j error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Neo4jError as e:
            logger.error(f"Neo4j error in {func.__name__}: {e}")
            raise DatabaseError(f"Graph operation failed: {e}")
    return wrapper
```

Then replace all duplicate blocks with `@with_neo4j_error_handling`.

### Why This Matters
- Single source of truth for error handling
- Easier to improve error messages or add monitoring
- 50 fewer lines to maintain
- Future graph ops inherit good error handling

### Files Affected
- `src/graph/utils/error_handling.py` - new file
- `src/graph/ops/article.py` - replace try/except with decorator
- `src/graph/ops/topic.py` - replace try/except with decorator
- `src/graph/ops/link.py` - replace try/except with decorator
```

---

## What Makes a Good Improvement

✅ **Good:**
- Specific problem with concrete solution
- Clear impact and effort estimate
- Can be completed independently
- Makes codebase objectively better

❌ **Bad:**
- "Improve code quality" (too vague)
- "Rewrite everything in Rust" (too large, unclear benefit)
- "Add more comments" (doesn't solve root issue)
- "Make it faster" (no specific bottleneck identified)

---

## Context

### Project Principles (from CLAUDE.md)

1. **Simplest Possible Code** - no unnecessary abstractions
2. **Fail Fast** - no silent errors
3. **Types Everywhere** - especially for LLM responses
4. **Co-located Code** - prompts with functions, tests with code

### Common Issues to Look For

- Functions in `src/llm/prompts/` that should be with their functions
- Bare `except:` or `except Exception:` blocks
- Missing type hints on function signatures
- Missing docstrings on complex functions
- Duplicated logic across files
- Graph queries that could be optimized (N+1 queries)

---

## Deliverable

Provide exactly **1-3 improvements** in the format above.

If you find more than 3, pick the ones with highest impact-to-effort ratio.

End with a summary:
```markdown
## Summary
Found [N] high-impact improvements:
1. [Title] - [Impact/Effort]
2. [Title] - [Impact/Effort]
3. [Title] - [Impact/Effort]

Estimated total effort: [X] hours
Expected impact: [brief description]
```
