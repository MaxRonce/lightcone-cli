# CLAUDE.md

## Project: {{name}}

ASP (Agentic Science Protocol) analysis project, built with Prism. Start with `/prism-new` to scope a research question.

**Skills:** `/prism-new` (scope + literature), `/prism-verify` (verify).

### Source of Truth

- `asp.yaml` -- The analysis specification. Read this first.
- `universes/` -- Decision selections (one YAML per universe).

### Project Layout

```
asp.yaml              # Specification: decisions, inputs, outputs
prism.yaml            # Prism config (default target, etc.)
CLAUDE.md             # This file
Containerfile         # Container image for execution
requirements.txt      # Python deps (keep in sync with scripts)
universes/
  baseline.yaml       # Default decision selections
scripts/              # Implementation scripts
results/<universe>/   # Outputs by universe (produced by prism run)
```

### Development Workflow

Three overlapping phases:

1. **Write & Debug** -- Run scripts directly (`python scripts/compute.py`) to iterate. Write them recipe-ready from the start: parameterize decisions, write to convention paths, one script per output.
2. **Integrate** -- Add `recipe:` blocks to outputs in `asp.yaml`. Track with `prism status` (`no recipe` / `pending` / `ok`).
3. **Materialize** -- `prism run` executes via Dagster in containers. Done when `prism status` shows all `ok`.

**An output is not done until `prism run` produces it.** Running scripts directly is for debugging only — final results must always come from `prism run` so they are reproducible inside containers.

### Spec-Code Invariant

**`asp.yaml` must always reflect the code and vice versa.** When you change one, update the other immediately:
- Add a decision to code? Add it to `asp.yaml` and all universe files.
- Add an output or change a script? Update the `recipe:` block in `asp.yaml`.
- Remove or rename something? Update both sides and run `asp validate asp.yaml`.

### asp.yaml Structure

The spec is **self-similar** -- every level (top or sub-analysis) has the same fields: `name`, `description`, `version`, `authors`, `tags`, `inputs`, `outputs`, `decisions`, `insights`, `analyses`, `container`, `success_criteria`.

```yaml
# Simple analysis -- everything at top level
version: "1.0"
name: "My Analysis"
description: "What this analysis investigates."
success_criteria:
  - "Achieve >95% accuracy on held-out test set"
inputs:
  - id: training_data
    type: data
    source: "data/train.csv"
decisions:
  scaling:
    label: "Feature Scaling"
    type: method                 # method | data | parameter
    rationale: "Affects convergence"
    default: standard
    options:
      standard: { label: "StandardScaler" }
      minmax: { label: "MinMaxScaler" }
outputs:
  - id: accuracy
    type: metric
    recipe:
      command: python scripts/evaluate.py
container:
  build: Containerfile
```

```yaml
# Multi-stage -- sub-analyses with cross-references
decisions:
  cosmology_model:               # Shared across stages
    label: "Cosmological Model"
    type: method
    default: flat_lcdm
    options:
      flat_lcdm: { label: "Flat LCDM" }
      wcdm: { label: "wCDM" }
analyses:
  build_mocks:
    inputs:
      - { id: survey_data, type: data, from: survey_catalog }   # Parent input
    outputs:
      - id: mock_catalog
        type: data
        recipe: { command: python src/generate_mocks.py }
    decisions:
      noise_model:
        label: "Noise Model"
        type: method
        default: heteroscedastic
        options:
          homoscedastic: { label: "Homoscedastic" }
          heteroscedastic: { label: "Heteroscedastic" }
  train_network:
    inputs:
      - { id: training_data, type: data, from: build_mocks.mock_catalog }  # Sibling output
    outputs:
      - id: trained_model
        type: data
        recipe: { command: python src/train.py, resources: { gpus: 1, memory: "32GB" } }
```

### Decision Parameterization

**Every decision must be parameterized in code** -- never hardcode a decision value. Accept as CLI args regardless of type (`method`, `data`, or `parameter`).

**Underscore convention:** IDs use underscores in `asp.yaml` (`prior_range`). Prism passes `--prior_range wide`. Scripts must match: `parser.add_argument('--prior_range')`, **not** `--prior-range`.

### Writing Results

Convention path: `results/<universe_id>/<output_id>.<ext>` -- no `path` field needed.

