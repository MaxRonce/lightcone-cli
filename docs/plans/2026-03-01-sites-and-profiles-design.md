# Design: Sites and Compute Profiles

## Summary

Replace the single "target" concept with a two-layer model: **sites** (user-level, where you run) and **compute profiles** (project-level, how much resources you want). Remove the "Custom" site option; add a built-in "local" site for laptop execution.

## The Two-Layer Model

**Sites** (user-level, `~/.prism/sites/<name>.yaml`) — configured once per machine:
- Credentials: account, username, hostname
- Container runtime (podman-hpc, shifter)
- Default minimal resources (node type, QOS, nodes, time limit)
- `local` is built-in (subprocess execution, no scheduler, no config file)

**Compute Profiles** (project-level, `prism.yaml`) — defined per project:
- References a site by name
- Overrides site defaults with larger/different resource values
- A project always has at least a `default` profile

## File Formats

### `~/.prism/config.yaml`

```yaml
default_site: perlmutter
```

### `~/.prism/sites/perlmutter.yaml`

```yaml
site: perlmutter
backend: slurm
connection:
  hostname: perlmutter.nersc.gov
  username: francois
account: m1234
container_runtime: podman-hpc
defaults:
  node_type: gpu
  constraint: gpu
  qos: debug
  nodes: 1
  time_limit: 30m
```

### Built-in `local` site (in code, no file)

```python
"local": {
    "display_name": "Local",
    "backend": "local",
}
```

### Project `prism.yaml`

```yaml
profiles:
  default:
    site: perlmutter

  debug:
    site: perlmutter
    qos: debug
    nodes: 1
    time_limit: 30m

  production:
    site: perlmutter
    qos: regular
    nodes: 8
    time_limit: 6h
    constraint: "gpu&hbm80g"
```

## Resolution

When `prism run --profile production` executes:

1. Load `production` profile from `prism.yaml`
2. Load `perlmutter` site from `~/.prism/sites/perlmutter.yaml`
3. Merge: profile values override site defaults
4. Build runner with merged config

If no `--profile` flag: use `default` profile. If no `default` profile: use default site's minimal resources.

## CLI Commands

| Command | Purpose |
|---|---|
| `prism setup` | Configure sites (interactive wizard) |
| `prism setup --list` | List configured sites, show default |
| `prism setup --default <name>` | Change default site |
| `prism profiles` | List profiles for current project |
| `prism profiles add <name>` | Create a new profile interactively |
| `prism run [--profile <name>]` | Run with a profile (default: `default`) |
| `prism init` | Create project, asks about compute profile |

## `prism setup` Wizard

Same as current implementation but:
- No "Custom" option — only known HPC sites
- `local` is always available (built-in, no setup needed)
- Site config includes `defaults` section with minimal resources
- `prism setup --default <name>` to switch default site

## `prism profiles` Output

```
$ prism profiles

  my-analysis — Compute Profiles

  PROFILE      SITE         QOS       NODES  TIME
  default      perlmutter   debug     1      30m
  debug        perlmutter   debug     1      30m
  production   perlmutter   regular   8      6h

  Use: prism run --profile <name>
```

## `prism profiles add <name>` Wizard

```
$ prism profiles add production

  Site [perlmutter]:
  QOS:
    1. regular — Standard priority, max 48h
    2. debug — Quick tests, max 30min
  Select QOS [1]: 1
  Nodes [1]: 8
  Time limit [30m]: 6h

  Added profile 'production' to prism.yaml
```

## `prism init` Change

After creating project structure, asks:
- "Use default site's minimal resources, or create a custom profile?"
- If default: writes `profiles: { default: { site: <default_site> } }`
- If custom: runs profile add wizard

## What Changes From Current

- `~/.prism/targets/` -> `~/.prism/sites/`
- `target` concept -> `site` + `profile`
- `prism run --target X` -> `prism run --profile X`
- `prism.yaml` format: `target: X` -> `profiles: { ... }`
- `runner.py`: add `backend: "local"` as first-class (currently a fallback)
- `build_definitions`: accept site + profile instead of target config

## What Stays The Same

- `prism setup` auto-triggers on first use
- Sites stored in `~/.prism/`
- `sites.py` SITE_DEFAULTS (node_types, qos_options)
- Runner's slurm/docker execution logic
