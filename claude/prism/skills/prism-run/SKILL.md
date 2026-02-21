---
name: prism-run
description: Execute ASP analysis recipes via Dagster — materialize outputs, monitor status, diagnose failures. Use when the user wants to run their analysis, check results, or troubleshoot execution.
allowed-tools: Read, Glob, Grep, Bash(asp:*), Bash(prism:*), Bash(python:*), Bash(docker:*), AskUserQuestion
---

# /prism-run

Execute ASP analysis recipes via Dagster. Materialize outputs, monitor progress, and diagnose failures.

## References

- [Prism Reference](./../prism/SKILL.md) — core concepts, CLI, validation

## Pre-Flight

Before running anything:

1. **Validate the spec**: `asp validate asp.yaml`
2. **Check recipes exist**: Look at `asp.yaml` outputs — each output that should be computed needs a `recipe:` block
3. **Verify container images**: If recipes reference container images, ensure they're accessible
4. **Check universe exists**: `ls universes/` — at least `baseline.yaml` should exist

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRISM ► EXECUTION PRE-FLIGHT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Running

### Basic Commands

```bash
# Run everything (all outputs, all universes)
prism run

# Run specific output
prism run accuracy

# Run for specific universe
prism run --universe baseline

# Run specific output + universe
prism run accuracy --universe baseline

# Run on remote target (SLURM)
prism run --target perlmutter
```

### Execution Flow

1. `prism run` reads `asp.yaml`, builds Dagster asset graph
2. Each output with a recipe becomes a Dagster asset
3. Dependencies (`recipe.inputs`) determine execution order
4. Container runner executes each recipe (Docker or SLURM)
5. Results are written to `results/<universe_id>/<output_id>/`

---

## Monitoring

```bash
# Check what's been materialized
prism status

# Check specific universe
prism status --universe baseline

# Launch full Dagster UI
prism dev
```

The status table shows each output vs universe:
- `ok` — output directory exists with files
- `not run` — output hasn't been materialized yet

---

## Inspecting Results

After execution, check outputs:

```bash
# List all results for a universe
ls results/baseline/

# Check specific output
ls results/baseline/trained_model/
cat results/baseline/accuracy/accuracy.json
```

---

## Failure Diagnosis

When execution fails:

1. **Check status**: `prism status` — which outputs failed?
2. **Check the error**: The CLI will show error messages from the container
3. **Check the script**: Read the script referenced in `recipe.command`
4. **Fix and re-run**: After fixing, `prism run <failed_output> --universe <name>`

### Common Issues

| Problem | Solution |
|---------|----------|
| "No container specified" | Add `container:` to the recipe or set analysis-level default |
| "Dagster not installed" | `pip install prism[dagster]` |
| Container image not found | Check image reference, ensure Docker can pull it |
| Recipe input not found | Check that input outputs have been materialized first |
| Permission denied | Check Docker permissions or SLURM account config |

---

## Recipe Format

Recipes are inline on outputs in `asp.yaml`:

```yaml
outputs:
  - id: cleaned_data
    type: data
    recipe:
      command: python scripts/clean.py
      container: ghcr.io/proj/analysis@sha256:abc
      resources: { cpus: 2, memory: 8GB }

  - id: trained_model
    type: data
    recipe:
      command: python scripts/train.py
      inputs: [cleaned_data]
      container: ghcr.io/proj/ml@sha256:def
      resources:
        cpus: 8
        memory: 32GB
        gpus: 1
        time_limit: 2h
```

### Recipe Fields

- `command` (required): Shell command to execute
- `inputs` (optional): List of output IDs this depends on
- `container` (optional): OCI image reference
- `resources` (optional): `cpus`, `memory`, `gpus`, `time_limit`

---

## Target Selection

For remote execution on HPC:

```bash
# List configured targets
prism remote setup --list

# Run on a target
prism run --target perlmutter
```

Configure targets with `prism remote setup <name>`.

---

## Rules

- **Always validate first** — `asp validate asp.yaml` before running
- **Check status after runs** — `prism status` to confirm materialization
- **Fix and re-run** — don't try to manually create output files
- **Inspect actual outputs** — read result files to verify correctness
