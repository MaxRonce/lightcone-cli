---
name: prism
description: Work with ASP (Agentic Science Protocol) analyses via Prism. ALWAYS use this skill when working in a project with asp.yaml. Use for creating analyses, editing specifications, validating, managing universes, extracting insights from papers, or building implementations. Triggers on asp.yaml, universes/, decisions, insights, or any ASP-related work.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(python:*)
---

# Prism Analysis Skill

Help users work with the Agentic Science Protocol (ASP) via Prism — a declarative specification format for scientific analyses.

## Agent Commands

| Command | Purpose |
|---------|---------|
| `/prism-new` | Create a new analysis — scope question, structure chunks, identify decisions with literature |

### Workflow

```
/prism-new  →  build each chunk with Claude Code  → ...
```

`/prism-new` scopes the research question, structures chunks, identifies decisions, and proactively searches for supporting literature. Then start building — Claude Code reads `CLAUDE.md` + `asp.yaml` and implements each chunk.

## Chunks

Every analysis has `chunks` in `asp.yaml`. All decisions live under chunks — there are no top-level decisions. A simple analysis uses a single `main` chunk. Complex analyses have multiple chunks:

```yaml
chunks:
  main:
    decisions:
      scaling:
        label: "Feature Scaling"
        type: method
        default: standard
        options:
          standard:
            label: "StandardScaler"
          minmax:
            label: "MinMaxScaler"
```

Multi-chunk example:

```yaml
chunks:
  build_mocks:
    problem: "Generate realistic mock catalogs matching survey properties."
    decisions:
      noise_model:
        label: "Noise Model"
        type: method
        default: heteroscedastic
        options:
          homoscedastic:
            label: "Homoscedastic"
          heteroscedastic:
            label: "Heteroscedastic"
    artefacts:
      - id: mock_catalog
        type: data

  train_network:
    problem: "Train SBI neural network on mock catalog."
    decisions:
      architecture:
        label: "Network Architecture"
        type: method
        default: maf
        options:
          maf:
            label: "Masked Autoregressive Flow"
          npe:
            label: "Neural Posterior Estimation"
```

A chunk can have: `problem`, `success_criteria`, `decisions`, and `artefacts` (figures, tables, data, reports produced by the chunk).

The `main` chunk is special — it inherits `problem` and `success_criteria` from the top-level `analysis`, and its outputs are the analysis-level `outputs`. Don't set `problem`, `success_criteria`, or `artefacts` on `main`; they belong on the analysis. Non-main chunks should set their own `problem`, `success_criteria`, and `artefacts` as needed.

## Quick Reference

### CLI Commands
```bash
# ASP CLI — spec operations
asp init <directory>              # Create minimal analysis scaffold
asp validate asp.yaml             # Validate analysis specification
asp validate universes/foo.yaml   # Validate universe
asp info                          # Show analysis summary
asp info --decisions              # Show decision details
asp universe generate -n baseline # Generate universe from defaults
asp universe check universes/x.yaml  # Check universe constraints
asp viz                           # Visualize decision space
asp schema show analysis          # Show JSON schema

# Prism CLI — agent operations
prism init <directory>            # Create full project with Claude Code config
prism remote setup perlmutter     # Configure HPC target
prism canvas                      # Launch visual editor
prism navigator                   # Launch Navigator
```

### Writing Results

Results use a convention-based layout — file names are `<id>.<ext>` derived from the output/artefact `id` and its format.

**Outputs** (analysis-level) → `results/<universe_id>/<output_id>.<ext>`
**Artefacts** (chunk-level) → `results/<universe_id>/<chunk>/<artefact_id>.<ext>`

```yaml
# asp.yaml — no path field needed
outputs:
  - id: accuracy
    type: metric             # → results/<universe_id>/accuracy.json
  - id: corner_plot
    type: figure
    formats: ["png"]         # → results/<universe_id>/corner_plot.png
```

For metrics, write a JSON file with the value: `{"value": 0.95}`

**Chunk note:** All chunks are defined inline in the root `asp.yaml`. No separate directories or files needed for chunk specifications.

## Core Concepts

### Analysis Structure
An ASP analysis (`asp.yaml`) contains:
- **analysis**: name, problem statement, success criteria, inputs, outputs
- **insights**: scientific knowledge from papers or prior analyses
- **chunks**: pipeline stages, each with its own decisions (every analysis has at least one — use `main` for single-stage analyses)

### Success Criteria
Define concrete, verifiable conditions for success:
```yaml
analysis:
  problem: |
    Build a classifier for the Iris dataset...
  success_criteria:
    - "Achieve >95% classification accuracy on held-out test set"
    - "Model size under 10MB for mobile deployment"
    - "Prediction time under 100ms per sample"
```

### Universes
A universe is a complete set of decisions organized by chunk — one option per decision point. Decisions are nested under their chunk:

```yaml
chunks:
  main:
    scaling: standard
    model: random_forest
```

### Inputs
Inputs define the data sources for an analysis:
- **id**: Unique identifier
- **type**: `data`, `analysis`, or `literature`
- **source**: Where to get the data (file path or URL)

```yaml
inputs:
  - id: training_data
    type: data
    source: "data/train.csv"           # Local file path

  - id: remote_data
    type: data
    source:
      type: url
      url: "https://example.com/data.csv"  # Remote URL
```

## Universe Lifecycle

Decisions emerge during analysis — you don't know all of them upfront. When you run baseline and realize "I should try X," that's a new decision (or a new option on an existing decision).

### Adding a new decision after baseline

1. **Identify the scope**: New option on an existing decision, or an entirely new decision?
   - New option → add it to the existing decision in `asp.yaml`
   - New decision → add a new decision entry under the relevant chunk

2. **Add to `asp.yaml`**: Define the decision with all options, a default, and a rationale.

