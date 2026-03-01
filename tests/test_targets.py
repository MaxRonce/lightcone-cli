"""Tests for site and user configuration."""
from __future__ import annotations

from pathlib import Path

import pytest

from prism.dagster.targets import (
    get_config_path,
    list_sites,
    load_site,
    load_user_config,
    save_site,
    save_user_config,
)


@pytest.fixture
def sites_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    sites = tmp_path / "sites"
    sites.mkdir()
    monkeypatch.setattr("prism.dagster.targets.get_sites_dir", lambda: sites)
    return sites


@pytest.fixture
def sample_site() -> dict:
    return {
        "site": "perlmutter",
        "backend": "slurm",
        "connection": {
            "hostname": "perlmutter.nersc.gov",
            "username": "testuser",
        },
        "account": "m1234",
        "container_runtime": "podman-hpc",
        "defaults": {
            "node_type": "gpu",
            "constraint": "gpu",
            "qos": "debug",
            "nodes": 1,
            "time_limit": "30m",
        },
    }


class TestSiteConfig:
    def test_save_then_load(self, sites_dir, sample_site):
        save_site("perlmutter", sample_site)
        loaded = load_site("perlmutter")
        assert loaded is not None
        assert loaded["backend"] == "slurm"
        assert loaded["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_load_nonexistent(self, sites_dir):
        assert load_site("nonexistent") is None

    def test_list_empty(self, sites_dir):
        assert list_sites() == []

    def test_list_with_sites(self, sites_dir, sample_site):
        save_site("perlmutter", sample_site)
        save_site("frontier", {"site": "frontier", "backend": "slurm"})
        assert list_sites() == ["frontier", "perlmutter"]


class TestUserConfig:
    def test_load_missing_returns_empty(self, sites_dir, monkeypatch):
        config_path = sites_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        assert load_user_config() == {}

    def test_save_and_load_default_site(self, sites_dir, monkeypatch):
        config_path = sites_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        save_user_config({"default_site": "perlmutter"})
        config = load_user_config()
        assert config["default_site"] == "perlmutter"

    def test_config_path_is_in_prism_dir(self):
        path = get_config_path()
        assert path.name == "config.yaml"
        assert ".prism" in str(path)
