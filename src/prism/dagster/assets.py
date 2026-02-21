"""Asset factory — generates Dagster assets from asp.yaml output recipes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import dagster as dg
except ImportError:
    raise ImportError(
        "Dagster is not installed. Install with: pip install prism[dagster]"
    )

from asp.helpers import get_outputs, load_yaml

from prism.dagster.runner import ASPContainerRunner


def build_asset_definitions(
    project_path: Path,
    runner: ASPContainerRunner | None = None,
) -> list[dg.AssetsDefinition]:
    """Read asp.yaml and generate one @asset per output with a recipe."""
    spec = load_yaml(project_path / "asp.yaml")
    outputs = get_outputs(spec)

    assets: list[dg.AssetsDefinition] = []
    for output_def in outputs:
        output_id = output_def.get("id")
        recipe = output_def.get("recipe")
        if not output_id or not recipe:
            continue
        assets.append(_build_single_asset(output_id, recipe, runner))

    return assets


def _build_single_asset(
    output_id: str,
    recipe: dict[str, Any],
    runner: ASPContainerRunner | None = None,
) -> dg.AssetsDefinition:
    """Build a single Dagster asset from an output recipe."""
    input_ids = recipe.get("inputs") or []
    command = recipe["command"]
    container = recipe.get("container")
    resources = recipe.get("resources") or {}

    @dg.asset(
        name=output_id,
        deps=[dg.AssetKey(i) for i in input_ids],
        metadata={
            "command": command,
            "container": container or "default",
        },
    )
    def _asset(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
        universe_id = "baseline"  # TODO: from partition key when partitions are wired
        result = runner.execute(
            command=command,
            container=container,
            inputs=input_ids,
            output_id=output_id,
            universe_id=universe_id,
            resources=resources,
        )
        return dg.MaterializeResult(
            metadata={
                "exit_code": result.exit_code,
                "output_path": str(result.output_path),
                **result.metadata,
            }
        )

    return _asset


def build_definitions(
    project_path: Path,
    target: str | None = None,
) -> dg.Definitions:
    """Build complete Dagster Definitions from an ASP project.

    This is the main entry point for the Dagster integration.
    """
    from prism.dagster.targets import load_target

    spec = load_yaml(project_path / "asp.yaml")
    default_container = spec.get("container")

    # Build runner from target config
    if target:
        target_config = load_target(target)
        if target_config is None:
            raise ValueError(f"Unknown target: {target}")
        runner = ASPContainerRunner(
            project_root=str(project_path),
            backend=target_config.get("backend", "docker"),
            default_container=default_container,
            target_config=target_config,
        )
    else:
        runner = ASPContainerRunner(
            project_root=str(project_path),
            backend="docker",
            default_container=default_container,
        )

    assets = build_asset_definitions(project_path, runner=runner)

    return dg.Definitions(assets=assets)
