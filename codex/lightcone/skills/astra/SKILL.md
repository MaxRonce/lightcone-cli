---
name: astra
description: Reference for ASTRA project structure and astra.yaml authoring.
---

# ASTRA Reference

ASTRA projects describe an analysis in `astra.yaml`. Treat that file as
the durable specification for inputs, outputs, decisions, and recipes.

Use this skill when editing or reviewing `astra.yaml`:

- Keep output ids stable once results exist.
- Make each output represent one concrete artifact, metric, table, or plot.
- Keep recipes executable through `lc run`; do not rely on hidden manual
  steps.
- Update the spec when scripts, parameters, inputs, or decisions change.

Useful checks:

```bash
astra validate astra.yaml
lc status
lc verify
```
