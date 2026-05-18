---
name: lc-new
description: Guide for scoping a new ASTRA analysis from a research question.
---

# New ASTRA Analysis

Use this skill when the user asks to scope a new analysis from a research
question, loose idea, or desired scientific output. The goal is to turn the
conversation into a precise `astra.yaml` before implementation work starts.

Do not treat scoping as a coding task. First establish the analysis structure:
what question is being answered, what data can be used, what outputs count as
answers, and which methodological choices should be explicit decisions.

## Workflow

1. Clarify the research question in the user's terms.
2. Ask what a satisfactory answer would look like.
3. Identify allowed inputs and any data that must not influence the result.
4. Define outputs as concrete artifacts, metrics, tables, plots, or reports.
5. Identify methodological decisions that could affect the result.
6. Draft or update `astra.yaml`.
7. Generate or update a baseline universe when defaults are clear.
8. Validate the spec and hand off implementation only after the structure is
   coherent.

## Analysis Structure

Prefer one output per concrete result. Do not make one broad output like
`performance_metrics` if the project actually produces accuracy, calibration,
and a ROC plot. Each independently interpreted artifact should be its own
output.

Split into sub-analyses only when stages have genuinely different inputs,
outputs, or scientific roles. If a training step and evaluation step together
produce one model assessment, they may belong in one analysis. If the stages
are independently meaningful products, sub-analyses may be appropriate.

## Decisions

Probe for decisions beyond obvious method choices:

- data inclusion and exclusion criteria;
- thresholds and quality cuts;
- statistical estimators and uncertainty methods;
- model families or algorithm choices;
- priors, smoothing, binning, and convergence criteria;
- operational definitions of measured quantities.

Skip implementation details that should not affect scientific interpretation.
When unsure, include the candidate decision in `astra.yaml` for review rather
than burying it in code.

## Spec-Code Invariant

During scoping, `astra.yaml` is the source of truth. Once implementation
starts, the code must follow it. If the user asks for code before the spec is
coherent, state the gap and finish the spec first.

After drafting or changing the spec, run if available:

```bash
astra validate astra.yaml
lc status
```

If outputs or recipes were implemented as part of the work, continue with:

```bash
lc run <changed_output>
lc verify
```

Do not produce final results by manual edits. Do not hide failed validation or
execution. Surface unresolved questions clearly and keep them in the spec or
project notes where appropriate.
