"""Tests for ASP Container Runner."""
from __future__ import annotations

import pytest

from prism.dagster.runner import (
    ASPContainerRunner,
    translate_resources_to_docker_flags,
)


class TestResourceTranslation:
    def test_translate_cpus(self):
        flags = translate_resources_to_docker_flags({"cpus": 4})
        assert "--cpus=4" in flags

    def test_translate_memory(self):
        flags = translate_resources_to_docker_flags({"memory": "16GB"})
        assert "--memory=16gb" in flags

    def test_translate_gpus(self):
        flags = translate_resources_to_docker_flags({"gpus": 1})
        assert "--gpus=1" in flags

    def test_translate_empty(self):
        flags = translate_resources_to_docker_flags({})
        assert flags == []

    def test_translate_time_limit(self):
        flags = translate_resources_to_docker_flags({"time_limit": "2h"})
        assert isinstance(flags, list)


class TestDockerRunner:
    def test_execute_local_fallback(self, tmp_path):
        """Without Docker, execute falls back to local subprocess."""
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        result = runner.execute(
            command="python -c 'print(1)'",
            output_id="test_out",
            universe_id="baseline",
        )
        # Should succeed via local fallback
        assert result.exit_code == 0
        assert result.metadata.get("backend") == "local"

    def test_execute_with_container_string(self, tmp_path):
        """Runner stores default_container from init."""
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
            default_container="myimage:latest",
        )
        assert runner.default_container == "myimage:latest"

    def test_slurm_backend_not_implemented(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="slurm",
        )
        with pytest.raises(NotImplementedError, match="SLURM backend"):
            runner.execute(
                command="test",
                output_id="result",
                universe_id="baseline",
            )
