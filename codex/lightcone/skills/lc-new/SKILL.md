---
name: lc-new
description: Guide for scoping a new ASTRA analysis from a research question.
---

# New ASTRA Analysis

Use this skill when starting from a research question or loose analysis idea.
The goal is to turn the idea into a precise `astra.yaml` before implementing
code.

Process:

1. Identify the research question and the decision the analysis informs.
2. Define the inputs that are allowed to influence the result.
3. Define outputs as concrete artifacts, metrics, tables, or plots.
4. Record important methodological choices as decisions.
5. Keep implementation work separate until the spec is coherent.

After drafting the spec, validate it and inspect project state:

```bash
astra validate astra.yaml
lc status
```
