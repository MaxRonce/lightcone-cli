---
name: lc-from-code
description: Guide for wrapping an existing codebase or script as an ASTRA project.
---

# Existing Code to ASTRA

Use this skill when a project already has scripts, notebooks, or data
processing code and needs an ASTRA specification around it.

Process:

1. Inventory the existing code and identify real analytical outputs.
2. Map each output to a recipe command that can run from the project root.
3. Record required inputs, parameters, and methodological decisions in
   `astra.yaml`.
4. Prefer small reproducible scripts over notebook-only execution.
5. Run through `lc run` and inspect with `lc status` and `lc verify`.

Do not change generated results directly. If existing outputs need to be
recreated, express the command in `astra.yaml` and let `lc run` materialize
them.
