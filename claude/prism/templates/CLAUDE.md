# CLAUDE.md

## Project: {{name}}

ASP (Agentic Science Protocol) analysis project, built with Prism.

### Skill Commands

| Command | Purpose |
|---------|---------|
| `/prism-new` | Scope question, structure decisions, integrate literature |
| `/prism-build` | Build loop -- spec to materialized results |
| `/prism-verify` | Verify results, decision-code alignment, success criteria |

**Workflow:** `/prism-new` --> `/prism-build` --> `/prism-verify`

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
  - claim: "Achieve >95% accuracy on held-out test set"
    output: accuracy
    condition: "value > 0.95"
inputs:
  - id: training_data
    type: data
    source: "data/train.csv"
decisions:
  scaling:
    label: "Feature Scaling"
    tags: [preprocessing]        # optional freeform tags for grouping
    rationale: "Affects convergence"
    default: standard
    options:
      standard: { label: "StandardScaler" }
      minmax: { label: "MinMaxScaler" }
  n_components:
    label: "PCA Components"
    when: use_pca.yes             # conditional: only exists when use_pca=yes
    default: "50"
    options:
      "50": { label: "50 components" }
      "100": { label: "100 components" }
outputs:
  - id: accuracy
    type: metric
    recipe:
      command: python scripts/evaluate.py
container:
  build: Containerfile
```

**Multi-stage analyses** use `analyses:` for pipelines. Each sub-analysis has its own inputs, outputs, and decisions. Sub-analysis inputs wire together with `from:` (parent input: `from: input_id`, sibling output: `from: sibling.output_id`).

### Decision Parameterization

**Every decision must be parameterized in code** -- never hardcode a decision value. Accept all decisions as CLI args.

**Underscore convention:** IDs use underscores in `asp.yaml` (`prior_range`). Prism passes `--prior_range wide`. Scripts must match: `parser.add_argument('--prior_range')`, **not** `--prior-range`.

### Decision Constraints

Options can declare constraints using `decision_id.option_id` format:

```yaml
options:
  method_a:
    label: "Method A"
    incompatible_with: ["scaling.minmax"]   # cannot coexist in a universe
    requires: ["library.scipy"]             # must be selected together
```

**Conditional decisions** use `when:` -- the decision only exists when a specific option is selected (see `n_components` example above).

**Excluded options** record choices that were considered but rejected:

```yaml
options:
  deprecated_method:
    label: "Old Method"
    excluded: true
    excluded_reason: "Superseded by method_a; see insight_id"
```

Excluded options cannot be defaults or selected in universes.

### Writing Results

Convention path: `results/<universe_id>/<output_id>.<ext>` -- no `path` field needed.

- `metric` -- JSON (`{"value": 0.95}`)
- `figure` -- PNG
- `table` -- CSV
- `data` -- Parquet/HDF5
- `report` -- Markdown

### Recipe Format

Inline on outputs. Fields: `command` (required), `inputs` (output IDs that must exist first), `container` (overrides analysis-level default), `resources` (`cpus`, `memory`, `gpus`, `time_limit`). Set `container:` at analysis level for all recipes; per-recipe overrides. Accepts build spec (`{ build: Containerfile }`) or image string.

### Key Commands

```bash
asp validate asp.yaml                       # Validate (run after every change)
asp info [--decisions]                      # Analysis summary / decision details
asp universe generate -n NAME [-d "desc"]   # Generate universe from defaults
prism run [OUTPUT] [--universe NAME]        # Execute recipes via Dagster
prism status [--universe NAME]              # Materialization + container status
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

Insights link evidence to decisions using W3C selectors. Each insight needs `id`, `claim`, `created_at`, and at least one `evidence` entry. Evidence requires exactly one of `doi` or `artifact`, plus at least one content selector (`quote`, `figure`, or `table`).

```yaml
insights:
  layer_norm_stability:
    id: layer_norm_stability
    claim: "Layer normalization improves training stability"
    created_at: "2025-01-15T10:30:00"
    evidence:
      - id: e1
        doi: "10.48550/arXiv.1607.06450"
        quote: { type: TextQuoteSelector, exact: "Exact text", prefix: "context before", suffix: "context after" }
        location: { type: FragmentSelector, page: 5 }
```

Other selectors: `figure: { type: FigureSelector, label: "Figure 3a" }`, `table: { type: TableSelector, label: "Table 1" }`. For computed outputs, use `artifact: "output_id"` instead of `doi`.

Link to decisions: `options: { layer_norm: { insights: [layer_norm_stability] } }`

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
