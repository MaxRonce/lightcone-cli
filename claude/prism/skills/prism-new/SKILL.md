---
name: prism-new
description: Create a new ASP analysis project - scope research question, structure outputs and decisions with literature support
allowed-tools: Read, Write(asp.yaml), Write(universes/*), Write(CLAUDE.md), Edit(asp.yaml), Edit(universes/*), Edit(CLAUDE.md), Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(mkdir:*), WebSearch, WebFetch, AskUserQuestion
---

# /prism-new

Create a new ASP analysis project through conversation. Build the spec iteratively so the user can watch it take shape in the navigator.

## References

- [Prism Reference](./../prism/SKILL.md) — core concepts, CLI, validation
- [Decision Guide](./decision-guide.md) — how to identify and structure decisions
- [UI Brand](./../ui-brand.md) — visual formatting patterns

## Setup

1. Read `asp.yaml` if it exists (to understand context or avoid overwriting)
2. Note the analysis directory for later

---

## Phase 1: Research Question

Display stage banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► RESEARCH QUESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Start with an open question:

> "What are you trying to learn? Describe the question in your own words."

Then sharpen:
- "What would a clear answer look like?" (becomes success criteria)
- "Why does this matter?" (context for decisions)

Don't checklist-walk. Follow what the user is uncertain or excited about.

**Write to asp.yaml:**
```yaml
version: "1.0"
name: "<analysis name>"
description: |
  <problem statement from conversation>
success_criteria:
  - "<concrete criterion>"
```

This gives the user something to see in the navigator immediately.

---

## Phase 2: Analysis Structure

Display stage banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► ANALYSIS STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Understand the pipeline:

> "Walk me through how you'd do this step by step. What happens first? What would you want to check before moving on?"

From this, identify **outputs and their dependencies**:
- Single flat analysis if it's a straightforward pipeline
- Multiple sub-analyses (via `analyses:`) if there are clear stages with inspectable intermediate outputs

For multi-stage analyses, map:
- What outputs does each stage produce? (outputs with recipes)
- What does the next stage consume? (inputs with `from:` references)
- What decisions belong where?

Then ask:

> "Want to fully scope all stages now, or start with [first stage]?"

**Update asp.yaml** with structure:
```yaml
inputs:
  - id: <input_id>
    type: data
    source: "<path or URL>"
outputs:
  - id: <output_id>
    type: <figure|table|data|metric|report>

# For multi-stage analyses, use sub-analyses:
analyses:
  first_stage:
    description: "What this stage accomplishes"
    inputs:
      - id: stage_input
        type: data
        from: <parent_input_id>
    outputs:
      - id: intermediate_output
        type: data
        recipe:
          command: python src/first_stage.py

  second_stage:
    inputs:
      - id: stage_input
        type: data
        from: first_stage.intermediate_output
    outputs:
      - id: final_result
        type: figure
    # decisions TBD
```

---

## Phase 3: Deep Dive

Display stage banner (repeat for each section being scoped):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► DEEP DIVE — [SECTION NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For each section of the analysis being scoped, explore:

1. **Decisions** — What choices matter? See [decision-guide.md](./decision-guide.md)
2. **Data** — What does the input look like? (characteristics that affect decisions)
3. **Assumptions** — What could go wrong? What's load-bearing?

This is one exploratory conversation, not a rigid sequence. Cover what's relevant.

**Update asp.yaml incrementally** as decisions are identified. Don't wait until the end.

### Literature Notes

As methods are mentioned, note papers for later:
- Ask: "Are there specific papers that should inform this?"
- Note any papers/methods the user mentions
- Don't extract insights yet — that's a separate step with `/prism-insights`

### Tracking Decision Review Status

When the user explicitly weighs in on a decision, note it in `CLAUDE.md` (in the Key Decisions section). Decisions you infer or fill with defaults should be surfaced for confirmation during the build phase.

---

## Checkpoint

> "Anything else that should inform this analysis?"

Review the spec with the user. Update asp.yaml with any additions.

---

## Compute Configuration (optional)

**Only activate this phase if the user mentions remote/HPC execution.**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► COMPUTE CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Check if any execution targets are configured:

```bash
prism remote setup --list
```

If the user needs to run on a remote cluster:

> "Do you need to configure a remote execution target (e.g., SLURM cluster)?"

If yes:
- Guide them through `prism remote setup <name>`
- Note the target name for later use with `prism run --target <name>`

If no, continue to Finalize.

---

## Finalize

Display stage banner:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► FINALIZING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

1. Validate: `asp validate asp.yaml`
2. Fix any validation errors
3. Generate baseline universe: `asp universe generate -n baseline`

### Populate CLAUDE.md

Read the existing `CLAUDE.md` (created by `prism init`). Replace the
`## Analysis Details` section at the bottom with project-specific content:

```markdown
## Analysis Details

### Description
<description from asp.yaml>

### Structure

**Top-level** — <what the top-level analysis covers>
- Decisions: <list of decision IDs with labels>
- Outputs: <list of output IDs>

**<sub_analysis_name>** — <sub-analysis description>
- Decisions: <list of decision IDs with labels>
- Outputs: <list of output IDs>

(Repeat for each sub-analysis, if any)

### Key Decisions
<For each decision the user discussed, briefly note what it controls and the default. Mark decisions the agent inferred that still need user confirmation.>

### Implementation Notes
<Any domain-specific guidance that came up during the conversation —
libraries mentioned, data format notes, known gotchas, etc.>
```

This section is what makes CLAUDE.md useful for building — it gives Claude Code
the context to implement without re-reading the entire conversation.

### Summary

Present a brief summary:

```
| Section       | Decisions | Outputs | Status |
|---------------|-----------|---------|--------|
| (top-level)   | 3         | 2       | ✓      |
| sub_analysis  | ...       | ...     | ...    |
```

- Description
- Key decisions (noting which the user discussed vs which were agent-inferred)

Then:

> "Anything you'd like to change? Otherwise the specification is ready."

If edits requested, apply, re-validate, and update CLAUDE.md.

---

## Done

When ready to proceed:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► SPECIFICATION COMPLETE ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

List sections and their status:

```
| Section       | Decisions | Outputs |
|---------------|-----------|---------|
| (top-level)   | 3         | 2       |
| sub_analysis  | ...       | ...     |
```

Then the Next Up block:

```
───────────────────────────────────────────────────────────────

▶ Next Up

Start building — write scripts, run them directly, iterate.
Write them recipe-ready (parameterized, results to convention paths).
See CLAUDE.md for conventions.

When scripts work, integrate:
- Add recipe: blocks to outputs in asp.yaml
- Check progress: prism status
- Execute via Dagster: /prism-run

Every decision becomes a parameter — no hardcoded values.
New decisions can be added later.

<sub>/clear first → CLAUDE.md has everything needed to pick back up</sub>

───────────────────────────────────────────────────────────────

Also available:
- `/prism-insights` — add literature support to decisions
- `/prism-status` — check output and integration status

───────────────────────────────────────────────────────────────
```

---

---

## Restrictions

**You are a specification agent, not an implementation agent.**

You MUST NOT write Python, R, or other implementation code.

You MUST ONLY create/modify:
- `asp.yaml`
- `universes/*.yaml`
- `CLAUDE.md` (during Finalize step only)

---

## Anti-patterns

- **Waiting to write** — Update asp.yaml after each phase so the user sees progress
- **Checklist walking** — Don't ask every question regardless of context
- **Over-nesting** — A single flat analysis is fine for simple analyses; don't force sub-analyses
- **Accepting vague goals** — "Analyze this data" is not a research question
- **Implementation questions** — "What preprocessing?" belongs in the build phase, not here
- **Writing insights directly** — Always defer to `/prism-insights` for evidence extraction
