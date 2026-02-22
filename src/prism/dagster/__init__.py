"""Dagster execution layer for Prism.

Provides:
- build_definitions(): Generate Dagster Definitions from asp.yaml
- ASPContainerRunner: Execute recipes in Docker/SLURM containers
- ASPIOManager: Map (asset, universe) to filesystem paths
- get_output_status(): Query materialization status
"""
from prism.dagster.io_manager import ASPIOManager
from prism.dagster.runner import (
    ASPContainerRunner,
    generate_sbatch_script,
    translate_resources_to_slurm_directives,
)
from prism.dagster.status import get_all_universe_status, get_output_status
from prism.dagster.targets import list_targets, load_target, save_target

__all__ = [
    "ASPContainerRunner",
    "ASPIOManager",
    "build_asset_definitions",
    "build_definitions",
    "generate_sbatch_script",
    "get_output_status",
    "get_all_universe_status",
    "list_targets",
    "load_target",
    "save_target",
    "translate_resources_to_slurm_directives",
]


def build_definitions(*args, **kwargs):
    """Build Dagster Definitions from asp.yaml. Requires dagster to be installed."""
    from prism.dagster.assets import build_definitions as _build
    return _build(*args, **kwargs)


def build_asset_definitions(*args, **kwargs):
    """Build asset definitions from asp.yaml. Requires dagster to be installed."""
    from prism.dagster.assets import build_asset_definitions as _build
    return _build(*args, **kwargs)
