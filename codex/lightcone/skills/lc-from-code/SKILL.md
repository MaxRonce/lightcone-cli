---
name: lc-from-code
description: Guide for wrapping an existing codebase or script as an ASTRA project.
---

# Existing Code to ASTRA

Use this skill when a project already has scripts, notebooks, or data
processing code and needs an ASTRA specification around it. The goal is to
preserve the existing behavior while making inputs, outputs, decisions, and
recipes explicit in `astra.yaml`.

## Workflow

1. Inventory the existing code before editing it.
2. Identify real analytical outputs and the files or commands that create
   them.
3. Identify inputs, dependencies, containers, and hardcoded analytical choices.
4. Draft or augment `astra.yaml`.
5. Parameterize code only as much as needed to match the spec.
6. Run through `lc run`, then inspect with `lc status` and `lc verify`.

## Scan First

For every script or notebook, determine:

- what it reads;
- what it writes;
- how it is invoked;
- which choices are hardcoded;
- which outputs are analytical results versus temporary files;
- which dependencies and environment assumptions it has.

Do not guess from filenames. Read the relevant code. If behavior is unclear,
say what is unclear and inspect the call sites, config files, or notebooks.

## Draft The Spec

Use `astra.yaml` as the source of truth. For each output, declare:

- `id` and `type`;
- upstream inputs;
- methodological decisions that parameterize it;
- a `recipe.command` that can run from the project root;
- a container at analysis or recipe level when needed.

Use current hardcoded behavior as the baseline default unless the user asks to
change it. If a baseline universe exists, keep it consistent with those
defaults.

## Parameterize Carefully

Make minimal code changes. Do not refactor, rename, or reorganize existing
logic unless it is necessary to make the recipe executable.

Common patterns:

- Add `argparse` flags for hardcoded decision values.
- Pass `{decisions.<id>}` and `{inputs.<id>}` from the recipe command.
- Pass `{output}` as an output directory and write artifacts inside it.
- Convert notebooks into small scripts only when notebook-only execution blocks
  reproducibility.
- Add missing dependencies to `requirements.txt` or the project environment
  file if imports require them.

Keep the spec-code invariant intact. If a recipe changes, update `astra.yaml`.
If a script gains a new parameter, represent it in the spec when it affects the
analysis.

## Run And Verify

After spec or code changes, run if available:

```bash
astra validate astra.yaml
lc status
lc run <changed_output>
lc status
lc verify
```

Do not copy old outputs into `results/` to make the project appear complete.
Do not edit generated result files directly. Do not suppress failing commands
with shell tricks that hide nonzero exits. If `lc run` fails, read the error,
fix the recipe/code/spec, and rerun.

When migration is complete, the baseline run should reproduce the original
behavior as closely as possible, and all final outputs should be traceable
through Lightcone manifests.
