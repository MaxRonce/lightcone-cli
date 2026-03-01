"""Tests for compute profile resolution."""
from pathlib import Path
from typing import Any

import pytest
import yaml

from prism.dagster.profiles import load_profiles, resolve_profile


@pytest.fixture
def prism_yaml(tmp_path: Path) -> Path:
    content = {
        "profiles": {
            "default": {"site": "perlmutter"},
            "debug": {
                "site": "perlmutter",
                "qos": "debug",
                "nodes": 1,
                "time_limit": "30m",
            },
            "production": {
                "site": "perlmutter",
                "qos": "regular",
                "nodes": 8,
                "time_limit": "6h",
                "constraint": "gpu&hbm80g",
            },
        }
    }
    path = tmp_path / "prism.yaml"
    path.write_text(yaml.dump(content, sort_keys=False))
    return path


@pytest.fixture
def site_config() -> dict[str, Any]:
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


class TestLoadProfiles:
    def test_load_profiles(self, prism_yaml):
        profiles = load_profiles(prism_yaml.parent)
        assert "default" in profiles
        assert "debug" in profiles
        assert "production" in profiles

    def test_load_profiles_no_file(self, tmp_path):
        profiles = load_profiles(tmp_path)
        assert profiles == {}

    def test_load_profiles_no_profiles_key(self, tmp_path):
        (tmp_path / "prism.yaml").write_text("target: perlmutter\n")
        profiles = load_profiles(tmp_path)
        assert profiles == {}


class TestResolveProfile:
    def test_default_profile_inherits_site_defaults(self, site_config):
        profile = {"site": "perlmutter"}
        merged = resolve_profile(profile, site_config)
        assert merged["backend"] == "slurm"
        assert merged["qos"] == "debug"
        assert merged["nodes"] == 1
        assert merged["constraint"] == "gpu"
        assert merged["account"] == "m1234"
        assert merged["container_runtime"] == "podman-hpc"

    def test_profile_overrides_site_defaults(self, site_config):
        profile = {
            "site": "perlmutter",
            "qos": "regular",
            "nodes": 8,
            "time_limit": "6h",
        }
        merged = resolve_profile(profile, site_config)
        assert merged["qos"] == "regular"
        assert merged["nodes"] == 8
        assert merged["time_limit"] == "6h"
        assert merged["constraint"] == "gpu"

    def test_profile_overrides_constraint(self, site_config):
        profile = {
            "site": "perlmutter",
            "constraint": "gpu&hbm80g",
        }
        merged = resolve_profile(profile, site_config)
        assert merged["constraint"] == "gpu&hbm80g"

    def test_connection_preserved(self, site_config):
        profile = {"site": "perlmutter"}
        merged = resolve_profile(profile, site_config)
        assert merged["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_local_site_profile(self):
        local_site = {
            "site": "local",
            "backend": "local",
        }
        profile = {"site": "local"}
        merged = resolve_profile(profile, local_site)
        assert merged["backend"] == "local"
