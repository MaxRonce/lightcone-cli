---
name: prism-new
description: Create a new ASP analysis project with integrated literature support. Scope the research question through conversation, structure outputs and decisions, search for and extract evidence from scientific papers, and build a complete asp.yaml specification. Use when starting a new analysis, when the user says "new project", "new analysis", or "scope". Triggers on "new", "scope", "research question", "start analysis".
allowed-tools: Read, Write(asp.yaml), Write(universes/*), Write(CLAUDE.md), Edit(asp.yaml), Edit(universes/*), Edit(CLAUDE.md), Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(mkdir:*), Bash(echo:*), WebSearch, WebFetch, AskUserQuestion, Task
---

# /prism-new

Create a new ASP analysis project through conversation. Build the spec iteratively so the user sees progress in the navigator. Literature search and decision identification happen in distinct phases -- talk first, then extract papers, then identify decisions informed by both conversation and literature.

## References

- [Prism Reference](./../prism/SKILL.md) -- core concepts, CLI, validation
- [Decision Guide](./decision-guide.md) -- decision identification, E/N/U classification, blind-spot checklist
- [Literature Extraction](./literature-extraction.md) -- subagent prompt template for paper processing
- [UI Brand](./../ui-brand.md) -- visual formatting patterns
- [CLAUDE.md Template](./../../templates/CLAUDE.md) -- asp.yaml structure, insights format, CLI

## Setup

1. Read `asp.yaml` if it exists (to understand context or avoid overwriting)
2. Note the analysis directory for later

---

## Phase 1: Research Question

Stage banner: RESEARCH QUESTION

> "What are you trying to learn? Describe the question in your own words."

Then sharpen:
- "What would a clear answer look like?" (becomes success criteria)
- "Why does this matter?" (context for decisions)

**Write to asp.yaml immediately** with `version`, `name`, `description`, `success_criteria`. This gives the user something visible in the navigator right away.

---

## Phase 2: Analysis Structure

Stage banner: ANALYSIS STRUCTURE

> "Walk me through your analysis step by step. What goes in, what comes out at the end?"

From this, identify **inputs and outputs**. If the workflow has stages that genuinely need to be independent, use AskUserQuestion to confirm whether to split into sub-analyses. Otherwise, structure as a single flat analysis.

For multi-stage: confirm stage boundaries, map each stage's inputs/outputs and `from:` cross-references. See CLAUDE.md template for YAML structure.

**Update asp.yaml** with `inputs` and `outputs` (extending the spec from Phase 1).

---

## Phase 3: Deep Dive

Stage banner: DEEP DIVE -- [SECTION NAME]

Ask the user if they want to do a literature deep dive for this section. If not, skip straight to decision identification.

### Paper Collection

Ask if the user has specific papers they want to look into. Also search with WebSearch for highly relevant papers -- keep it limited, only papers that directly bear on the analysis. Use AskUserQuestion to present the list with a one-line description of each paper and why it's relevant. The user can check off which ones to extract and add any others.

### Extraction

For each approved paper: `asp paper add <doi>`, `asp paper path <doi>`, then spawn one Task subagent per paper using [literature-extraction.md](./literature-extraction.md). Spawn all in a single message (parallel). Show progress as results come in:

```
  ✓ Ba et al. 2016 -- 3 insights
  ○ Wu & He 2018 (reading...)
```

Write extracted insights to asp.yaml immediately. Synthesize findings by topic for the user.

### Decision Identification

Use the conversation and literature to identify decisions. Apply [decision-guide.md](./decision-guide.md):

- What could be done differently and still be defensible?
- Where did papers disagree or compare alternatives?
- Where did the user express uncertainty?

Present candidate decisions as a batch for the user to review. Classify each as Type E, N, or U. Write confirmed decisions to asp.yaml with options, rationale, and insight references.

**Probe for blind spots** -- analysts over-focus on methods and neglect data handling. Probe 1-3 areas: data exclusion, variable operationalization, inference criteria.

### Decision Review

Every decision is **Confirmed** (user weighed in) or **Inferred** (marked `[UNCONFIRMED]`). Track both in the Key Decisions section of `CLAUDE.md`.

---

## Checkpoint

> "Anything else that should inform this analysis?"

Review the spec with the user. Update asp.yaml with any additions.

---

## Finalize

Stage banner: FINALIZING

### Validate

1. `asp validate asp.yaml` -- fix errors, iterate until clean
2. If insights exist: `asp validate asp.yaml --verify-evidence`

### Generate Baseline Universe

```bash
asp universe generate -n baseline
```

### Populate CLAUDE.md

Read the existing `CLAUDE.md` (created by `prism init`). Replace the `## Analysis Details` section with project-specific content:

- **Description**: from asp.yaml
- **Structure**: for each section (top-level and sub-analyses), list decision IDs with labels and output IDs
- **Key Decisions**: what each controls and its default. Mark agent-inferred decisions with [UNCONFIRMED]
- **Literature Support**: N insights from P papers, DOIs, which decisions they inform (or "No literature added during scoping")
- **Domain Context**: important things the user explained during scoping -- data characteristics, constraints, why certain approaches were preferred. This is context that would be lost after `/clear`.
- **Implementation Notes**: domain-specific guidance from the conversation (libraries, data formats, gotchas)

### Review with User

> "Anything you'd like to change? Otherwise the specification is ready."

If edits requested, apply, re-validate, and update CLAUDE.md.

---

## Done

Stage banner: SPECIFICATION COMPLETE

Show summary table:

```
| Section       | Decisions | Outputs | Insights |
|---------------|-----------|---------|----------|
| (top-level)   | 3         | 2       | 5        |
| sub_analysis  | ...       | ...     | ...      |
```

Then show a Next Up block (see ui-brand.md) with:

- Run `/clear` to free up context, then start building
- Write scripts recipe-ready (parameterized, results to convention paths). See CLAUDE.md for conventions
- When scripts work, integrate: add `recipe:` blocks to outputs, `prism status`, `prism run`
- Every decision becomes a parameter -- no hardcoded values
- Also available: `/prism-verify`

Prompt the user to `/clear` before starting implementation. The scoping conversation consumes significant context. Everything needed to continue is captured in `asp.yaml` and `CLAUDE.md`.

---

## Restrictions

**You are a specification agent, not an implementation agent.**

You MUST NOT write Python, R, or other implementation code.

You MUST ONLY create/modify: `asp.yaml`, `universes/*.yaml`, `CLAUDE.md` (Finalize only).

You MUST NOT fabricate quotes -- all evidence must pass `asp validate --verify-evidence`.

You MUST spawn subagents (via Task) for paper processing. One paper per subagent. Never read a PDF in the main agent context.

---

## Anti-Patterns

- **Waiting to write** -- Update asp.yaml after each decision crystallizes, not in bulk at the end
- **Accepting vague goals** -- "Analyze this data" is not a research question; push back
- **Method-only decisions** -- Actively probe for data handling and exclusion criteria, not just method choices
- **Literature as afterthought** -- Do not defer all literature to the end. Collect papers during conversation (Mode 1) and extract before identifying decisions (Mode 2 before Mode 3)
- **Too many papers** -- ~2 papers per topic area, max 10 per section; do not try to be exhaustive
- **Background interruptions** -- Never spawn search or extraction subagents during conversation. Collect candidates in Mode 1, process them in Mode 2
- **Reading PDFs in main context** -- Always delegate to subagents; PDFs consume too much context
- **Skipping verification** -- If quotes were extracted, always run `asp validate --verify-evidence`
