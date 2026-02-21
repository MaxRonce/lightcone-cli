# Dagster Execution Layer Design

**Date:** 2026-02-21
**Status:** Approved

## Overview

Integrate a Dagster-based execution layer into Prism as a first-class component. ASP outputs become Dagster assets, recipes are the execution instructions that materialize them, and universes map to Dagster partitions. This replaces the existing remote/HPC infrastructure with a unified execution framework.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Packaging | Integrated into Prism (`prism[dagster]`) | Skills need to know how to run things through Dagster |
| Recipe source | Existing `asp.yaml` outputs | Single source of truth, no new file format |
| Container runtime | Docker-first via `dagster-docker` | Native Dagster integration via PipesDockerClient |
| Initial backends | Local Docker + SLURM | HPC is a primary use case |
| IO conventions | Custom Dagster IO Manager | Clean separation: Dagster manages DAG, IO Manager manages ASP path conventions |
| CLI | Under existing `prism` CLI | Consistent with `prism init`, `prism remote` |
| Agent autonomy | CLI-mediated | Auditable, guardable via hooks, `prism run` / `prism status` |
| Recipe format | Inline on outputs, no shared recipe block | 1:1 mapping to Dagster `@asset`, trivial factory loop |
| Asset mapping | Output = Asset, Universe = Partition | Natural fit with Dagster's partitioned asset model |

## Architecture

```
asp.yaml (outputs with inline recipes)
    |
    v
build_definitions()                    # prism.dagster.assets
    |
    v
For each output with a recipe:
    output -> @asset(name=output_id, deps=recipe.inputs)
    universes -> DynamicPartitionsDefinition
    |
    v
Definitions(assets, resources, jobs)
    |
    +-- ASPContainerRunner             # prism.dagster.runner
    |   (Docker or SLURM dispatch)
    |
    +-- ASPIOManager                   # prism.dagster.io_manager
        (results/<universe>/<output>/ path conventions)
```

## 1. ASP Schema Changes

The recipe format moves from a top-level recipe-centric block to inline recipes on outputs.

### Current format (removed)

```yaml
recipes:
  train:
    command: python scripts/train.py
    outputs: [trained_model]
    depends_on: [preprocess]
    container: ghcr.io/proj/ml@sha256:def
    resources: { cpus: 4 }
```

### New format (recipe on output)

```yaml
outputs:
  cleaned_data:
    type: data
    recipe:
      command: python scripts/clean.py
      container: ghcr.io/proj/analysis@sha256:abc
      resources: { cpus: 2, memory: 8GB }

  trained_model:
    type: data
    recipe:
      command: python scripts/train.py
      inputs: [cleaned_data]
      container: ghcr.io/proj/ml@sha256:def
      resources:
        cpus: 8
        memory: 32GB
        gpus: 1
        time_limit: 2h

  accuracy:
    type: metric
    recipe:
      command: python scripts/evaluate.py
      inputs: [trained_model]
      resources: { cpus: 4 }

  confusion_matrix:
    type: figure
    recipe:
      command: python scripts/evaluate.py
      inputs: [trained_model]
      resources: { cpus: 4 }
```

### Recipe fields

- `command` (required): shell command to execute
- `inputs` (optional): list of output IDs this depends on
- `container` (optional): OCI image reference, overrides analysis-level default
- `resources` (optional): `cpus`, `memory`, `gpus`, `time_limit`

### ASP changes required

- **Pydantic models (`models/analysis.py`):** `Output` gains optional `recipe` field. `Recipe` model: remove `outputs` list, rename `depends_on` to `inputs`. Remove top-level `recipes` from `Analysis`.
- **JSON schemas:** Regenerate via `tools/generate_schemas.py`.
- **Semantic validation:** Output-to-output cycle detection. Validate recipe `inputs` reference declared outputs.
- **Helpers:** Add `get_recipe()`, `get_output_dependencies()`.
- **CLI:** `asp info` shows per-output recipe status.
- **Examples and tests:** Update to new format.

