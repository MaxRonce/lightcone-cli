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
    },
    "cori": {
        "hostname_patterns": ["cori"],
        "display_name": "NERSC Cori (retired)",
        "backend": "slurm",
        "connection": {
            "hostname": "cori.nersc.gov",
        },
        "scheduler": {
            "container_runtime": "shifter",
            "qos": "regular",
        },
        "partitions": {
            "haswell": {
                "constraint": "haswell",
                "container_flags": [],
            },
            "knl": {
                "constraint": "knl",
                "container_flags": [],
            },
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 240,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 32,
        },
    },
    "frontier": {
        "hostname_patterns": ["frontier"],
        "display_name": "OLCF Frontier",
        "backend": "slurm",
        "connection": {
            "hostname": "frontier.olcf.ornl.gov",
        },
        "scheduler": {
            "container_runtime": "singularity",
            "qos": "batch",
        },
        "partitions": {
            "batch": {
                "constraint": "",
                "container_flags": [],
            },
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 120,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 32,
        },
    },
    "polaris": {
        "hostname_patterns": ["polaris"],
        "display_name": "ALCF Polaris",
        "backend": "pbs",
        "connection": {
            "hostname": "polaris.alcf.anl.gov",
        },
        "scheduler": {
            "container_runtime": "singularity",
        },
        "partitions": {
            "default": {
                "constraint": "",
                "container_flags": [],
            },
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 180,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 32,
        },
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


def list_known_sites() -> list[tuple[str, str]]:
    """Return list of (site_key, display_name) for all known sites."""
    return [
        (key, site.get("display_name", key))
        for key, site in SITE_DEFAULTS.items()
    ]