- `metric` -- JSON (`{"value": 0.95}`)
- `figure` -- PNG
- `table` -- CSV
- `data` -- Parquet/HDF5
- `report` -- Markdown

### Recipe Format

Inline on outputs. Fields: `command` (required), `inputs`, `container`, `resources`.

```yaml
outputs:
  - id: accuracy
    type: metric
    recipe:
      command: python scripts/evaluate.py
      inputs: [trained_model]               # Dependency on other output
      container: ghcr.io/proj/ml:latest     # Overrides analysis-level default
      resources: { cpus: 4, memory: "32GB", gpus: 1, time_limit: "2h" }
```

Set `container:` at analysis level (all recipes inherit); per-recipe `container:` overrides. Accepts a build spec (`{ build: Containerfile }`) or image string (`"python:3.12-slim"`).

### CLI Reference

```bash
# asp -- spec operations
asp validate asp.yaml                       # Validate (run after every change)
asp validate asp.yaml --verify-evidence     # + verify insight quotes against PDFs
asp info [--decisions]                      # Analysis summary / decision details
asp universe generate -n NAME [-d "desc"]   # Generate universe from defaults
asp universe check universes/x.yaml         # Check universe constraints
asp viz                                     # Visualize decision space
asp schema show analysis                    # Show JSON schema

# prism -- execution operations
prism build [--force]                       # Build container images
prism run [OUTPUT] [--universe NAME]        # Execute recipes via Dagster (auto-builds)
prism run --no-build                        # Execute without building containers
prism status [--universe NAME]              # Materialization + container status
prism dev                                   # Dagster webserver UI
prism remote setup NAME                     # Configure HPC execution target
```

### Universe Management

A universe selects one option per decision -- a defensible alternative analysis path. Bug fixes and refactors are normal commits, not universes.

```bash
asp universe generate -n experiment1 -d "Testing hypothesis X"
# Edit universes/experiment1.yaml, then: prism run --universe experiment1
```

**Adding a new decision:** (1) add to `asp.yaml` with options/default/rationale, (2) add parameter to code, (3) add to all existing universe files with default, (4) create new universe, (5) `asp validate asp.yaml`.

### Status Interpretation

`prism status` shows outputs vs universes. **Progression:** `no recipe` --> `pending` --> `ok`

- `ok` -- Recipe exists, results on disk. Done.
- `pending` -- Recipe exists, not materialized. Run `prism run`.
- `no recipe` -- No `recipe:` block yet. Still in Write & Debug phase.

Container status: `prebuilt: image`, `build: Containerfile (built)`, or `(not built)` (needs `prism build`).

### Insights Format

Insights link evidence to decisions using W3C selectors:

```yaml
insights:
  layer_norm_stability:
    id: layer_norm_stability
    claim: "Layer normalization improves training stability"
    created_at: "2025-01-15T10:30:00"
    evidence:
      - id: e1
        doi: "10.48550/arXiv.1607.06450"
        quote: { type: TextQuoteSelector, exact: "Exact text", prefix: "~20-100 chars before", suffix: "~20-100 chars after" }
        location: { type: FragmentSelector, page: 5 }
      - id: e2
        doi: "10.48550/arXiv.1607.06450"
        figure: { type: FigureSelector, label: "Figure 3a", caption: "..." }
      - id: e3
        doi: "10.48550/arXiv.1607.06450"
        table: { type: TableSelector, label: "Table 1", region: "row 3, col 2" }
    scope: "Context where this applies (optional)"
```

Link to decisions: `options: { layer_norm: { insights: [layer_norm_stability] } }`

Literature is integrated into `/prism-new` during scoping.

### Failure Diagnosis

- **Script arg not recognized** -- Use underscores in argparse to match decision IDs
- **Container not built** -- `prism build` or remove `--no-build`
- **Recipe input not found** -- Materialize upstream outputs first
- **Dagster not installed** -- `pip install prism[dagster]`

After failure: fix, then `prism run <output_id> --universe <name>`.

### Validation

Run `asp validate asp.yaml` after **every** spec change. Additional checks:
- Universe files: `asp universe check universes/<name>.yaml`
- Evidence quotes: `asp validate asp.yaml --verify-evidence`

---

<!-- AUTOGENERATED: /prism-new populates below during specification -->
## Analysis Details

_Run `/prism-new` to scope the research question and populate this section._
