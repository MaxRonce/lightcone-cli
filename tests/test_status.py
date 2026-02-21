"""Tests for materialization status queries."""
from __future__ import annotations
from pathlib import Path
import pytest
from prism.dagster.status import get_output_status


class TestOutputStatus:
    def test_no_results_dir(self, tmp_path):
        """Status should show 'not run' when no results exist."""
        asp_yaml = tmp_path / "asp.yaml"
        asp_yaml.write_text("""
version: "1.0"
name: test
inputs: []
outputs:
  - id: result
    type: metric
    recipe:
      command: python run.py
""")
        status = get_output_status(tmp_path, "baseline")
        assert status["result"] == "not_run"

    def test_results_exist(self, tmp_path):
        """Status should show 'materialized' when output files exist."""
        asp_yaml = tmp_path / "asp.yaml"
        asp_yaml.write_text("""
version: "1.0"
name: test
inputs: []
outputs:
  - id: result
    type: metric
    recipe:
      command: python run.py
""")
        result_dir = tmp_path / "results" / "baseline" / "result"
        result_dir.mkdir(parents=True)
        (result_dir / "output.json").write_text("{}")
        status = get_output_status(tmp_path, "baseline")
        assert status["result"] == "materialized"