## 2. Prism Package Structure

```
src/prism/
├── __init__.py              # existing
├── cli.py                   # rewrite: init + run/status/dev/remote
└── dagster/                 # NEW subpackage
    ├── __init__.py          # public API: build_definitions()
    ├── assets.py            # asset factory: asp.yaml -> @asset
    ├── io_manager.py        # ASPIOManager: /workspace/ + universe paths
    ├── runner.py            # ASPContainerRunner: Docker + SLURM dispatch
    ├── targets.py           # target config (replaces remote.py)
    └── status.py            # materialization status queries
```

### Dependencies

```toml
[project.optional-dependencies]
dagster = [
    "dagster>=1.9",
    "dagster-webserver>=1.9",
    "dagster-docker>=0.25",
]
```

`pip install prism` gives scaffolding and skills. `pip install prism[dagster]` adds the execution layer. Commands `prism run`, `prism status`, `prism dev` gracefully error if dagster is not installed.

### Removed

- `src/prism/remote.py` -- replaced by `dagster/targets.py`
- `claude/prism/scripts/hpc-guard.sh` -- Dagster enforces resource limits
- `claude/prism/scripts/hpc-session-start.sh` -- `prism status` replaces this
- `prism canvas` / `prism navigator` commands -- removed entirely
- `canvas` optional dependency -- removed

## 3. Asset Factory

The factory reads `asp.yaml` and generates one `@asset` per output with a recipe. Universes become Dagster partitions.

```python
def build_definitions(project_path: Path, target: str | None = None) -> dg.Definitions:
    spec = asp.load_yaml(project_path / "asp.yaml")
    outputs = asp.get_outputs(spec)

    assets = []
    for output_id, output_def in outputs.items():
        if "recipe" in output_def:
            assets.append(build_asset(output_id, output_def["recipe"]))
        else:
            assets.append(build_external_asset(output_id))

    runner = build_runner_from_target(target, str(project_path))
    return dg.Definitions(
        assets=assets,
        resources={
            "runner": runner,
            "io_manager": ASPIOManager(project_root=str(project_path)),
        },
    )

def build_asset(output_id, recipe):
    input_ids = recipe.get("inputs", [])

    @dg.asset(
        name=output_id,
        deps=[dg.AssetKey(i) for i in input_ids],
        metadata={"command": recipe["command"]},
    )
    def _asset(context, runner: ASPContainerRunner):
        return runner.execute(
            command=recipe["command"],
            container=recipe.get("container"),
            inputs=input_ids,
            output_id=output_id,
            resources=recipe.get("resources", {}),
        )

    return _asset
```

Dependencies are output-to-output via recipe `inputs`. Cycle detection happens at ASP validation time. The factory is stateless -- re-reads `asp.yaml` each time.

### Multi-output optimization

When multiple outputs have identical `command` + `inputs` + `container` (e.g., `accuracy` and `confusion_matrix` both running `evaluate.py`), the runner detects this and executes the container once, collecting all outputs. This is an implementation detail in the runner, not a schema concern.

## 4. Container Runner

`ASPContainerRunner` is a Dagster resource that executes recipes in containers, dispatching to Docker or SLURM.

```python
class ASPContainerRunner(dg.ConfigurableResource):
    project_root: str
    backend: str = "docker"
    default_container: str | None = None
    target_config: dict | None = None
```

### Docker execution flow

1. Resolve container image (recipe-level or analysis-level default)
2. Prepare mounts:
   - `results/<universe_id>/<input_id>/` -> `/workspace/inputs/<input_id>/` (read-only)
   - `results/<universe_id>/<output_id>/` -> `/workspace/outputs/<output_id>/`
3. Generate `params.json` from universe decision selections, mount as `/workspace/params.json`
4. Translate resources to Docker flags (`--cpus`, `--memory`, `--gpus`)
5. `docker run --rm <flags> <mounts> <image> <command>`
6. Collect outputs, return `MaterializeResult` with metadata (exit code, duration, output files)

