---
name: lc-cli
description: Reference for lightcone-cli execution commands and project checks.
---

# lightcone-cli Reference

Use `lc` as the execution surface for ASTRA projects. It ties together
recipes, containers, universes, manifests, and provenance checks. Scripts
can be run directly while debugging, but final analysis outputs must be
materialized through `lc run` so the result has a traceable manifest.

## Commands

```bash
lc init [DIR]                       # scaffold a project
lc run [OUTPUTS...]                 # materialize all or selected outputs
lc run output_id --universe NAME    # materialize one output in one universe
lc status                           # show ok, missing, stale, alias, invalid
lc status --json                    # machine-readable status
lc verify                           # recompute hashes and validate provenance
lc build                            # build project containers
lc export wrroc                     # export a Workflow Run RO-Crate
```

`lc run` is quiet by default. If a run fails, inspect the actual error and fix
the cause; do not hide failures by writing placeholder outputs, weakening
recipes, or bypassing `lc`.

## Core Invariants

- `astra.yaml` is the source of truth for the analysis structure.
- The spec-code invariant must hold: when code, inputs, parameters, outputs,
  or recipe commands change, update `astra.yaml` in the same change.
- Results under `results/<universe>/<output_id>/` are not hand-authored
  deliverables. They are materialized outputs with `.lightcone-manifest.json`
  provenance.
- Do not patch results in place to make status look clean. Update the spec or
  code, rerun `lc run`, then verify.
- Do not mask execution failures. A failed run is information that should lead
  to a concrete fix.

## Development Flow

1. Edit code and `astra.yaml` together.
2. If the ASTRA CLI is available, run:

   ```bash
   astra validate astra.yaml
   ```

3. Check what changed:

   ```bash
   lc status
   ```

4. Materialize the smallest useful target:

   ```bash
   lc run output_id --universe baseline
   ```

5. After relevant outputs are materialized, run:

   ```bash
   lc verify
   ```

For multi-output projects, prefer running one upstream output at a time while
debugging. It is usually easier to inspect a direct failure than to run the
whole DAG and debug from a downstream error.

## Status Meanings

- `ok`: output has a manifest that matches the current spec and inputs.
- `stale`: spec, code, decisions, or upstream data changed after the last run.
- `missing`: recipe exists, but no current manifest is present.
- `alias`: output is produced by another recipe or references another output.
- invalid or verification failures: inspect with `lc verify`, then rerun the
  affected recipe after fixing the cause.

## Failure Handling

Common causes:

- Recipe command references `{decisions.foo}` or `{inputs.bar}` but the output
  does not declare that decision or input.
- Script argument names do not match the recipe command.
- A script writes outside `{output}`, leaving the output directory empty or
  incomplete.
- Existing files were copied into `results/` without a manifest.
- A result file was edited after materialization, causing a hash mismatch.

Fix the recipe, script, or spec. Then run `astra validate astra.yaml` if
available, `lc run ...`, `lc status`, and `lc verify`.
