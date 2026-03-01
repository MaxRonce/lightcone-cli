"""Tests for Dagster target configuration."""
from __future__ import annotations

from pathlib import Path

import pytest

from prism.dagster.targets import (
    get_config_path,
    list_targets,
    load_target,
    load_user_config,
    save_target,
    save_user_config,
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


class TestUserConfig:
    def test_load_missing_returns_empty(self, targets_dir, monkeypatch):
        config_path = targets_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        assert load_user_config() == {}

    def test_save_and_load_default_target(self, targets_dir, monkeypatch):
        config_path = targets_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        save_user_config({"default_target": "perlmutter"})
        config = load_user_config()
        assert config["default_target"] == "perlmutter"

    def test_config_path_is_in_prism_dir(self):
        path = get_config_path()
        assert path.name == "config.yaml"
        assert ".prism" in str(path)
