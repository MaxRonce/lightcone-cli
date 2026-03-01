# Design: `prism setup` command

## Summary

Replace `prism remote setup` with a top-level `prism setup` command that configures the user's default execution environment. Auto-triggers on first use of any prism command. Constraint and container flags are derived automatically from node type selection.

## User-level config structure

### `~/.prism/config.yaml`

Tracks the default target:

```yaml
default_target: perlmutter
```

### `~/.prism/targets/<name>.yaml`

Individual target configs (unchanged location, refined schema):

```yaml
name: perlmutter
site: perlmutter
backend: slurm
connection:
  hostname: perlmutter.nersc.gov
  username: francois
scheduler:
  account: m1234
  node_type: gpu
  constraint: gpu           # auto-derived from node_type
  qos: regular
  container_runtime: podman-hpc
  container_flags: [--gpu]  # auto-derived from node_type
resource_limits:
  max_nodes: 4
  max_walltime_minutes: 360
  max_concurrent_jobs: 8
  max_node_hours_per_session: 64
```

### Project-level override (`prism.yaml`)

```yaml
target: perlmutter
```

## Setup wizard flow

```
$ prism setup

  Prism Setup — Default Execution Environment
  These settings are stored in ~/.prism/ and can be overridden per-project.

  Known HPC sites:
    1. NERSC Perlmutter
    2. Custom

  Select site [1]: 1
  Detected: NERSC Perlmutter (perlmutter.nersc.gov)

  Username [francois]: francois
  Account/allocation: m1234

  Node type:
    1. GPU (A100 40GB) — constraint: gpu, 1536 nodes
    2. GPU (A100 80GB) — constraint: gpu&hbm80g, 256 nodes
    3. CPU only — constraint: cpu, 3072 nodes
  Select node type [1]: 1
    -> Constraint: gpu
    -> Container flags: --gpu

  QOS:
    1. regular — Standard priority, max 48h
    2. debug — Quick tests, max 30min, 8 nodes max
    3. shared — Fractional GPU (1-2 GPUs), max 48h
    4. preempt — 0.25x cost, can be preempted after 2h
  Select QOS [1]: 1

  Container runtime:
    1. podman-hpc (Recommended)
    2. shifter
  Select runtime [1]: 1

  Resource limits:
    Max nodes per job [4]: 4
    Max walltime (minutes) [360]: 360
    Max concurrent jobs [8]: 8

  Target name [perlmutter]: perlmutter

  Saved target: ~/.prism/targets/perlmutter.yaml
  Set as default target in ~/.prism/config.yaml

  To override per-project, add to prism.yaml:
    target: <other-target-name>
```

## Auto-trigger

The `main` click group callback checks for `~/.prism/config.yaml` before every subcommand. If missing, launches the setup wizard. Exceptions: `prism setup` itself, `--help`, `--version`.

## CLI changes

- **Add:** `prism setup [name]` — top-level command
- **Add:** `prism setup --list` — list targets, show default
- **Add:** `prism setup --show <name>` — show target config
- **Remove:** entire `prism remote` group
- **Keep:** `prism init --target <name>` references saved targets

## sites.py changes

Rename `partitions` to `node_types`. Add `qos_options` and `container_runtimes`. Updated Perlmutter defaults based on NERSC documentation:

```python
"perlmutter": {
    "hostname_patterns": ["perlmutter", "saul"],
    "display_name": "NERSC Perlmutter",
    "backend": "slurm",
    "connection": {"hostname": "perlmutter.nersc.gov"},
    "scheduler": {"container_runtime": "podman-hpc"},
    "node_types": {
        "gpu": {
            "description": "GPU (A100 40GB) — 1,536 nodes, 4 GPUs/node",
            "constraint": "gpu",
            "container_flags": ["--gpu"],
        },
        "gpu_hbm80": {
            "description": "GPU (A100 80GB) — 256 nodes, 4 GPUs/node",
            "constraint": "gpu&hbm80g",
            "container_flags": ["--gpu"],
        },
        "cpu": {
            "description": "CPU only — 3,072 nodes, 128 cores/node",
            "constraint": "cpu",
            "container_flags": [],
        },
    },
    "qos_options": {
        "regular":  {"description": "Standard priority, max 48h", "default": True},
        "debug":    {"description": "Quick tests, max 30min, 8 nodes max"},
        "shared":   {"description": "Fractional GPU (1-2 GPUs), max 48h"},
        "preempt":  {"description": "0.25x cost, can be preempted after 2h"},
    },
    "container_runtimes": ["podman-hpc", "shifter"],
    "resource_limits": {
        "max_nodes": 4,
        "max_walltime_minutes": 360,
        "max_concurrent_jobs": 8,
        "max_node_hours_per_session": 64,
    },
}
```

## Testing

- Unit tests for the setup wizard (mocked prompts)
- Test auto-trigger behavior (missing config -> wizard runs)
- Test auto-trigger exceptions (setup, help, version skip check)
- Test constraint auto-derivation from node type
- Update existing site tests for renamed fields
- Test user-level config read/write
- Test project-level override takes precedence