### SLURM execution flow

1. Resolve container image
2. Translate resources to SLURM directives (`#SBATCH --cpus-per-task`, `--mem`, `--gres=gpu`, `--time`)
3. Generate sbatch script with container runtime (Shifter or Podman-HPC)
4. Submit via SSH: `sbatch job.sh`
5. Poll for completion (`sacct`/`squeue`)
6. Collect outputs from shared filesystem
7. Return `MaterializeResult` with metadata (slurm_job_id, node, walltime, exit code)

### Resource translation

| Resource | Docker | SLURM |
|----------|--------|-------|
| `cpus: 4` | `--cpus=4` | `--cpus-per-task=4` |
| `memory: 16GB` | `--memory=16g` | `--mem=16G` |
| `gpus: 1` | `--gpus=1` | `--gres=gpu:1` |
| `time_limit: 2h` | `--timeout=7200` | `--time=02:00:00` |

## 5. IO Manager

The `ASPIOManager` maps `(asset_key, partition_key)` to filesystem paths following ASP conventions.

```python
class ASPIOManager(dg.ConfigurableIOManager):
    project_root: str

    def _get_path(self, asset_key, partition_key) -> Path:
        output_id = asset_key.path[-1]
        universe_id = partition_key
        return Path(self.project_root) / "results" / universe_id / output_id

    def handle_output(self, context, obj):
        path = self._get_path(context.asset_key, context.partition_key)
        context.add_output_metadata({"path": str(path)})

    def load_input(self, context):
        return self._get_path(context.asset_key, context.partition_key)
```

Results directory structure:

```
results/
├── baseline/
│   ├── cleaned_data/
│   ├── trained_model/
│   ├── accuracy.json
│   └── confusion_matrix.png
├── experiment1/
│   ├── cleaned_data/
│   └── ...
└── .dagster/              # event storage (SQLite), gitignored
```

## 6. Target Configuration

Targets define where Dagster dispatches execution. Stored in `~/.prism/targets/`.

### SLURM target example (`~/.prism/targets/perlmutter.yaml`)

```yaml
name: perlmutter
backend: slurm

connection:
  hostname: perlmutter.nersc.gov
  username: francois

scheduler:
  account: m1234
  partition: gpu
  constraint: gpu&hbm80g
  container_runtime: shifter

resource_limits:
  max_nodes: 4
  max_walltime_minutes: 240
  max_concurrent_jobs: 8
  max_node_hours_per_session: 32
```

### Target resolution

```python
def build_runner_from_target(target, project_root) -> ASPContainerRunner:
    if target is None:
        return ASPContainerRunner(backend="docker", project_root=project_root)
    config = load_target(target)
    return ASPContainerRunner(
        backend=config["backend"],
        project_root=project_root,
        target_config=config,
    )
```

`prism remote setup <name>` is rewritten as an interactive wizard collecting Dagster-relevant fields: backend type, connection details, scheduler config, container runtime, resource limits.

## 7. CLI Commands

### `prism run [OUTPUT...] [--universe NAME] [--target NAME]`

Materialize outputs via Dagster.

```bash
prism run                                # all outputs, all universes
prism run accuracy                       # one output, all universes
prism run --universe baseline            # all outputs, one universe
prism run accuracy --universe baseline   # one output, one universe
prism run --target perlmutter            # execute on SLURM
```

Shows live Rich progress during execution. Prints summary table on completion.

### `prism status [--universe NAME]`

Show materialization state of all outputs.

```
$ prism status
  ASP Analysis: my_analysis (3 outputs, 2 universes)

  Output             baseline    experiment1
  ---                ---         ---
  cleaned_data       ok 2m ago   ok 1m ago
  trained_model      ok 1m ago   not run
  accuracy           not run     not run

  3 materialized  3 pending
```

