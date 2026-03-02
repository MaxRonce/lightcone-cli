"""Tests for ASP asset factory."""
from __future__ import annotations

import unittest.mock
from unittest.mock import MagicMock

import dagster as dg
import pytest
from asp.helpers import load_yaml

from prism.dagster.assets import build_asset_definitions, build_definitions


@pytest.fixture
def mock_runner():
    """Create a mock ASPContainerRunner."""
    return MagicMock()


@pytest.fixture
def sample_asp_yaml(tmp_path):
    """Create a sample asp.yaml with inline recipes."""
    asp_yaml = tmp_path / "asp.yaml"
    asp_yaml.write_text("""
version: "1.0"
name: "Test Analysis"
inputs:
  - id: raw_data
    type: data
outputs:
  - id: cleaned
    type: data
    recipe:
      command: python clean.py
      container: test:latest
  - id: result
    type: metric
    recipe:
      command: python analyze.py
      inputs: [cleaned]
      container: test:latest
  - id: external
    type: data
decisions: {}
""")
    return tmp_path


class TestBuildAssetDefinitions:
    def test_generates_assets_for_outputs_with_recipes(
        self, sample_asp_yaml, mock_runner,
    ):
        spec = load_yaml(sample_asp_yaml / "asp.yaml")
        assets = build_asset_definitions(spec, runner=mock_runner)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "cleaned" in asset_keys
        assert "result" in asset_keys

    def test_skips_outputs_without_recipes(
        self, sample_asp_yaml, mock_runner,
    ):
        spec = load_yaml(sample_asp_yaml / "asp.yaml")
        assets = build_asset_definitions(spec, runner=mock_runner)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "external" not in asset_keys

    def test_asset_dependencies(self, sample_asp_yaml, mock_runner):
        spec = load_yaml(sample_asp_yaml / "asp.yaml")
        assets = build_asset_definitions(spec, runner=mock_runner)
        result_asset = next(a for a in assets if a.key.path[-1] == "result")
        # Check dependencies via specs
        dep_keys = set()
        for spec_item in result_asset.specs:
            for dep in spec_item.deps:
                dep_keys.add(dep.asset_key.path[-1])
        assert "cleaned" in dep_keys

    def test_build_definitions_returns_definitions(self, sample_asp_yaml):
        defs = build_definitions(sample_asp_yaml)
        assert isinstance(defs, dg.Definitions)

    def test_container_flags_forwarded_to_runner(self, sample_asp_yaml):
        """container_flags from target config should reach the runner's scheduler config."""
        target_config = {
            "backend": "slurm",
            "account": "m1234",
            "container_runtime": "podman-hpc",
            "container_flags": ["--scratch", "--cfs"],
        }
        with unittest.mock.patch(
            "prism.dagster.assets.ASPContainerRunner",
        ) as MockRunner:
            build_definitions(
                sample_asp_yaml, target_config=target_config, no_build=True,
            )
            call_kwargs = MockRunner.call_args[1]
            scheduler = call_kwargs["target_config"]["scheduler"]
            assert scheduler["container_flags"] == ["--scratch", "--cfs"]

    def test_build_spec_resolved_to_string(self, tmp_path, mock_runner):
        """Container build specs should be resolved to tag strings."""
        containerfile = tmp_path / "Containerfile"
        containerfile.write_text("FROM python:3.12-slim\n")

        spec = {
            "name": "Test",
            "container": {"build": "Containerfile"},
            "outputs": [
                {
                    "id": "result",
                    "type": "metric",
                    "recipe": {"command": "python run.py"},
                },
            ],
        }

        with unittest.mock.patch(
            "prism.container.image_exists_locally", return_value=True,
        ):
            assets = build_asset_definitions(
                spec,
                runner=mock_runner,
                project_path=tmp_path,
                project_name="Test",
            )

        assert len(assets) == 1
        # The container metadata should be a resolved tag string, not a dict
        for asset_spec in assets[0].specs:
            meta = asset_spec.metadata or {}
            container_val = meta.get("container", "")
            assert isinstance(container_val, str)
            assert "build" not in container_val  # not the raw dict
