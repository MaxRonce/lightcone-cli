---
name: prism-status
description: Quick reference for inspecting ASP pipeline status — materialization state, output inspection, and re-execution. Use when checking what has run, what hasn't, and what needs re-running.
allowed-tools: Read, Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(ls:*)
---

# /prism-status

Quick reference for inspecting the execution state of an ASP analysis.

## Status Overview

```bash
prism status
```

Shows a table of all outputs vs all universes:

```
  my_analysis — Output Status

  Output             baseline      experiment1
  ---                ---           ---
  cleaned_data       ok            ok
  trained_model      ok            pending
  accuracy           pending       pending
  visualization      no recipe     no recipe

  Recipes: 3/4 outputs integrated
  Materialized: 3/6 runs
```

### Filter by Universe

```bash
prism status --universe baseline
```

## Interpreting Status

| Status | Meaning |
|--------|---------|
| `ok` | Output has recipe and results exist |
| `pending` | Output has recipe but not yet materialized |
| `no recipe` | Output declared but no recipe block yet |

## Integration Progress

Outputs progress through three states as development proceeds:

`no recipe` → `pending` → `ok`

1. **no recipe** — Output is declared in `asp.yaml` but has no `recipe:` block. The script is still being written or debugged.
2. **pending** — A `recipe:` block has been added. The output is ready for `prism run` but hasn't been materialized yet.
3. **ok** — The recipe has been executed and results exist on disk.

## Re-Materializing

To re-run a specific output:
```bash
prism run <output_id> --universe <universe_id>
```

To re-run everything:
```bash
prism run
```

## Full Dagster UI

For a richer view with run history and asset graph:
```bash
prism dev
```

Opens a web UI at http://localhost:3000.

## Inspecting Outputs

```bash
# List materialized outputs
ls results/<universe_id>/

# Check specific output
ls results/<universe_id>/<output_id>/
```

## Container Status

`prism status` also shows the analysis-level container configuration:

- `prebuilt: python:3.12-slim` — using a pre-built image
- `build: Containerfile -> prism-proj-abc123 (built)` — build spec, image exists
- `build: Containerfile -> prism-proj-abc123 (not built)` — build spec, needs `prism build`

To build missing images: `prism build`

## Rules

- **Status is filesystem-based** — it checks if output directories contain files
- **Re-running is safe** — Dagster tracks dependencies and won't re-run upstream unless needed
- **One universe at a time** for detailed inspection
