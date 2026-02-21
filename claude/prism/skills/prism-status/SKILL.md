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
  ASP Analysis: my_analysis (3 outputs, 2 universes)

  Output             baseline    experiment1
  ---                ---         ---
  cleaned_data       ok 2m ago   ok 1m ago
  trained_model      ok 1m ago   not run
  accuracy           not run     not run

  3 materialized  3 pending
```

### Filter by Universe

```bash
prism status --universe baseline
```

## Interpreting Status

| Status | Meaning |
|--------|---------|
| `ok` | Output directory exists and contains files |
| `not run` | Output has not been materialized |

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

## Rules

- **Status is filesystem-based** — it checks if output directories contain files
- **Re-running is safe** — Dagster tracks dependencies and won't re-run upstream unless needed
- **One universe at a time** for detailed inspection
