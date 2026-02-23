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
2. **Check recipe coverage**: Run `prism status` to see which outputs have recipes — only those will be executed
3. **Build containers**: If using `container: {build: Containerfile}`, run `prism build` (or let `prism run` auto-build)
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
- `pending` — has recipe, not yet materialized
- `no recipe` — output declared but no recipe block yet

### Partial Execution

`prism run` only materializes outputs that have recipes. Outputs still in
development (showing `no recipe` in `prism status`) are skipped — this is
expected during progressive development. Add recipes as scripts become ready.

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
| Container not built | Run `prism build` or remove `--no-build` flag |
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

## Running on NERSC (Perlmutter)

Perlmutter uses SLURM with **podman-hpc** (recommended) or **shifter** as the container runtime. Prism handles everything automatically: building/migrating container images, generating sbatch scripts, submitting jobs, and polling for completion.

### One-Time Setup

Configure the Perlmutter target (the wizard auto-detects Perlmutter and pre-fills most defaults — you only need the user's account/allocation):

```bash
prism remote setup perlmutter
```

### Running

```bash
prism run --target perlmutter
prism run trained_model --target perlmutter --universe baseline
```

Container images are automatically built (`podman-hpc build`) and migrated for compute nodes, or pulled via `shifterimg` for Shifter targets. Use `prism build --runtime podman-hpc` to pre-build without running.

### Local Environment vs Container Execution

Scripts run inside containers on compute nodes. You do **not** need to install Python packages locally for HPC execution — `requirements.txt` and the `Containerfile` define the execution environment. A local `.venv` is useful for IDE support and linting, but `prism run --target` uses the container image exclusively.

### Example recipe for GPU jobs

```yaml
outputs:
  - id: trained_model
    type: data
    recipe:
      command: python scripts/train.py
      container: ghcr.io/myorg/myanalysis:latest
      resources:
        cpus: 64
        gpus: 4
        memory: 256GB
        time_limit: 2h
```

The `gpus:` field automatically adds `--gpu` to the `podman-hpc` invocation and `#SBATCH --gpus=<n>` to the script.

### Monitoring SLURM jobs

```bash
prism status
squeue -u $USER
sacct -j <job_id> --format=JobID,State,ExitCode,Elapsed
cat results/.slurm/<output_id>_<universe_id>.out
cat results/.slurm/<output_id>_<universe_id>.err
```

### Common NERSC Issues

| Problem | Solution |
|---------|----------|
| `sbatch: command not found` | You must run `prism run --target` from a Perlmutter login node |
| MPI performance poor | Add `--mpi` to container flags: `prism remote edit perlmutter` |
| NCCL errors on multi-GPU | Add `--nccl` (and optionally `--cuda-mpi`) to container flags |
| Job not found in `prism status` | Give sacct a moment — it may lag by ~30s after completion |
| SLURM rejects job (no time limit) | Prism defaults to the target's `max_walltime_minutes` (or 30 minutes). For precise control, add `resources: { time_limit: 2h }` to the recipe in `asp.yaml`. |
| `--prior_range` not recognized by script | Decision IDs use underscores → Prism passes `--prior_range`. Scripts must use underscores in argparse: `parser.add_argument('--prior_range')` |
| GPU allocation wasted on CPU-only work | Edit target: `prism remote edit <name>`, set `partition: cpu` and `constraint: cpu`. GPU partitions waste allocation hours on CPU workloads. |
| `prism status` shows "Container: not built" | Expected when targeting HPC — `prism run --target` builds/migrates containers automatically on the target. Run `prism build` locally only for local Docker execution. |

---

## Rules

- **Always validate first** — `asp validate asp.yaml` before running
- **Check status after runs** — `prism status` to confirm materialization
- **Fix and re-run** — don't try to manually create output files
- **Inspect actual outputs** — read result files to verify correctness
