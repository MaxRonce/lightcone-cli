---
name: prism-new
description: Create a new ASP analysis project with integrated literature support. Scope the research question through conversation, structure outputs and decisions, search for and extract evidence from scientific papers, and build a complete asp.yaml specification. Use when starting a new analysis, when the user says "new project", "new analysis", or "scope". Triggers on "new", "scope", "research question", "start analysis".
allowed-tools: Read, Write(asp.yaml), Write(universes/*), Write(CLAUDE.md), Edit(asp.yaml), Edit(universes/*), Edit(CLAUDE.md), Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(mkdir:*), Bash(echo:*), WebSearch, WebFetch, AskUserQuestion, Task
---

# /prism-new

Create a new ASP analysis project through conversation. Build the spec iteratively so the user sees progress in the navigator. Literature search is woven into the conversation -- not a separate phase. When the user describes their approach, proactively search for relevant work to discover what the decision space actually is.

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

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM > RESEARCH QUESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> "What are you trying to learn? Describe the question in your own words."

Then sharpen:
- "What would a clear answer look like?" (becomes success criteria)
- "Why does this matter?" (context for decisions)

**Write to asp.yaml immediately** with `version`, `name`, `description`, `success_criteria`. This gives the user something visible in the navigator right away.

---

## Phase 2: Analysis Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM > ANALYSIS STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> "Walk me through how you'd do this step by step. What happens first? What would you want to check before moving on?"

From this, identify **outputs and their dependencies**:
- Single flat analysis for a straightforward pipeline
- Multiple sub-analyses (via `analyses:`) for clear stages with inspectable intermediate outputs

For multi-stage: map what each stage produces (outputs with recipes), what the next stage consumes (inputs with `from:` references), and where decisions belong. See CLAUDE.md template for YAML structure.

> "Want to fully scope all stages now, or start with [first stage]?"

**Update asp.yaml** with `inputs`, `outputs`, and `analyses` (if multi-stage).

---

## Phase 3: Deep Dive

Repeat this phase for each section being scoped (top-level or sub-analysis).

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM > DEEP DIVE -- [SECTION NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The Deep Dive is ONE integrated conversation where decision identification and literature search happen together. You are simultaneously:
- Talking to the user about their approach
- Searching the web for papers in the background as topic areas emerge
- Spawning subagents to extract from papers
- Using findings to enrich the conversation and surface new decisions

### Conversation Flow

**Ask the user what they are thinking** for this section -- methods, data handling, assumptions. Listen for topic areas where decisions live (e.g., "normalization strategy", "handling missing data", "model architecture").

**As topic areas emerge, search proactively.** Do not wait to be asked. When the user mentions an approach, immediately spawn a background Task subagent (`run_in_background: true`) to WebSearch for recent papers comparing approaches in the user's domain. The conversation continues uninterrupted. Check results via TaskOutput at natural pauses. For quick, lightweight queries, use WebSearch directly.

**When the user mentions specific papers, process them immediately.** Download with `asp paper add <doi>` and spawn an extraction subagent in the background using the template in [literature-extraction.md](./literature-extraction.md). Do not batch -- process while the conversation continues.

**Feed findings back naturally.** As background work completes, weave results into the discussion:

> "I found that Smith et al. 2023 compared three normalization approaches for this type of data -- Layer Norm showed better stability in their experiments. This suggests normalization_method should be a decision with at least those three options. What do you think?"

> "From the papers I've been reading, there seems to be no consensus on the outlier threshold -- some use 2.5 SD, others 3 SD. That looks like a Type E decision. Want to include both?"

**Decisions, options, and evidence land in asp.yaml together.** When a decision crystallizes from the conversation (whether from user input, literature, or both), write it with its options, rationale, AND any insight references -- all in one pass.

### Confirm Before Deep Extraction

As background searches accumulate paper candidates, confirm with the user before committing to full extraction:

> "I've found these papers relevant to the normalization and regularization decisions:
> 1. Ba et al. 2016 -- Layer Normalization (you mentioned this)
> 2. Ioffe & Szegedy 2015 -- Batch Normalization
> 3. Wu & He 2018 -- Group Normalization
>
> I'll extract insights from them while we continue scoping. Proceed, or adjust?"

This is about confirming WHICH papers to process deeply, not WHETHER to search at all.

For each confirmed paper: download (`asp paper add <doi>`, `asp paper path <doi>`), then spawn an extraction subagent using the template in [literature-extraction.md](./literature-extraction.md). One paper per subagent. Multiple papers in parallel.

### Decision Identification

As the conversation proceeds and literature arrives, identify decisions using the techniques in [decision-guide.md](./decision-guide.md):

- **From the user's description:** "What could be done differently that would still be defensible?"
- **From literature:** Papers comparing approaches reveal decision points. "Following standard practice, we used..." is a signal -- convention is not always justified.
- **From user uncertainty signals:** "I'm not sure whether to..." / "It depends on..." / "I've seen people do it both ways"
- **From the domain:** Use the domain checklist in the decision guide.

Classify each decision as Type E, N, or U (see decision guide). Write to asp.yaml incrementally.

### Probe for Blind Spots

Analysts systematically neglect data handling decisions while over-focusing on method choices. After the initial conversation settles, probe for 1-3 overlooked areas:

- **Data exclusion/missing data**: outlier criteria, imputation strategy
- **Variable operationalization**: alternative ways to measure or define key variables
- **Inference criteria**: thresholds, evidence standards, evaluation metrics and baselines

These probes may trigger additional background searches.

### Decision Review Tracking

When the user explicitly weighs in on a decision, note it in `CLAUDE.md` (Key Decisions section). Decisions inferred from literature or filled with defaults should be marked for confirmation during Finalize.

### When the Section is Complete

Before moving on, ensure all background subagents for this section have completed. Report:

> "For [section]: [N] decisions identified, [M] with literature support from [P] papers. Moving on to [next section]."

---

## Checkpoint

> "Anything else that should inform this analysis?"

Review the spec with the user. Update asp.yaml with any additions. Check that any remaining background tasks have completed.

---

## Finalize

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM > FINALIZING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

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
- **Implementation Notes**: domain-specific guidance from the conversation (libraries, data formats, gotchas)

### Review with User

> "Anything you'd like to change? Otherwise the specification is ready."

If edits requested, apply, re-validate, and update CLAUDE.md.

---

## Done

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM > SPECIFICATION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Show summary table:

```
| Section       | Decisions | Outputs | Insights |
|---------------|-----------|---------|----------|
| (top-level)   | 3         | 2       | 5        |
| sub_analysis  | ...       | ...     | ...      |
```

Then:

```
---------------------------------------------------------------

> Next Up

Start building -- write scripts, run them directly, iterate.
Write them recipe-ready (parameterized, results to convention paths).
See CLAUDE.md for conventions.

When scripts work, integrate:
- Add recipe: blocks to outputs in asp.yaml
- Check progress: prism status
- Execute: prism run

Every decision becomes a parameter -- no hardcoded values.

<sub>/clear first -- CLAUDE.md has everything needed to pick back up</sub>

---------------------------------------------------------------

Also available:
- `/prism-verify` -- verify results, decision-code alignment, success criteria

---------------------------------------------------------------
```

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
- **Literature as afterthought** -- Do not identify all decisions first and then search. Literature shapes the decision space; search as topics emerge
- **Too many papers** -- 3-5 papers per topic area is sufficient; do not try to be exhaustive
- **Reading PDFs in main context** -- Always delegate to subagents; PDFs consume too much context
- **Skipping verification** -- If quotes were extracted, always run `asp validate --verify-evidence`