### `prism dev [--port PORT]`

Launch Dagster webserver UI. Generates temporary `workspace.yaml`, spawns `dagster-webserver`.

### `prism init` (updated)

- Generates `dagster.yaml` (SQLite storage in `results/.dagster/`)
- Updates `.gitignore` to include `results/.dagster/`
- No longer generates HPC config or permission entries

### `prism remote setup|list|show|edit`

Rewritten for Dagster executor targets.

### Graceful degradation

`prism run`, `prism status`, `prism dev` check for dagster import. If missing: `"Dagster not installed. Run: pip install prism[dagster]"`.

## 8. Claude Code Skills

### New skills

**`/prism-run`** -- guides the agent through execution:

1. Validate analysis (`asp validate asp.yaml`)
2. Check recipe completeness
3. Execute via `prism run [OUTPUT...] --universe <name>`
4. Monitor with `prism status`
5. Inspect outputs in `results/<universe_id>/`
6. On failure: read logs, diagnose, fix script, re-run

**`/prism-status`** -- quick reference for pipeline inspection:

- `prism status` for overview table
- `prism dev` for full Dagster UI
- Staleness interpretation
- Re-materialization commands

### Updated skills

- **`/prism`**: Add execution section (run, status, dev, recipe format)
- **`/prism-new`**: Inline recipe format during analysis creation
- **`/prism-verify`**: Materialization-aware via `prism status`

### Agent workflow (end-to-end)

```
/prism-new          -> scope analysis, declare outputs with inline recipes
    |
agent writes src/   -> implementation scripts
    |
/prism-run          -> prism run --universe baseline
    |
agent inspects      -> results/baseline/*, prism status
    |
/prism-verify       -> verify completeness and correctness
```

## 9. Change Summary

### ASP repo

| Action | File | What |
|--------|------|------|
| Change | `models/analysis.py` | Recipe on Output, remove top-level recipes |
| Change | `spec/draft/analysis.schema.json` | Regenerate schema |
| Change | `src/asp/validation/semantic.py` | Output-to-output DAG validation |
| Change | `src/asp/helpers.py` | Recipe helpers on outputs |
| Change | `src/asp/cli.py` | `asp info` shows per-output recipe status |
| Change | `examples/iris/asp.yaml` | New recipe format |
| Change | `tests/` | Update recipe test cases |

### Prism repo

| Action | File | What |
|--------|------|------|
| Add | `src/prism/dagster/__init__.py` | Public API: `build_definitions()` |
| Add | `src/prism/dagster/assets.py` | Asset factory |
| Add | `src/prism/dagster/io_manager.py` | ASPIOManager |
| Add | `src/prism/dagster/runner.py` | ASPContainerRunner (Docker + SLURM) |
| Add | `src/prism/dagster/targets.py` | Target config |
| Add | `src/prism/dagster/status.py` | Materialization queries |
| Add | `claude/prism/skills/prism-run/SKILL.md` | Execution skill |
| Add | `claude/prism/skills/prism-status/SKILL.md` | Status skill |
| Remove | `src/prism/remote.py` | Replaced by dagster/targets.py |
| Remove | `claude/prism/scripts/hpc-guard.sh` | Dagster enforces limits |
| Remove | `claude/prism/scripts/hpc-session-start.sh` | `prism status` replaces |
| Rewrite | `src/prism/cli.py` | Add run/status/dev, rewrite remote, remove canvas/navigator |
| Change | `pyproject.toml` | Add dagster optional deps, remove canvas dep |
| Change | `claude/prism/skills/prism/SKILL.md` | Add execution section |
| Change | `claude/prism/skills/prism-new/SKILL.md` | Inline recipe format |
| Change | `claude/prism/skills/prism-verify/SKILL.md` | Materialization-aware |
| Change | `claude/prism/templates/CLAUDE.md` | Update for execution workflow |
| Change | `tests/` | New dagster tests, update CLI tests, remove remote tests |