3. **Update existing universes**: Add the new decision to all existing universe files, selecting the default to preserve their behavior.

4. **Create the new universe**: `asp universe generate -n <name>`, then edit to select the new option.

5. **Validate**: `asp validate asp.yaml && asp universe check universes/<name>.yaml`

Results for each universe go to `results/<universe_id>/`.

### What is and isn't a universe

A universe captures a **defensible alternative analysis path** — a choice a reasonable researcher might make differently. These are universes:
- Different hyperparameter selections
- Different data subsets or filtering criteria
- Different algorithmic approaches

These are NOT universes (just normal commits):
- Bug fixes
- Adding a missing output to `asp.yaml`
- Improving plot formatting
- Refactoring code without changing behavior

## Creating a New Analysis

Use `/prism-new` to interactively scope your project:
1. Define the research question
2. Define top-level inputs, outputs, success criteria
3. Define chunks with wiring

Then start building each chunk — Claude Code reads `CLAUDE.md` + `asp.yaml` and implements naturally.

Alternatively, scaffold manually:
```bash
prism init my-analysis
```

## Extracting Insights from Papers

When the user provides a paper (PDF, DOI, or description) to extract insights:

### Step 1: Identify the Paper
Get the DOI. Format: `10.XXXX/...` (e.g., `10.1038/s41586-023-06221-2`)

### Step 2: Read the Current Analysis
Check `asp.yaml` to understand:
- What problem is being solved?
- What decisions need evidence?
- What inputs/outputs are defined?

### Step 3: Extract Relevant Insights
For each insight relevant to the analysis:

```yaml
insights:
  insight_id:  # lowercase_with_underscores
    claim: "One sentence stating what we learned"
    source:
      doi: "10.1234/paper-doi"
    evidence:
      # For figures:
      - figure: "Figure 3a"
        caption: "Description of what it shows"
      # For quotes:
      - quote: "Exact text from the paper"
        location: "Section 2.1, p.5"
      # For tables:
      - table: "Table 1"
        location: "row 3, accuracy column"
        value: "0.92"
      # For equations:
      - equation: "Equation 7"
        expression: "L = (C/C_0)^α"
      # For numerical results:
      - result: "accuracy improvement"
        location: "Section 4.2"
        value: "15%"
    scope: "Context where this applies (optional)"
```

### Step 4: Link to Decisions
Reference insights in decision options:

```yaml
decisions:
  method_choice:
    options:
      method_a:
        label: "Method A"
        evidence:
          - insight: insight_id  # Reference the insight
```

### Step 5: Validate
```bash
asp validate asp.yaml
```

## Insight Types by Source

### From Papers (doi)
Use these evidence types:
- `figure`: Reference to a figure
- `quote`: Direct quote with location
- `table`: Table reference with specific value
- `equation`: Mathematical expression
- `result`: Numerical finding

### From Prior Analyses (analysis)
Use these evidence types:
- `metric`: Named metric with value
- `output`: Reference to output artifact

```yaml
insights:
  prior_finding:
    claim: "StandardScaler outperforms MinMaxScaler on this dataset"
    source:
      analysis: "our-org/preprocessing-study"
      version: "1.2.0"
      universe: "baseline"
    evidence:
      - metric:
          name: "accuracy"
          value: { standard: 0.94, minmax: 0.89 }
      - output: "figures/scaler_comparison.png"
```

## Validation Checklist

Before finalizing an analysis, verify:

1. **Schema compliance**: `asp validate asp.yaml`
2. **All decisions have defaults**: Required for universe generation
3. **Insights have valid DOIs**: Pattern `10.XXXX/...`
4. **Evidence references exist**: Insights referenced in evidence must be defined
5. **Constraint references valid**: `incompatible_with` and `requires` point to real options

## Common Patterns

### Adding a New Decision
Decisions live under `chunks.<chunk_name>.decisions`:
```yaml
chunks:
  main:
    decisions:
      new_decision:
        label: "Human-readable Label"
        type: method  # or: data, parameter
        importance: 3  # 1=critical, 5=minor
        reviewed: true  # Has a human weighed in on this decision?
        rationale: "Why this decision matters"
        default: option_a
        options:
          option_a:
            label: "Option A"
            description: "What this option does"
          option_b:
            label: "Option B"
            description: "Alternative approach"
            incompatible_with: ["other_decision.some_option"]
```

### Adding Literature Input
```yaml
analysis:
  inputs:
    - id: smith2023
      type: literature
      description: "Smith et al. 2023 - Methodology paper"
```

### Creating a New Universe

```bash
asp universe generate -n experiment1 -d "Testing hypothesis X"
```

Then edit `universes/experiment1.yaml` to customize decisions. If this requires a new decision or option that doesn't exist yet, see **Universe Lifecycle** above — add it to `asp.yaml` first and update all existing universe files with the default.

## File Locations

```
my-analysis/
├── asp.yaml              # Full spec with chunks defined inline
├── CLAUDE.md             # Build conventions and project context
├── universes/
│   └── baseline.yaml     # Decision selections organized by chunk
├── scripts/              # Implementation scripts
├── results/              # Execution outputs (gitignored)
└── .claude/
    ├── settings.json     # Permissions and hooks
    ├── scripts/          # Hook scripts
    └── skills/           # Prism skills
```

Chunks are defined inline in `asp.yaml` — no separate directories needed for the specification.

## Tips

1. **Start with the problem**: Write a clear problem statement before defining decisions
2. **One insight per finding**: Don't combine multiple findings in one insight
3. **Precise evidence**: Include page numbers, figure labels, exact quotes
4. **Link insights to decisions**: Every decision option should ideally have supporting evidence
5. **Use scope**: Clarify when an insight applies (dataset, model type, conditions)
