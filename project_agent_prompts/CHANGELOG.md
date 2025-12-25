# Project Agent Prompts - Changelog

## 2025-12-25 - Initial Setup + Bidirectional Compliance

### Created
- `README.md` - Index of all agent prompts
- `find_improvements.md` - Suggest 1-3 high-impact improvements
- `code_quality_audit.md` - Comprehensive quality check
- `documentation_audit.md` - Verify docs are current
- `security_audit.md` - Security vulnerability scan
- `check_architecture_compliance.md` - **Bidirectional** compliance check

### Key Feature: Bidirectional Architecture Compliance

**Version**: 2025-12-25-v2

**What Changed**: `check_architecture_compliance.md` now performs **TWO-WAY** checking:

1. **Code → Rules** (Original)
   - Find code violating CLAUDE.md principles
   - Silent exceptions, missing types, over-engineering, etc.

2. **Reality → Architecture** (NEW)
   - Find components that exist but aren't documented
   - Find outdated references in ARCHITECTURE.md
   - Find missing entries in INDEX.md
   - Suggest where architecture should evolve

**Why This Matters**:
- Catches **documentation drift** - when code evolves but docs don't
- Identifies **architectural gaps** - patterns suggesting structure should change
- Ensures **both code quality AND documentation accuracy**
- Makes architecture a **living document** not a snapshot

**Example Output**:
```
PART A: Code Violations
- 5 bare except blocks found
- 3 functions missing type hints

PART B: Documentation Gaps
- exploration_agent/ exists but not in ARCHITECTURE.md
- INDEX.md missing 3 new components
- Suggest: Document exploration as part of topic writing flow
```

### Usage

**Run bidirectional compliance:**
```bash
# Copy contents of check_architecture_compliance.md
# Paste to AI agent
# Receive comprehensive report with:
#  - Code quality issues
#  - Documentation gaps
#  - Proposed doc updates (copy-pasteable)
#  - Combined action plan
```

### Next Steps

When new patterns emerge:
1. Add them to relevant prompt
2. Update this CHANGELOG
3. Re-run prompts to catch issues early
