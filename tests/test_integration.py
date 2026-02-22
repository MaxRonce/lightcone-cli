"""Integration tests for the Dagster execution layer."""

import pytest
from click.testing import CliRunner

from prism.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(tmp_path, runner):
    """Create a project with init, then add inline recipes."""
    project = tmp_path / "test-project"
    runner.invoke(main, ["init", str(project), "--no-git", "--no-venv"])

    # Overwrite asp.yaml with recipes
    (project / "asp.yaml").write_text("""
version: "1.0"
name: "Integration Test"
inputs:
  - id: raw_data
    type: data
outputs:
  - id: cleaned
    type: data
    recipe:
      command: python scripts/clean.py
      container: python:3.11
  - id: result
    type: metric
    recipe:
      command: python scripts/analyze.py
      inputs: [cleaned]
      container: python:3.11
decisions: {}
""")
    return project


class TestIntegration:
    def test_init_creates_dagster_yaml(self, project_dir):
        assert (project_dir / "dagster.yaml").exists()

    def test_init_creates_project_structure(self, project_dir):
        assert (project_dir / "asp.yaml").exists()
        assert (project_dir / "universes").is_dir()
        assert (project_dir / "results").is_dir()
        assert (project_dir / "scripts").is_dir()

    def test_status_shows_pending(self, project_dir):
        """Status should show 'pending' when nothing has been materialized."""
        # Ensure a universe exists
        (project_dir / "universes" / "baseline.yaml").write_text(
            "id: baseline\ndecisions: {}\n"
        )
        from prism.dagster.status import get_output_status

        status = get_output_status(project_dir, "baseline")
        assert status["cleaned"] == "pending"
        assert status["result"] == "pending"

    def test_status_shows_materialized(self, project_dir):
        """Status should show 'materialized' when output files exist."""
        (project_dir / "universes" / "baseline.yaml").write_text(
            "id: baseline\ndecisions: {}\n"
        )
        # Simulate materialized output
        result_dir = project_dir / "results" / "baseline" / "cleaned"
        result_dir.mkdir(parents=True)
        (result_dir / "data.csv").write_text("col1,col2\n1,2\n")

        from prism.dagster.status import get_output_status

        status = get_output_status(project_dir, "baseline")
        assert status["cleaned"] == "materialized"
        assert status["result"] == "pending"

    def test_status_cli_output(self, project_dir, runner, monkeypatch):
        """prism status should run without error."""
        monkeypatch.chdir(project_dir)
        (project_dir / "universes" / "baseline.yaml").write_text(
            "id: baseline\ndecisions: {}\n"
        )
        result = runner.invoke(main, ["status", "--universe", "baseline"])
        assert result.exit_code == 0
        assert "cleaned" in result.output or "pending" in result.output

    def test_target_save_and_load(self, tmp_path, monkeypatch):
        """Target config round-trip."""
        targets = tmp_path / "targets"
        targets.mkdir()
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir", lambda: targets)

        from prism.dagster.targets import list_targets, load_target, save_target

        save_target("test-target", {
            "name": "test-target",
            "backend": "docker",
        })

        loaded = load_target("test-target")
        assert loaded is not None
        assert loaded["backend"] == "docker"
        assert list_targets() == ["test-target"]

    def test_io_manager_paths(self, project_dir):
        """IO manager should produce correct paths."""
        from prism.dagster.io_manager import ASPIOManager

        mgr = ASPIOManager(project_root=str(project_dir))
        path = mgr.get_output_path("cleaned", "baseline")
        assert path == project_dir / "results" / "baseline" / "cleaned"

    def test_runner_builds_docker_command(self, project_dir):
        """Runner should build valid Docker commands."""
        from prism.dagster.runner import ASPContainerRunner

        runner = ASPContainerRunner(
            project_root=str(project_dir),
            backend="docker",
        )
        cmd = runner.build_docker_command(
            command="python scripts/clean.py",
            container="python:3.11",
            input_ids=[],
            output_id="cleaned",
            universe_id="baseline",
            resources={},
        )
        assert "docker" in cmd[0]
        assert "python:3.11" in cmd
        assert "python scripts/clean.py" in " ".join(cmd)
