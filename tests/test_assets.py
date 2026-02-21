"""Tests for ASP asset factory."""
from __future__ import annotations

import pytest

dagster = pytest.importorskip("dagster")

import dagster as dg  # noqa: E402

from prism.dagster.assets import build_asset_definitions, build_definitions  # noqa: E402


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
    def test_generates_assets_for_outputs_with_recipes(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "cleaned" in asset_keys
        assert "result" in asset_keys

    def test_skips_outputs_without_recipes(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        asset_keys = {a.key.path[-1] for a in assets}
        assert "external" not in asset_keys

    def test_asset_dependencies(self, sample_asp_yaml):
        assets = build_asset_definitions(sample_asp_yaml)
        result_asset = next(a for a in assets if a.key.path[-1] == "result")
        # Check dependencies via specs
        dep_keys = set()
        for spec in result_asset.specs:
            for dep in spec.deps:
                dep_keys.add(dep.asset_key.path[-1])
        assert "cleaned" in dep_keys

    def test_build_definitions_returns_definitions(self, sample_asp_yaml):
        defs = build_definitions(sample_asp_yaml)
        assert isinstance(defs, dg.Definitions)
