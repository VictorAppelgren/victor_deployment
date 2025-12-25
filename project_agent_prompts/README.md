# Project Agent Prompts

> **Purpose**: Ready-to-use prompts for AI agents to maintain 10/10 code quality
> **Usage**: Copy prompt and paste to AI agent for immediate analysis

These are **executable tasks**, not vague requests. Each prompt is specific, scoped, and produces actionable output.

---

## Philosophy

Instead of "improve the code", we have:
- ✅ "Find all functions missing type hints and list them"
- ✅ "Check for silent try/except blocks and suggest explicit error handling"
- ✅ "Find prompts in src/llm/prompts/ that should be co-located with functions"

This makes AI agents **surgical** rather than scattershot.

---

## Available Prompts

### 🔍 Code Quality
- **`code_quality_audit.md`** - Comprehensive code quality check
- **`find_silent_exceptions.md`** - Find dangerous error handling
- **`check_type_hints.md`** - Verify type hint coverage
- **`find_missing_docstrings.md`** - Find undocumented functions

### 📚 Documentation
- **`documentation_audit.md`** - Check docs completeness
- **`update_index.md`** - Verify INDEX.md reflects current structure
- **`update_architecture.md`** - Check ARCHITECTURE.md is current

### 🧪 Testing
- **`test_coverage_audit.md`** - Find untested code
- **`check_test_quality.md`** - Review existing tests for quality

### 🏗️ Architecture
- **`find_misplaced_prompts.md`** - Find prompts not co-located
- **`check_architecture_compliance.md`** - Verify code follows CLAUDE.md rules
- **`suggest_refactoring.md`** - Find code that violates simplicity principle

### 🔒 Security
- **`security_audit.md`** - Check for vulnerabilities
- **`find_secrets.md`** - Find hardcoded credentials

### 🚀 Performance
- **`find_n_plus_one_queries.md`** - Find inefficient graph queries
- **`check_llm_costs.md`** - Estimate token usage and costs

### 💡 Improvements
- **`find_improvements.md`** - Suggest 1-3 high-impact improvements
- **`quick_wins.md`** - Find easy, high-value fixes

---

## How to Use

### For Humans
1. Open the relevant prompt file
2. Copy the entire contents
3. Paste to your AI agent (Claude, ChatGPT, etc.)
4. Review output and take action

### For AI Agents
When starting a new session or stuck:
1. Check relevant prompts in this directory
2. Run 1-2 prompts to understand current state
3. Use findings to guide your work
4. Update prompts if you discover new patterns to check

---

## Prompt Template

Each prompt should follow this structure:

```markdown
# [Prompt Title]

## Task
[1-2 sentence description of what to do]

## Scope
[What files/directories to check]

## Output Format
[Exact format for results - table, list, etc.]

## Example
[Show what good output looks like]

## Context
[Any background info needed to complete task]
```

---

## Creating New Prompts

### When to Create a Prompt

Create a new prompt when:
1. You manually check something repeatedly (automate it)
2. Code quality issue keeps recurring (prevent it)
3. New pattern emerges that should be validated (codify it)

### Prompt Quality Checklist

Good prompts are:
- [ ] **Specific**: Clear, bounded task
- [ ] **Scoped**: Exact files/directories to check
- [ ] **Actionable**: Output directly leads to fixes
- [ ] **Example-driven**: Shows what success looks like
- [ ] **Fast**: Completable in < 5 minutes

---

## Quick Reference

| Need | Use This Prompt |
|------|-----------------|
| "Is the code clean?" | `code_quality_audit.md` |
| "What should we fix next?" | `find_improvements.md` |
| "Are docs up to date?" | `documentation_audit.md` |
| "Any security issues?" | `security_audit.md` |
| "What's not tested?" | `test_coverage_audit.md` |
| "Is architecture consistent?" | `check_architecture_compliance.md` |

---

## Meta

- **Owner**: Entire team
- **Review**: Update prompts when new patterns emerge
- **Version**: Prompts should be dated - archive old versions
