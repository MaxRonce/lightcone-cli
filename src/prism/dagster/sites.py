"""Known HPC site defaults for target configuration.

When ``prism remote setup`` detects a known hostname, it auto-populates
scheduler settings with site-specific defaults (container runtime,
partitions, constraints, etc.).  Users can override any value during the
interactive wizard.

To add a new site, append an entry to ``SITE_DEFAULTS``.
"""
from __future__ import annotations

from typing import Any

# Each entry maps a site key to its defaults.  The ``hostname_patterns``
# list is used to auto-detect the site from user-provided hostnames.
# The ``guidance`` field is appended to the project CLAUDE.md so the
# agent knows how to work with the site.
SITE_DEFAULTS: dict[str, dict[str, Any]] = {
    "perlmutter": {
        "hostname_patterns": ["perlmutter", "saul"],
        "display_name": "NERSC Perlmutter",
        "backend": "slurm",
        "connection": {
            "hostname": "perlmutter.nersc.gov",
        },
        "scheduler": {
            "container_runtime": "podman-hpc",
            "qos": "regular",
        },
        "partitions": {
            "gpu": {
                "constraint": "gpu",
                "container_flags": ["--gpu"],
            },
            "gpu_hbm80": {
                "constraint": "gpu&hbm80g",
                "container_flags": ["--gpu"],
            },
            "cpu": {
                "constraint": "cpu",
                "container_flags": [],
            },
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 360,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 64,
        },
        "guidance": """\
### Target: NERSC Perlmutter

This project is configured to run on **NERSC Perlmutter** via SLURM with `podman-hpc`.

**Running:** `prism run` submits SLURM jobs automatically. No `--target` flag needed (default is set in `prism.yaml`).

**Container images** are automatically built (`podman-hpc build`) and migrated for compute nodes. Scripts run inside containers on compute nodes -- you do not need to install Python packages locally. A local `.venv` is useful for IDE support but `prism run` uses the container image exclusively.

**Monitoring SLURM jobs:**

```bash
prism status
squeue -u $USER
sacct -j <job_id> --format=JobID,State,ExitCode,Elapsed
cat results/.slurm/<output_id>_<universe_id>.out
cat results/.slurm/<output_id>_<universe_id>.err
```

**GPU recipe example:**

```yaml
outputs:
  - id: trained_model
    type: data
    recipe:
      command: python scripts/train.py
      container: ghcr.io/myorg/myanalysis:latest
      resources:
        cpus: 64
        gpus: 4
        memory: 256GB
        time_limit: 2h
```

The `gpus:` field automatically adds `--gpu` to `podman-hpc` and `#SBATCH --gpus=<n>` to the script.

**Common issues:**

| Problem | Solution |
|---------|----------|
| `sbatch: command not found` | Run from a Perlmutter login node |
| MPI performance poor | `prism remote edit perlmutter`, add `--mpi` to container flags |
| NCCL errors on multi-GPU | Add `--nccl` (and optionally `--cuda-mpi`) to container flags |
| Job not found in `prism status` | sacct may lag ~30s after completion |
| SLURM rejects job (no time limit) | Add `resources: { time_limit: 2h }` to recipe |
| `--prior_range` not recognized | Use underscores in argparse: `parser.add_argument('--prior_range')` |
| GPU allocation wasted on CPU work | `prism remote edit perlmutter`, set `partition: cpu` and `constraint: cpu` |
| `prism status` shows "Container: not built" | Expected -- `prism run` builds/migrates automatically on the target |
""",
    },
}


def detect_site(hostname_or_name: str) -> str | None:
    """Detect a known HPC site from a hostname or target name.

    Returns the site key (e.g. ``"perlmutter"``) or ``None`` if no match.
    """
    normalized = hostname_or_name.lower()
    for site_key, site in SITE_DEFAULTS.items():
        if site_key in normalized:
            return site_key
        for pattern in site.get("hostname_patterns", []):
            if pattern in normalized:
                return site_key
    return None


def get_site_defaults(site_key: str) -> dict[str, Any] | None:
    """Return defaults for a known site, or ``None``."""
    return SITE_DEFAULTS.get(site_key)


def get_site_guidance(site_key: str) -> str | None:
    """Return the CLAUDE.md guidance text for a known site, or ``None``."""
    site = SITE_DEFAULTS.get(site_key)
    if site is None:
        return None
    return site.get("guidance")


def list_known_sites() -> list[tuple[str, str]]:
    """Return list of (site_key, display_name) for all known sites."""
    return [
        (key, site.get("display_name", key))
        for key, site in SITE_DEFAULTS.items()
    ]
