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

from prism.container import resolve_container_spec
from prism.dagster.runner import ASPContainerRunner


def build_asset_definitions(
    spec: dict[str, Any],
    runner: ASPContainerRunner | None = None,
    universe_id: str = "baseline",
    project_path: Path | None = None,
    project_name: str | None = None,
    no_build: bool = False,
) -> list[dg.AssetsDefinition]:
    """Generate one @asset per output with a recipe."""
    outputs = get_outputs(spec)

    # Resolve analysis-level container spec once.
    raw_default = spec.get("container")
    if raw_default is not None and not no_build:
        _name = project_name or spec.get("name") or "project"
        _path = project_path or Path.cwd()
        default_container = resolve_container_spec(raw_default, _path, _name)
    else:
        default_container = raw_default if isinstance(raw_default, str) else None

    assets: list[dg.AssetsDefinition] = []
    for output_def in outputs:
        output_id = output_def.get("id")
        recipe = output_def.get("recipe")
        if not output_id or not recipe:
            continue
        assets.append(
            _build_single_asset(
                output_id, recipe, runner, universe_id, project_path,
                project_name=project_name, default_container=default_container,
                no_build=no_build,
            )
        )

    return assets


def _load_universe_params(
    project_path: Path | None, universe_id: str
) -> dict[str, Any]:
    """Load universe decisions as params dict."""
    if project_path is None:
        return {}
    universe_file = project_path / "universes" / f"{universe_id}.yaml"
    if not universe_file.exists():
        return {}
    universe_data = load_yaml(universe_file)
    return universe_data.get("decisions", {})


def _build_single_asset(
    output_id: str,
    recipe: dict[str, Any],
    runner: ASPContainerRunner | None = None,
    universe_id: str = "baseline",
    project_path: Path | None = None,
    project_name: str | None = None,
    default_container: str | None = None,
    no_build: bool = False,
) -> dg.AssetsDefinition:
    """Build a single Dagster asset from an output recipe."""
    input_ids = recipe.get("inputs") or []
    command = recipe["command"]
    raw_container = recipe.get("container")
    # Resolve per-recipe container spec; fall back to analysis-level default.
    if raw_container is not None and not no_build:
        _name = project_name or "project"
        _path = project_path or Path.cwd()
        container = resolve_container_spec(raw_container, _path, _name)
    elif raw_container is not None and isinstance(raw_container, str):
        container = raw_container
    else:
        container = default_container
    resources = recipe.get("resources") or {}

    @dg.asset(
        name=output_id,
        deps=[dg.AssetKey(i) for i in input_ids],
        metadata={
            "command": command,
            "container": container or "default",
        },
    )
    def _asset(context) -> dg.MaterializeResult:
        params = _load_universe_params(project_path, universe_id)
        result = runner.execute(
            command=command,
            container=container,
            inputs=input_ids,
            output_id=output_id,
            universe_id=universe_id,
            resources=resources,
            params=params,
        )
        if result.metadata.get("stdout"):
            context.log.info(result.metadata["stdout"])
        if result.exit_code != 0:
            stderr = result.metadata.get("stderr", "")
            raise RuntimeError(
                f"Recipe for '{output_id}' failed (exit code {result.exit_code})"
                f"{': ' + stderr if stderr else ''}"
            )
        return dg.MaterializeResult(
            metadata={
                "exit_code": result.exit_code,
                "output_path": str(result.output_path),
                "backend": result.metadata.get("backend", "unknown"),
            }
        )

    return _asset


def build_definitions(
    project_path: Path,
    target: str | None = None,
    universe_id: str = "baseline",
    no_build: bool = False,
) -> dg.Definitions:
    """Build complete Dagster Definitions from an ASP project.

    This is the main entry point for the Dagster integration.
    """
    from prism.dagster.targets import load_target

    spec = load_yaml(project_path / "asp.yaml")
    project_name = spec.get("name") or project_path.name

    # Resolve analysis-level container spec to a string for the runner.
    raw_container = spec.get("container")
    if not no_build:
        default_container = resolve_container_spec(
            raw_container, project_path, project_name
        )
    else:
        default_container = raw_container if isinstance(raw_container, str) else None

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

    assets = build_asset_definitions(
        spec, runner=runner, universe_id=universe_id, project_path=project_path,
        project_name=project_name, no_build=no_build,
    )

    return dg.Definitions(assets=assets)
