"""Shared test fixtures for Prism tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def targets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override the targets directory to use a temp path."""
    targets = tmp_path / "targets"
    targets.mkdir()
    monkeypatch.setattr("prism.remote.get_targets_dir", lambda: targets)
    return targets


@pytest.fixture
def sample_config() -> dict:
    """A typical target config for testing."""
    return {
        "target": {
            "name": "perlmutter",
            "scheduler": "slurm",
        },
        "auth": {
            "account": "m9999",
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 120,
            "max_concurrent_jobs": 3,
            "max_node_hours_per_session": 16,
        },
        "permissions": {
            "auto_approve": ["python", "python3", "squeue", "sacct"],
            "deny": ["rm -rf /", "scancel --all"],
        },
    }
