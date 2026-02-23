# Eliminate Perlmutter HPC Friction

**Date**: 2026-02-23
**Status**: Approved

## Problem

Running `prism run --target perlmutter` surfaced six friction points that caused runtime failures or confusion. These should be preventable through better defaults in code and clearer guidance in skills.

## Friction Points

| # | Friction | Root Cause |
|---|---------|------------|
| 1 | Missing `--time` → SLURM rejection | No default walltime fallback when `resources.time_limit` is omitted |
| 2 | `nodes: 1` fails ASP validation | `nodes` is not in the ASP Resources schema; `/prism-run` example incorrectly showed it |
| 3 | `--prior_range` vs `--prior-range` | Prism emits underscored args; argparse scripts used hyphens |
| 4 | GPU partition for CPU work | Agent configured GPU partition for CPU-only MCMC workload |
| 5 | Local venv confusion | Agent installed packages locally instead of trusting the container |
| 6 | `prism status` shows "not built" | Misleading when `prism run --target` auto-builds on the HPC side |

## Changes

### Code: Default walltime for SLURM (`runner.py`)

In `translate_resources_to_slurm_directives()`, when no `time_limit` is present in resources and we're generating SLURM directives, inject `--time=00:30:00` as a 30-minute default. Log a warning so users know a default was applied and can set an explicit value for longer jobs.

### Skill: Fix `/prism-run` GPU example

Remove `nodes: 1` from the example recipe — it fails ASP validation and SLURM defaults to 1 node anyway.

### Skill: Expand `/prism-run` NERSC section

Add guidance for:
- **Partition selection**: CPU-only work → `constraint: cpu`, not GPU. Check/change via `prism remote edit`.
- **Underscore convention**: Decision IDs use underscores → CLI args use underscores → argparse must use underscores.
- **Local venv**: Scripts run in containers on compute nodes. Local venvs are for IDE/linting only.
- **Container status**: "not built" locally is expected when targeting HPC — `prism run --target` builds automatically.

### Template: `CLAUDE.md` template

Add note to Decision Parameterization about using underscores in argparse to match decision IDs.
