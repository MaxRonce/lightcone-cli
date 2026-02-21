"""Tests for Dagster target configuration."""
from __future__ import annotations
from pathlib import Path
import pytest
from prism.dagster.targets import (
    list_targets,
    load_target,
    save_target,
)


@pytest.fixture
def targets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    targets = tmp_path / "targets"
    targets.mkdir()
    monkeypatch.setattr("prism.dagster.targets.get_targets_dir", lambda: targets)
    return targets


@pytest.fixture
def sample_target() -> dict:
    return {
        "name": "perlmutter",
        "backend": "slurm",
        "connection": {
            "hostname": "perlmutter.nersc.gov",
            "username": "testuser",
        },
        "scheduler": {
            "account": "m1234",
            "partition": "gpu",
            "container_runtime": "shifter",
        },
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 240,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 32,
        },
    }


class TestTargetConfig:
    def test_save_then_load(self, targets_dir, sample_target):
        save_target("perlmutter", sample_target)
        loaded = load_target("perlmutter")
        assert loaded is not None
        assert loaded["backend"] == "slurm"
        assert loaded["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_load_nonexistent(self, targets_dir):
        assert load_target("nonexistent") is None

    def test_list_empty(self, targets_dir):
        assert list_targets() == []

    def test_list_with_targets(self, targets_dir, sample_target):
        save_target("perlmutter", sample_target)
        save_target("other", {"name": "other", "backend": "slurm"})
        assert list_targets() == ["other", "perlmutter"]
