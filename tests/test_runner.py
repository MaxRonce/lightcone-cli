"""Tests for ASP Container Runner."""
from __future__ import annotations
from pathlib import Path
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
    def test_build_docker_command(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        cmd = runner.build_docker_command(
            command="python train.py",
            container="myimage:latest",
            input_ids=["cleaned_data"],
            output_id="trained_model",
            universe_id="baseline",
            resources={},
        )
        assert "docker" in cmd[0]
        assert "myimage:latest" in cmd
        assert "python train.py" in " ".join(cmd)

    def test_build_docker_mounts(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        mounts = runner.build_docker_mounts(
            input_ids=["cleaned_data"],
            output_id="trained_model",
            universe_id="baseline",
        )
        assert any("/workspace/inputs/cleaned_data" in m for m in mounts)
        assert any("/workspace/outputs/trained_model" in m for m in mounts)

    def test_no_container_raises(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="docker",
        )
        with pytest.raises(ValueError, match="No container specified"):
            runner.build_docker_command(
                command="python train.py",
                container=None,
                input_ids=[],
                output_id="result",
                universe_id="baseline",
                resources={},
            )

    def test_unknown_backend_raises(self, tmp_path):
        runner = ASPContainerRunner(
            project_root=str(tmp_path),
            backend="unknown",
        )
        with pytest.raises(ValueError, match="Unknown backend"):
            runner.execute(
                command="test",
                output_id="result",
                universe_id="baseline",
            )
