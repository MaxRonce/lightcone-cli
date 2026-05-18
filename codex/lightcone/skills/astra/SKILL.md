---
name: astra
description: Reference for ASTRA project structure and astra.yaml authoring.
---

# ASTRA Reference

ASTRA projects describe an analysis in `astra.yaml`. Treat that file as the
durable specification for inputs, outputs, decisions, findings, sub-analyses,
containers, and recipes. The code implements the spec; it should not hide
extra analytical choices that are absent from `astra.yaml`.

## What Belongs In The Spec

- Inputs: data, files, external analysis outputs, or other material
  dependencies.
- Outputs: concrete artifacts, metrics, tables, plots, reports, or datasets.
- Decisions: methodological choices where multiple defensible options could
  affect the result.
- Recipes: commands that materialize outputs through `lc run`.
- Containers: the environment needed to run recipes reproducibly.

Keep output ids stable once results exist. If an output changes meaning, prefer
adding a new output or clearly updating the spec and rerunning the affected
recipes.

## Decisions

A decision is an analytical choice, not a general implementation detail.
Include choices such as thresholds, statistical methods, filtering criteria,
model families, binning, smoothing, priors, convergence criteria, and data
selection rules. Skip choices that should not change the scientific answer,
such as ordinary refactors, plotting style, file formats, or library choices
that produce equivalent results.

Every decision used by code should be parameterized. The recipe should pass it
with `{decisions.<id>}`, and the script should accept the corresponding command
line argument or config value. Do not leave decision values hardcoded in code
while claiming they are represented in `astra.yaml`.

## Outputs And Recipes

Each output should represent one concrete result. Avoid bundling unrelated
metrics or plots into one output just because one script can create them.

Recipes live under outputs and describe how to materialize the output:

```yaml
outputs:
  - id: accuracy
    type: metric
    inputs: [training_data]
    decisions: [model_family, threshold]
    recipe:
      command: >-
        python src/evaluate.py
        --data {inputs.training_data}
        --model {decisions.model_family}
        --threshold {decisions.threshold}
        --output {output}
```

The output should be written under `{output}`. Do not write final artifacts to
untracked ad hoc paths and then copy them into `results/`.

## Spec-Code Invariant

`astra.yaml` and code must move together:

- New script argument or analytical parameter: add or update the matching
  decision and recipe.
- New result: add an output and recipe.
- Changed input data path: update the input declaration.
- Removed or renamed output: update the spec, universes, code, and any
  downstream references.
- Changed default behavior: update the baseline universe or default option.

## Validation And Checks

If available, run:

```bash
astra validate astra.yaml
lc status
lc run <changed_output>
lc verify
```

If `astra validate` is unavailable in the environment, say that explicitly and
continue with structural review plus `lc status` / `lc verify` where possible.
Do not ignore validation failures. Fix the spec or explain the remaining
blocker.
