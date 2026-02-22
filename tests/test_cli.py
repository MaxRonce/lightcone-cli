"""Tests for Prism CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from prism.cli import main


@pytest.fixture
def runner():
    """Return a CLI runner."""
    return CliRunner()


class TestInitCommand:
    """Tests for the prism init command."""

    def test_init_creates_project_structure(self, runner: CliRunner, tmp_path: Path):
        """Test that basic init creates the project structure."""
        project_dir = tmp_path / "my-analysis"
        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
        )
        assert result.exit_code == 0
        assert "Created ASP analysis project" in result.output

        # Check directory structure
        assert (project_dir / "asp.yaml").exists()
        assert (project_dir / ".gitignore").exists()
        assert (project_dir / "universes").is_dir()
        assert (project_dir / "universes" / "baseline.yaml").exists()
        assert (project_dir / "scripts").is_dir()
        assert (project_dir / "results").is_dir()

    def test_init_asp_yaml_content(self, runner: CliRunner, tmp_path: Path):
        """Test that the generated asp.yaml has the expected content."""
        project_dir = tmp_path / "content-test"
        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
        )
        assert result.exit_code == 0

        content = (project_dir / "asp.yaml").read_text()
        assert "content-test" in content
        assert "version:" in content
        assert "name:" in content
        assert "description:" in content
        assert "decisions:" in content

    def test_init_gitignore_content(self, runner: CliRunner, tmp_path: Path):
        """Test gitignore content."""
        project_dir = tmp_path / "gitignore-test"
        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
        )
        assert result.exit_code == 0

        gitignore = (project_dir / ".gitignore").read_text()
        assert "results/" in gitignore
        assert "__pycache__/" in gitignore

    def test_init_refuses_if_asp_yaml_exists(self, runner: CliRunner, tmp_path: Path):
        """Test that init refuses to run in an existing ASP project."""
        project_dir = tmp_path / "already-init"
        runner.invoke(main, ["init", str(project_dir), "--no-git", "--no-venv"])
        assert (project_dir / "asp.yaml").exists()

        result = runner.invoke(main, ["init", str(project_dir), "--no-git", "--no-venv"])
        assert result.exit_code == 1
        assert "already an ASP project" in result.output

    def test_init_existing_nonempty_dir_decline(self, runner: CliRunner, tmp_path: Path):
        """Test declining to overwrite existing non-empty directory."""
        project_dir = tmp_path / "existing"
        project_dir.mkdir()
        (project_dir / "some_file.txt").write_text("existing content")

        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
            input="n\n",
        )
        assert result.exit_code == 0
        assert not (project_dir / "asp.yaml").exists()

    def test_init_existing_nonempty_dir_confirm(self, runner: CliRunner, tmp_path: Path):
        """Test confirming to overwrite existing non-empty directory."""
        project_dir = tmp_path / "existing-confirm"
        project_dir.mkdir()
        (project_dir / "some_file.txt").write_text("existing content")

        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert (project_dir / "asp.yaml").exists()

    def test_init_creates_dagster_yaml(self, runner: CliRunner, tmp_path: Path):
        """Test that init creates dagster.yaml."""
        project_dir = tmp_path / "dagster-test"
        result = runner.invoke(main, ["init", str(project_dir), "--no-git", "--no-venv"])
        assert result.exit_code == 0
        assert (project_dir / "dagster.yaml").exists()


class TestVersionOption:
    """Tests for version option."""

    def test_version(self, runner: CliRunner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output


class TestHelpOption:
    """Tests for help option."""

    def test_help(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Prism" in result.output

    def test_init_help(self, runner: CliRunner):
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0

    def test_remote_help(self, runner: CliRunner):
        result = runner.invoke(main, ["remote", "--help"])
        assert result.exit_code == 0

