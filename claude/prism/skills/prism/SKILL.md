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
| `/prism-new` | Create a new analysis — scope question, structure decisions, identify sub-analyses with literature |
| `/prism-verify` | Verify a completed analysis — check results, decision-code alignment, success criteria |

### Workflow

```
/prism-new  →  write & debug  →  integrate recipes  →  prism run
```

`/prism-new` scopes the research question, structures decisions (and sub-analyses if needed), identifies decision points, and proactively searches for supporting literature. Then start building progressively. Execute with `prism run` (reads default target from `prism.yaml`).

## Development Workflow

### Phase 1: Write & Debug
Write scripts and run them directly (`python scripts/compute.py`). Iterate until they work. But write them **recipe-ready** from the start:
- Parameterize all decisions (accept as CLI args, never hardcode)
- Write results to convention paths (`results/<universe_id>/<output_id>.<ext>`)
- One script per output

### Phase 2: Integrate
When a script works, add a `recipe:` block to its output in `asp.yaml`. Check integration progress with `prism status` — it shows which outputs have recipes and which don't.

### Phase 3: Materialize
Run `prism run` to execute via Dagster. Phases can overlap — some outputs may be materialized while others are still being debugged. Use `prism status` to track progress across all three states.

## Analysis Structure

An ASP analysis (`asp.yaml`) is a **self-similar** specification. Every level has the same structure: metadata, inputs, outputs, decisions, insights, and optional sub-analyses. Top-level fields are:

- `name`, `description`, `version`, `authors`, `tags`
- `inputs`: data sources
- `outputs`: expected outputs (metrics, figures, tables, data, reports)
- `decisions`: analysis choice points (methods, parameters, data choices)
- `insights`: scientific knowledge from papers or prior analyses
- `analyses`: optional sub-analyses (self-similar nesting)
- `container`: default container image for recipes — either a pre-built image string (e.g., `"python:3.12-slim"`) or a build spec (`{build: Containerfile}`)

A simple analysis puts everything at the top level. Complex analyses use `analyses:` for multi-stage pipelines where each sub-analysis has its own inputs, outputs, and decisions.

### Simple analysis (decisions at top level)

```yaml
decisions:
  scaling:
    label: "Feature Scaling"
    tags: [method]
    default: standard
    options:
      standard:
        label: "StandardScaler"
      minmax:
        label: "MinMaxScaler"
```

### Multi-stage analysis (using sub-analyses)

```yaml
# Top-level decisions shared across stages
decisions:
  cosmology_model:
    label: "Cosmological Model"
    tags: [method]
    default: flat_lcdm
    options:
      flat_lcdm:
        label: "Flat LCDM"
      wcdm:
        label: "wCDM"

# Sub-analyses for pipeline stages
analyses:
  build_mocks:
    description: "Generate realistic mock catalogs matching survey properties."
    inputs:
      - id: survey_data
        type: data
        from: survey_catalog
    outputs:
      - id: mock_catalog
        type: data
        recipe:
          command: python src/generate_mocks.py
    decisions:
      noise_model:
        label: "Noise Model"
        tags: [method]
        default: heteroscedastic
        options:
          homoscedastic:
            label: "Homoscedastic"
          heteroscedastic:
            label: "Heteroscedastic"

  train_network:
    description: "Train SBI neural network on mock catalog."
    inputs:
      - id: training_data
        type: data
        from: build_mocks.mock_catalog
    outputs:
      - id: trained_model
        type: data
        recipe:
          command: python src/train.py
          resources:
            gpus: 1
            memory: "32GB"
    decisions:
      architecture:
        label: "Network Architecture"
        tags: [method]
        default: maf
        options:
          maf:
            label: "Masked Autoregressive Flow"
          npe:
            label: "Neural Posterior Estimation"
```

