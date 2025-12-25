# Code Quality Audit

**Version**: 2025-12-25
**Estimated Time**: 10-15 minutes
**Output**: Comprehensive quality report with specific issues

---

## Task

Perform a systematic code quality audit of the codebase, checking for violations of our coding standards (defined in `/CLAUDE.md`).

This is a **diagnostic** task - find issues, don't fix them yet.

---

## Scope

**Primary:**
- `graph-functions/src/` - all Python code
- `saga-be/src/` - all Python code

**Secondary (if time):**
- `saga-fe/src/` - TypeScript/Svelte code

---

## Checks to Perform

### 1. Silent Error Handling
**What**: Find `except:` or `except Exception:` without re-raising or logging

**Good:**
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise  # Re-raise or handle specifically
```

**Bad:**
```python
try:
    result = risky_operation()
except:
    return None  # Silent failure - we never know what went wrong
```

**Output**: List of files and line numbers with silent exception handling

---

### 2. Missing Type Hints
**What**: Functions without type hints on parameters or return values

**Good:**
```python
def process_article(article: Article) -> ProcessedArticle:
    ...
```

**Bad:**
```python
def process_article(article):
    ...
```

**Output**: List of functions missing type hints (ignore `__init__`, test files)

---

### 3. Misplaced Prompts
**What**: Prompts in `src/llm/prompts/` that belong to specific functions

**Should Be:**
```
src/functions/evaluate_relevance/
  ├── __init__.py
  └── prompt.py  ← Prompt lives WITH the function
```

**Currently Wrong:**
```
src/llm/prompts/
  └── relevance_prompt.py  ← Centralized, far from function
```

**Output**: List of prompts that should be moved

---

### 4. Missing Docstrings
**What**: Complex functions (>20 lines) without docstrings

**Good:**
```python
def complex_operation(data: dict) -> Result:
    """
    Process data through multi-step pipeline.

    Args:
        data: Input data with 'field1', 'field2'

    Returns:
        Result with processed output
    """
    ...
```

**Bad:**
```python
def complex_operation(data: dict) -> Result:
    # No docstring
    ...
```

**Output**: List of complex functions without docstrings

---

### 5. Testing Gaps
**What**: Functions without `if __name__ == "__main__":` tests or separate test file

**Good:**
```python
def my_function(x: int) -> int:
    return x * 2

if __name__ == "__main__":
    assert my_function(2) == 4
    print("Tests passed")
```

**Bad:**
```python
def my_function(x: int) -> int:
    return x * 2

# No tests
```

**Output**: List of files missing test coverage

---

### 6. Unnecessary Complexity
**What**: Over-engineered code (abstract base classes, factories, etc.)

Check for:
- Abstract base classes with only one implementation
- Factory patterns for simple object creation
- Inheritance hierarchies >2 levels deep
- Design patterns without clear benefit

**Output**: Examples of over-engineering with simplification suggestions

---

### 7. Hardcoded Values
**What**: Magic numbers or strings that should be constants

**Good:**
```python
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

def fetch_data():
    for attempt in range(MAX_RETRIES):
        ...
```

**Bad:**
```python
def fetch_data():
    for attempt in range(3):  # Magic number
        ...
```

**Output**: List of hardcoded values that should be constants

---

## Output Format

```markdown
# Code Quality Audit Report
**Date**: YYYY-MM-DD
**Scope**: graph-functions/src, saga-be/src

---

## Summary
- ✅ **Passed**: [N] checks
- ⚠️ **Warnings**: [N] issues found
- ❌ **Critical**: [N] critical issues

**Overall Grade**: [A/B/C/D/F]

---

## 1. Silent Error Handling
**Status**: [✅ Pass | ⚠️ Warning | ❌ Critical]
**Issues Found**: [N]

### Critical Issues
- `src/graph/ops/article.py:145` - Bare `except:` catches all errors silently
- `src/analysis/utils.py:67` - Exception caught but not logged

### Details
[Brief explanation of why this matters]

---

## 2. Missing Type Hints
**Status**: [✅ Pass | ⚠️ Warning | ❌ Critical]
**Issues Found**: [N]

### Functions Missing Type Hints
- `src/functions/process_data/__init__.py:23` - `process_data()`
- `src/agents/analysis/critic/agent.py:89` - `_validate_finding()`

### Details
[Brief explanation]

---

[Continue for each check...]

---

## Recommendations

### High Priority (Fix This Week)
1. [Specific recommendation with file path]
2. [Specific recommendation with file path]

### Medium Priority (Fix This Month)
1. [Specific recommendation]

### Low Priority (Nice to Have)
1. [Specific recommendation]

---

## Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Functions with type hints | 85% | >90% | ⚠️ Below |
| Functions with docstrings | 70% | >80% | ⚠️ Below |
| Test coverage (est.) | 60% | >80% | ❌ Low |
| Silent exceptions | 5 | 0 | ❌ Fix |
| Misplaced prompts | 8 | 0 | ⚠️ Move |

---

## Next Steps

1. Address all ❌ Critical issues immediately
2. Create tickets for ⚠️ Warning issues
3. Schedule cleanup sprint for accumulated debt
4. Re-run this audit weekly to track progress
```

---

## Context

### Grading Scale

- **A (90-100)**: Production-ready, minimal issues
- **B (80-89)**: Good quality, some cleanup needed
- **C (70-79)**: Acceptable, notable issues to address
- **D (60-69)**: Needs improvement, quality issues affecting development
- **F (<60)**: Critical issues, not production-ready

### What's Critical vs Warning

**Critical (❌)**:
- Silent exception handling
- Missing error handling in critical paths
- Hardcoded credentials or secrets
- Functions that could cause data corruption

**Warning (⚠️)**:
- Missing type hints
- Missing docstrings
- Misplaced prompts
- Minor code smells

---

## Deliverable

Provide the full audit report in the format above.

Be specific with file paths and line numbers.

End with clear, prioritized next steps.
