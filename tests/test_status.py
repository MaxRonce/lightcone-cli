"""Tests for materialization status queries."""
from __future__ import annotations

from prism.dagster.status import get_all_universe_status, get_output_status


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


class TestAllUniverseStatus:
    def test_no_universes_dir(self, tmp_path):
        """Should return empty dict when no universes directory exists."""
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
        result = get_all_universe_status(tmp_path)
        assert result == {}

    def test_multiple_universes(self, tmp_path):
        """Should return status for each universe YAML file."""
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
        universes_dir = tmp_path / "universes"
        universes_dir.mkdir()
        (universes_dir / "baseline.yaml").write_text(
            'id: baseline\ndecisions: {}\n'
        )
        (universes_dir / "alt.yaml").write_text(
            'id: alt\ndecisions: {}\n'
        )
        # Materialize result for baseline only
        result_dir = tmp_path / "results" / "baseline" / "result"
        result_dir.mkdir(parents=True)
        (result_dir / "output.json").write_text("{}")

        result = get_all_universe_status(tmp_path)
        assert "baseline" in result
        assert "alt" in result
        assert result["baseline"]["result"] == "materialized"
        assert result["alt"]["result"] == "not_run"
