"""Materialization status queries for ASP outputs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from asp.helpers import load_yaml, get_outputs


def get_output_status(
    project_path: Path,
    universe_id: str,
) -> dict[str, str]:
    """Get materialization status for all outputs in a universe.

    Returns dict mapping output_id to status string:
    - "materialized": output directory exists and contains files
    - "not_run": output directory doesn't exist or is empty
    """
    spec = load_yaml(project_path / "asp.yaml")
    outputs = get_outputs(spec)

    status: dict[str, str] = {}
    for out in outputs:
        out_id = out.get("id")
        if not out_id:
            continue
        if not out.get("recipe"):
            continue
        output_path = project_path / "results" / universe_id / out_id
        if output_path.exists() and any(output_path.iterdir()):
            status[out_id] = "materialized"
        else:
            status[out_id] = "not_run"

    return status


def get_all_universe_status(
    project_path: Path,
) -> dict[str, dict[str, str]]:
    """Get status for all universes.

    Returns dict mapping universe_id to output status dict.
    """
    universes_dir = project_path / "universes"
    if not universes_dir.exists():
        return {}

    result: dict[str, dict[str, str]] = {}
    for universe_file in sorted(universes_dir.glob("*.yaml")):
        universe_data = load_yaml(universe_file)
        universe_id = universe_data.get("id", universe_file.stem)
        result[universe_id] = get_output_status(project_path, universe_id)

    return result
