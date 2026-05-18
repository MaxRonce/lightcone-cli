# AGENTS.md

This is an ASTRA analysis project orchestrated by `lightcone-cli`.

The source of truth is `astra.yaml`. Keep the spec, recipes, scripts, and
recorded outputs in sync. Do not edit or replace files under `results/`
without updating the relevant `astra.yaml` recipe or decisions and
rematerializing the output through `lc run`.

Use the `lc` commands for execution and checks:

```bash
lc run                    # materialize outputs in the default universe
lc run output_id          # materialize one output
lc status                 # inspect missing, stale, and current outputs
lc verify                 # validate manifests and provenance integrity
```

When changing analysis code, update `astra.yaml` in the same change if the
inputs, outputs, decisions, parameters, or command recipes changed. Run
`lc status` and `lc verify` before considering the project state complete.
