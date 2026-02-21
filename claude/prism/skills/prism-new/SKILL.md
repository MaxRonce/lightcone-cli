---
name: prism-new
description: Create a new ASP analysis project - scope research question, structure chunks, identify decisions with literature support
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
analysis:
  name: "<analysis name>"
  problem: |
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

From this, identify **chunks**:
- Single `main` chunk if it's a straightforward analysis
- Multiple chunks if there are clear stages with inspectable outputs

For multi-chunk analyses, map:
- What does each chunk produce? (artefacts)
- What does the next chunk consume?
- What decisions belong where?

Then ask:

> "Want to fully scope all chunks now, or start with [first chunk]?"

**Update asp.yaml** with chunk structure:
```yaml
analysis:
  inputs:
    - id: <input_id>
      type: data
      source: "<path or URL>"
  outputs:
    - id: <output_id>
      type: <figure|table|data|report>

chunks:
  first_chunk:
    problem: "What this chunk accomplishes"
    artefacts:
      - id: intermediate_output
        type: data

  second_chunk:
    problem: "What this chunk accomplishes"
    # decisions TBD
```

---

## Phase 3: Deep Dive

Display stage banner (repeat for each chunk being scoped):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► DEEP DIVE — [CHUNK NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For each chunk being scoped, explore:

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

### Tracking Reviewed Decisions

When the user explicitly weighs in on a decision, mark it `reviewed: true` in the spec. Decisions you infer or fill with defaults stay unreviewed.

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

### Problem
<problem statement from asp.yaml>

### Chunks

**<chunk_name>** — <chunk problem>
- Decisions: <list of decision IDs with labels>
- Artefacts: <list of artefact IDs if any>

(Repeat for each chunk)

### Key Decisions
<For each reviewed decision, briefly note what it controls and the default>

### Implementation Notes
<Any domain-specific guidance that came up during the conversation —
libraries mentioned, data format notes, known gotchas, etc.>
```

This section is what makes CLAUDE.md useful for building — it gives Claude Code
the context to implement without re-reading the entire conversation.

### Summary

Present a brief summary:

```
| Chunk | Decisions | Artefacts | Status |
|-------|-----------|-----------|--------|
| main  | 3         | 2         | ✓      |
| ...   | ...       | ...       | ...    |
```

- Problem statement
- Key decisions (noting which are ✓ reviewed vs ○ unreviewed)

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

List chunks and their status:

```
| Chunk | Decisions | Reviewed | Artefacts |
|-------|-----------|----------|-----------|
| main  | 3         | 2/3      | 2         |
```

Then the Next Up block:

```
───────────────────────────────────────────────────────────────

▶ Next Up

Start building — ask me to implement a chunk
(e.g. "implement the main chunk")

After implementation, run with `/prism-run`

Every decision becomes a parameter — no hardcoded values.
New decisions can be added later.
See CLAUDE.md for details.

<sub>/clear first → CLAUDE.md has everything needed to pick back up</sub>

───────────────────────────────────────────────────────────────

Also available:
- `/prism-insights` — add literature support to decisions
- `/prism-run` — execute recipes and materialize outputs

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
- **Over-chunking** — Single chunk is fine for simple analyses
- **Accepting vague goals** — "Analyze this data" is not a research question
- **Implementation questions** — "What preprocessing?" belongs in the build phase, not here
- **Writing insights directly** — Always defer to `/prism-insights` for evidence extraction
