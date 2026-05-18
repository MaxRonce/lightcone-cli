---
name: lc-cli
description: Reference for lightcone-cli execution commands and project checks.
---

# lightcone-cli Reference

Use `lc` as the execution surface for ASTRA projects. It keeps recipes,
containers, universes, manifests, and provenance checks tied together.

Common commands:

```bash
lc run [OUTPUTS...]       # materialize all or selected outputs
lc status                 # show current, missing, stale, and invalid outputs
lc verify                 # recompute hashes and validate provenance
lc build                  # build project containers
```

Workflow rules:

- Run recipes through `lc run`, not by calling scripts manually.
- Use `lc status` after edits to see what needs rematerialization.
- Use `lc verify` before handing off completed work.
- If a result is stale, update the recipe/spec or rerun it; do not patch the
  result in place.
