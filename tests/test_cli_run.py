"""Tests for prism run CLI command."""
from click.testing import CliRunner
from prism.cli import main
import pytest


@pytest.fixture
def runner():
    return CliRunner()


class TestRunCommand:
    def test_run_help(self, runner):
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "Materialize" in result.output
