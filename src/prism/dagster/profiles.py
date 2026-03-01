"""Compute profile resolution — merges site defaults with project overrides."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_profiles(project_path: Path) -> dict[str, dict[str, Any]]:
    """Load compute profiles from prism.yaml.

    Returns an empty dict if prism.yaml doesn't exist or has no profiles key.
    """
    prism_yaml = project_path / "prism.yaml"
    if not prism_yaml.exists():
        return {}
    with open(prism_yaml) as f:
        data = yaml.safe_load(f) or {}
    return data.get("profiles", {})


def resolve_profile(
    profile: dict[str, Any],
    site_config: dict[str, Any],
) -> dict[str, Any]:
    """Merge a profile with its site config.

    Site-level fields provide the base. Profile values override site defaults.
    Returns a flat dict with all fields needed to build a runner.
    """
    site_defaults = site_config.get("defaults", {})

    merged: dict[str, Any] = {}

    # Copy site-level fields
    merged["backend"] = site_config.get("backend", "local")
    merged["connection"] = site_config.get("connection", {})
    merged["account"] = site_config.get("account")
    merged["container_runtime"] = site_config.get("container_runtime")

    # Apply site defaults
    for key in ("node_type", "constraint", "qos", "nodes", "time_limit"):
        if key in site_defaults:
            merged[key] = site_defaults[key]

    # Profile overrides
    for key, value in profile.items():
        if key == "site":
            continue
        merged[key] = value

    return merged
