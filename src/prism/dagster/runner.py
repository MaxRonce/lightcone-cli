"""ASP Container Runner — executes recipes in Docker or SLURM containers."""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prism.dagster.io_manager import ASPIOManager


@dataclass
class ExecutionResult:
    """Result of executing a recipe."""
    exit_code: int
    output_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


def translate_resources_to_docker_flags(resources: dict[str, Any]) -> list[str]:
    """Translate ASP resource requirements to Docker CLI flags."""
    flags: list[str] = []
    if cpus := resources.get("cpus"):
        flags.append(f"--cpus={cpus}")
    if memory := resources.get("memory"):
        flags.append(f"--memory={memory.lower()}")
    if gpus := resources.get("gpus"):
        flags.append(f"--gpus={gpus}")
    return flags


class ASPContainerRunner:
    """Executes ASP recipes in containers.

    Dispatches to Docker (local) or SLURM (remote) based on backend config.
    """

    def __init__(
        self,
        project_root: str,
        backend: str = "docker",
        default_container: str | None = None,
        target_config: dict[str, Any] | None = None,
    ):
        self.project_root = Path(project_root)
        self.backend = backend
        self.default_container = default_container
        self.target_config = target_config or {}
        self.io_manager = ASPIOManager(project_root)

    def execute(
        self,
        command: str,
        output_id: str,
        universe_id: str,
        container: str | None = None,
        inputs: list[str] | None = None,
        resources: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a recipe, dispatching to the configured backend."""
        if self.backend == "docker":
            return self._run_docker(
                command=command,
                container=container or self.default_container,
                input_ids=inputs or [],
                output_id=output_id,
                universe_id=universe_id,
                resources=resources or {},
                params=params or {},
            )
        elif self.backend == "slurm":
            return self._run_slurm(
                command=command,
                container=container or self.default_container,
                input_ids=inputs or [],
                output_id=output_id,
                universe_id=universe_id,
                resources=resources or {},
            )
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def build_docker_mounts(
        self,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        params_file: Path | None = None,
    ) -> list[str]:
        """Build Docker volume mount arguments."""
        mounts: list[str] = []
        for inp_id in input_ids:
            host_path = self.io_manager.get_output_path(inp_id, universe_id)
            mounts.extend([
                "-v", f"{host_path}:/workspace/inputs/{inp_id}:ro"
            ])
        output_path = self.io_manager.get_output_path(output_id, universe_id)
        output_path.mkdir(parents=True, exist_ok=True)
        mounts.extend([
            "-v", f"{output_path}:/workspace/outputs/{output_id}"
        ])
        if params_file is not None:
            mounts.extend([
                "-v", f"{params_file}:/workspace/params.json:ro"
            ])
        return mounts

    def build_docker_command(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
        params_file: Path | None = None,
    ) -> list[str]:
        """Build the full docker run command."""
        if container is None:
            raise ValueError(
                f"No container specified for output '{output_id}' "
                "and no default_container configured"
            )
        cmd = ["docker", "run", "--rm"]
        cmd.extend(translate_resources_to_docker_flags(resources))
        cmd.extend(
            self.build_docker_mounts(
                input_ids, output_id, universe_id, params_file=params_file
            )
        )
        cmd.extend([container, "sh", "-c", command])
        return cmd

    def _run_docker(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a recipe in a Docker container."""
        # Write params.json to a temp file if decisions are provided
        params_file = None
        tmp = None
        try:
            if params:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                )
                json.dump(params, tmp)
                tmp.close()
                params_file = Path(tmp.name)

            docker_cmd = self.build_docker_command(
                command=command,
                container=container,
                input_ids=input_ids,
                output_id=output_id,
                universe_id=universe_id,
                resources=resources,
                params_file=params_file,
            )
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
            )
            output_path = self.io_manager.get_output_path(output_id, universe_id)
            return ExecutionResult(
                exit_code=result.returncode,
                output_path=output_path,
                metadata={
                    "stdout": result.stdout[-1000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                    "docker_command": " ".join(docker_cmd),
                },
            )
        finally:
            if tmp is not None:
                Path(tmp.name).unlink(missing_ok=True)

    def _run_slurm(
        self,
        command: str,
        container: str | None,
        input_ids: list[str],
        output_id: str,
        universe_id: str,
        resources: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a recipe via SLURM. Placeholder for Phase 2."""
        raise NotImplementedError("SLURM backend not yet implemented")
