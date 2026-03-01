"""Tests for Prism CLI commands."""

from pathlib import Path
from unittest.mock import patch

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

    def test_init_with_site_creates_prism_yaml(self, runner: CliRunner, tmp_path: Path):
        """Test that --site creates prism.yaml with a default profile."""
        project_dir = tmp_path / "site-test"
        with patch("prism.dagster.targets.load_site", return_value={"site": "perlmutter"}):
            result = runner.invoke(
                main,
                ["init", str(project_dir), "--no-git", "--no-venv", "--site", "perlmutter"],
            )
        assert result.exit_code == 0
        assert (project_dir / "prism.yaml").exists()

        import yaml
        config = yaml.safe_load((project_dir / "prism.yaml").read_text())
        assert config["profiles"]["default"]["site"] == "perlmutter"

    def test_init_without_site_no_prism_yaml(self, runner: CliRunner, tmp_path: Path):
        """Test that without --site, no prism.yaml is created."""
        project_dir = tmp_path / "no-site-test"
        result = runner.invoke(
            main,
            ["init", str(project_dir), "--no-git", "--no-venv"],
        )
        assert result.exit_code == 0
        assert not (project_dir / "prism.yaml").exists()

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

    def test_setup_help(self, runner: CliRunner):
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0


class TestSetupCommand:
    """Tests for the prism setup command."""

    def test_setup_help(self, runner: CliRunner):
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0
        assert "site" in result.output.lower() or "Setup" in result.output

    def test_setup_list_empty(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: tmp_path / "sites")
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        result = runner.invoke(main, ["setup", "--list"])
        assert result.exit_code == 0
        assert "no additional sites" in result.output.lower() or "local" in result.output

    def test_setup_list_with_sites(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        sites_dir = tmp_path / "sites"
        sites_dir.mkdir()
        (sites_dir / "perlmutter.yaml").write_text("site: perlmutter\n")
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: sites_dir)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("default_site: perlmutter\n")
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        result = runner.invoke(main, ["setup", "--list"])
        assert result.exit_code == 0
        assert "perlmutter" in result.output

    def test_setup_show(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        sites_dir = tmp_path / "sites"
        sites_dir.mkdir()
        (sites_dir / "perlmutter.yaml").write_text("site: perlmutter\nbackend: slurm\n")
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: sites_dir)
        result = runner.invoke(main, ["setup", "--show", "perlmutter"])
        assert result.exit_code == 0
        assert "slurm" in result.output

    def test_setup_show_nonexistent(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: tmp_path / "sites")
        result = runner.invoke(main, ["setup", "--show", "nonexistent"])
        assert result.exit_code == 1

    def test_setup_wizard_known_site(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Test the wizard flow with a known site (perlmutter)."""
        sites_dir = tmp_path / "sites"
        sites_dir.mkdir(parents=True)
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: sites_dir)
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")

        # Simulate wizard input: site=1(perlmutter), username=testuser,
        # account=m1234, node_type=1(gpu), qos=1(regular),
        # runtime=1(podman-hpc), nodes=1, time_limit=30m,
        # site_name=perlmutter
        input_lines = "1\ntestuser\nm1234\n1\n1\n1\n1\n30m\nperlmutter\n"
        result = runner.invoke(main, ["setup"], input=input_lines)
        assert result.exit_code == 0
        assert "Saved site" in result.output
        assert (sites_dir / "perlmutter.yaml").exists()
        assert (tmp_path / "config.yaml").exists()

        # Verify constraint was auto-derived
        import yaml
        site = yaml.safe_load((sites_dir / "perlmutter.yaml").read_text())
        assert site["defaults"]["constraint"] == "gpu"
        assert site["defaults"]["node_type"] == "gpu"

    def test_setup_wizard_sets_default(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Test that wizard sets the default_site in config.yaml."""
        sites_dir = tmp_path / "sites"
        sites_dir.mkdir(parents=True)
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: sites_dir)
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")

        input_lines = "1\ntestuser\nm1234\n1\n1\n1\n1\n30m\nmypm\n"
        result = runner.invoke(main, ["setup"], input=input_lines)
        assert result.exit_code == 0

        import yaml
        config = yaml.safe_load((tmp_path / "config.yaml").read_text())
        assert config["default_site"] == "mypm"


class TestAutoTrigger:
    """Tests for the auto-trigger setup check."""

    def test_init_without_setup_triggers_wizard(
        self, runner: CliRunner, tmp_path: Path, monkeypatch,
    ):
        """Commands should trigger setup when no config exists."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        result = runner.invoke(main, ["init", str(tmp_path / "proj"), "--no-git", "--no-venv"])
        assert "Prism Setup" in result.output or "No execution environment" in result.output

    def test_setup_command_skips_auto_trigger(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """prism setup itself should not trigger the auto-trigger."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        monkeypatch.setattr("prism.dagster.targets.get_sites_dir",
                            lambda: tmp_path / "sites")
        result = runner.invoke(main, ["setup", "--list"])
        assert "no additional sites" in result.output.lower() or "local" in result.output

    def test_version_skips_auto_trigger(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """--version should not trigger setup."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output

    def test_help_skips_auto_trigger(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """--help should not trigger setup."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_commands_work_after_setup(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Commands should work normally when config exists."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("default_site: perlmutter\n")
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        result = runner.invoke(main, ["init", str(tmp_path / "proj"), "--no-git", "--no-venv"])
        assert result.exit_code == 0
        assert "Created ASP analysis project" in result.output


class TestRemoteCommandRemoved:
    """Verify that the old remote commands are gone."""

    def test_remote_not_a_command(self, runner: CliRunner):
        result = runner.invoke(main, ["remote", "--help"])
        assert result.exit_code != 0 or "No such command" in result.output \
            or "Error" in result.output