Sub-analyses can have: `description`, `success_criteria`, `inputs`, `outputs`, `decisions`, `insights`, and their own nested `analyses`. Sub-analysis inputs can reference parent inputs (`from: input_id`) or sibling outputs (`from: sibling_id.output_id`).

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
prism build                       # Build container images from specs
prism build --force               # Rebuild all images
prism run                         # Execute recipes via Dagster (auto-builds)
prism run --no-build              # Execute without building containers
prism run accuracy --universe baseline  # Run specific output
prism status                      # Show materialization + container status
prism dev                         # Launch Dagster webserver UI
prism remote setup perlmutter     # Configure execution target
```

### Writing Results

Results use a convention-based layout — file names are `<id>.<ext>` derived from the output `id` and its format.

**Outputs** go to `results/<universe_id>/<output_id>.<ext>`

```yaml
# asp.yaml — no path field needed
outputs:
  - id: accuracy
    type: metric             # → results/<universe_id>/accuracy.json
  - id: corner_plot
    type: figure             # → results/<universe_id>/corner_plot.png
```

For metrics, write a JSON file with the value: `{"value": 0.95}`

### Execution

Outputs with inline `recipe:` blocks can be executed via Dagster:

```yaml
outputs:
  - id: accuracy
    type: metric
    recipe:
      command: python scripts/evaluate.py
      inputs: [trained_model]
      container: ghcr.io/proj/ml:latest
      resources: { cpus: 4 }
```

Recipe fields: `command` (required), `inputs` (optional), `container` (optional), `resources` (optional).

The `container` field can be a pre-built image string or a build spec:

```yaml
# Pre-built image
container: "python:3.12-slim"

# Build from Containerfile (content-addressed, auto-cached)
container:
  build: Containerfile
```

When using a build spec at the analysis level, all recipes inherit it. Per-recipe `container:` overrides the default.

```bash
prism build                  # build container images from specs
prism run                    # materialize all outputs (auto-builds)
prism run accuracy           # materialize specific output
prism run --no-build         # skip auto-building containers
prism status                 # check materialization + container status
prism dev                    # Dagster webserver UI
```

## Core Concepts

### Success Criteria
Define concrete, verifiable conditions for success:
```yaml
description: |
  Build a classifier for the Iris dataset...
success_criteria:
  - "Achieve >95% classification accuracy on held-out test set"
  - "Model size under 10MB for mobile deployment"
  - "Prediction time under 100ms per sample"
```

### Universes
A universe is a complete set of decisions — one option per decision point. For simple analyses, decisions are at the top level. For analyses with sub-analyses, decisions are nested under `analyses:`:

Simple universe:
```yaml
id: baseline
decisions:
  scaling: standard
  model: random_forest
```

Nested universe (with sub-analyses):
```yaml
id: baseline
decisions:
  cosmology_model: flat_lcdm
analyses:
  build_mocks:
    decisions:
      noise_model: heteroscedastic
  train_network:
    decisions:
      architecture: maf
```

### Inputs
Inputs define the data sources for an analysis:
- **id**: Unique identifier
- **type**: `data` or `analysis`
- **source**: Where to get the data (file path or URL)
- **from**: Reference a parent input or sibling output (sub-analyses only)

```yaml
inputs:
  - id: training_data
    type: data
    source: "data/train.csv"           # Local file path

  - id: reference_study
    type: analysis
    ref: "analyses/reference"          # Another ASP analysis
