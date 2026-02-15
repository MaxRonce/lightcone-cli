"""Target configuration management for HPC/remote environments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_targets_dir() -> Path:
    """Return the user-level targets directory (~/.prism/targets/)."""
    return Path.home() / ".prism" / "targets"


def list_saved_targets() -> list[str]:
    """Return names of saved target configurations."""
    targets_dir = get_targets_dir()
    if not targets_dir.exists():
        return []
    return sorted(p.stem for p in targets_dir.glob("*.yaml"))


def load_target_config(name: str) -> dict[str, Any] | None:
    """Load a saved target configuration by name.

    Returns None if the target config doesn't exist.
    """
    config_path = get_targets_dir() / f"{name}.yaml"
    if not config_path.exists():
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def save_target_config(name: str, config: dict[str, Any]) -> Path:
    """Save a target configuration to ~/.prism/targets/{name}.yaml.

    Returns the path where it was saved.
    """
    targets_dir = get_targets_dir()
    targets_dir.mkdir(parents=True, exist_ok=True)
    config_path = targets_dir / f"{name}.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path


def merge_permissions_into_settings(
    settings: dict[str, Any], target_config: dict[str, Any]
) -> None:
    """Add target permissions to a Claude Code settings.json structure.

    Modifies settings in place.
    """
    permissions = target_config.get("permissions", {})

    if "permissions" not in settings:
        settings["permissions"] = {}

    allow_list: list[str] = settings["permissions"].get("allow", [])
    deny_list: list[str] = settings["permissions"].get("deny", [])

    # Add auto-approve commands as Bash permissions
    for cmd in permissions.get("auto_approve", []):
        entry = f"Bash({cmd}:*)"
        if entry not in allow_list:
            allow_list.append(entry)

    settings["permissions"]["allow"] = allow_list

    # Add deny patterns
    for cmd in permissions.get("deny", []):
        entry = f"Bash({cmd})"
        if entry not in deny_list:
            deny_list.append(entry)

    if deny_list:
        settings["permissions"]["deny"] = deny_list


def create_project_hpc_config(
    target_config: dict[str, Any], overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a project-level HPC config dict from a target config.

    The project config is a subset of the full target config, focused on
    what's needed at runtime (resource limits, auth, compute settings).

    Args:
        target_config: The full target configuration.
        overrides: Optional overrides for resource_limits or compute settings.
    """
    config: dict[str, Any] = {
        "target": target_config.get("target", {}),
        "auth": target_config.get("auth", {}),
        "compute": target_config.get("compute", {}),
        "resource_limits": target_config.get("resource_limits", {}),
    }

    # Include notes if present
    if target_config.get("notes"):
        config["notes"] = target_config["notes"]

    if overrides:
        for section in ("resource_limits", "compute"):
            if section in overrides:
                config[section].update(overrides[section])

    return config
