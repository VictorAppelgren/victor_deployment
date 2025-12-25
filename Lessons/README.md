# Lessons Learned

> **Purpose**: Capture specific, actionable lessons from development work
> **Not For**: Summaries, status updates, TODO lists, or meeting notes

This directory is for **permanent knowledge** that makes the team smarter over time.

---

## What is a Lesson?

A lesson is:
- ✅ **Specific**: Concrete problem or insight, not vague observation
- ✅ **Actionable**: What should we do differently next time
- ✅ **Reusable**: Applies to future similar situations
- ✅ **Timestamped**: When we learned this

A lesson is NOT:
- ❌ "We worked on the exploration agent today"
- ❌ "The integration was complex"
- ❌ "Need to improve code quality"

---

## Format

**Filename**: `YYYY-MM-DD_short_topic_name.md`

**Example**: `2025-12-25_llm_json_parsing_reliability.md`

**Template**: See `TEMPLATE.md`

---

## Categories

- **Architecture**: System design decisions and trade-offs
- **LLM**: Prompt engineering, model behavior, cost optimization
- **Testing**: What testing strategies worked or failed
- **Performance**: Optimization insights
- **Integration**: How to integrate new components
- **DevOps**: Deployment, monitoring, operations
- **Code Quality**: Patterns that improve or hurt maintainability

---

## How to Use

### When to Write a Lesson

Write a lesson when you:
1. Solve a tricky bug and learn why it happened
2. Try an approach that fails and learn what works instead
3. Discover a pattern that significantly improves code quality
4. Find a gotcha in a library/framework
5. Make a design decision with important trade-offs

### How AI Agents Use This

Before starting complex work, AI agents should:
1. Read recent lessons in relevant category
2. Apply lessons to current task
3. Write new lesson if they learn something valuable

This creates a **learning flywheel** where the codebase gets better over time.

---

## Examples

**Good Lesson:**
```
Title: LLM JSON Parsing Requires Fallback Extraction
Date: 2025-12-25
Category: LLM

Problem: LLMs sometimes return valid JSON wrapped in markdown code blocks,
or with extra explanatory text, causing json.loads() to fail.

Solution: Always clean response before parsing:
- Strip ```json and ``` markers
- Try to extract first complete JSON object via brace counting
- Log failures but continue with fallback

Code: See _extract_tool_from_text() in exploration_agent/agent.py

Impact: Reduced LLM call failures from 15% to <1%
```

**Bad "Lesson":**
```
Title: Worked on exploration agent
Date: 2025-12-25

We integrated the exploration agent today. It was complex.
Need to improve code quality.
```

---

## Current Lessons

(This section auto-updated by scripts or manually maintained)

### 2025-12
- None yet - start writing lessons!

---

## Meta

- **Owner**: Entire team (humans + AI agents)
- **Review**: Weekly review of new lessons
- **Cleanup**: Archive lessons older than 2 years unless critical