```

## Universe Lifecycle

Decisions emerge during analysis — you don't know all of them upfront. When you run baseline and realize "I should try X," that's a new decision (or a new option on an existing decision).

### Adding a new decision after baseline

1. **Identify the scope**: New option on an existing decision, or an entirely new decision?
   - New option: add it to the existing decision in `asp.yaml`
   - New decision: add a new decision entry under `decisions:` (at the top level or within the relevant sub-analysis)

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
3. Define decisions (and sub-analyses if the pipeline has distinct stages)

Then start building — Claude Code reads `CLAUDE.md` + `asp.yaml` and implements naturally.

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
For each insight relevant to the analysis, use W3C-compliant selectors for evidence:

```yaml
insights:
  insight_id:  # lowercase_with_underscores
    id: insight_id
    claim: "One sentence stating what we learned"
    created_at: "2025-01-15T10:30:00"
    evidence:
      - id: e1
        doi: "10.1234/paper-doi"
        # For quotes (W3C TextQuoteSelector):
        quote:
          type: TextQuoteSelector
          exact: "Exact text from the paper"
          prefix: "text before for disambiguation"
          suffix: "text after for disambiguation"
        location:
          type: FragmentSelector
          page: 5
      # For figures (FigureSelector):
      - id: e2
        doi: "10.1234/paper-doi"
        figure:
          type: FigureSelector
          label: "Figure 3a"
          caption: "Description of what it shows"
      # For tables (TableSelector):
      - id: e3
        doi: "10.1234/paper-doi"
        table:
          type: TableSelector
          label: "Table 1"
          region: "row 3, accuracy column"
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
        insights:
          - insight_id  # Reference the insight
```

### Step 5: Validate
```bash
asp validate asp.yaml
```

## Insight Types by Source

### From Papers (doi)
Use W3C-compliant selectors as evidence:
- `quote`: TextQuoteSelector with `exact`, optional `prefix`/`suffix`
- `figure`: FigureSelector with `label`, optional `caption`
- `table`: TableSelector with `label`, optional `region`
- `location`: FragmentSelector with `page` number

### From Analysis Artifacts (artifact)
Reference an output by its ID:

```yaml
insights:
  prior_finding:
    id: prior_finding
    claim: "StandardScaler outperforms MinMaxScaler on this dataset"
    created_at: "2025-01-15T10:30:00"
    evidence:
      - id: e1
        artifact: "accuracy"
        quote:
          exact: "StandardScaler achieved 97% accuracy vs 91% for MinMaxScaler"
        checksum:
          algorithm: sha256
          value: "abc123..."
```

## Validation Checklist

Before finalizing an analysis, verify:

1. **Schema compliance**: `asp validate asp.yaml`
2. **All decisions have defaults**: Required for universe generation
3. **Insights have valid DOIs**: Pattern `10.XXXX/...`
4. **Evidence references exist**: Insights referenced in options must be defined
5. **Constraint references valid**: `incompatible_with` and `requires` point to real options

## Common Patterns

### Adding a New Decision
Decisions live under `decisions:` at the top level (or within a sub-analysis under `analyses:`):
```yaml
decisions:
  new_decision:
    label: "Human-readable Label"
    tags: [method]  # optional: freeform tags for grouping (e.g., method, data, parameter)
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
inputs:
  - id: smith2023
    type: data
    description: "Smith et al. 2023 - Methodology paper"
    source: "https://doi.org/10.1234/smith2023"
```

### Creating a New Universe

```bash
asp universe generate -n experiment1 -d "Testing hypothesis X"
```

Then edit `universes/experiment1.yaml` to customize decisions. If this requires a new decision or option that doesn't exist yet, see **Universe Lifecycle** above — add it to `asp.yaml` first and update all existing universe files with the default.

## File Locations

```
my-analysis/
├── asp.yaml              # Full spec with decisions and optional sub-analyses
├── CLAUDE.md             # Build conventions and project context
├── universes/
│   └── baseline.yaml     # Decision selections (mirrors analysis tree)
├── scripts/              # Implementation scripts
├── results/              # Execution outputs (gitignored)
└── .claude/
    ├── settings.json     # Permissions and hooks
    ├── scripts/          # Hook scripts
    └── skills/           # Prism skills
```

## Tips

1. **Start with the description**: Write a clear description before defining decisions
2. **One insight per finding**: Don't combine multiple findings in one insight
3. **Precise evidence**: Use W3C selectors — include exact quotes, figure labels, page numbers
4. **Link insights to decisions**: Every decision option should ideally have supporting evidence via `insights:`
5. **Use scope**: Clarify when an insight applies (dataset, model type, conditions)
6. **Self-similar nesting**: For multi-stage pipelines, use `analyses:` to decompose into sub-analyses — each is a valid analysis on its own
