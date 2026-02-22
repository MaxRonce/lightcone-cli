"""ASP Container Runner — executes recipes in Docker, locally, or via SLURM."""
from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing a recipe."""
    exit_code: int
    output_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_cli_args(params: dict[str, Any], universe_id: str) -> list[str]:
    """Build CLI arguments from universe decisions."""
    args = ["--universe", universe_id]
    for key, value in params.items():
        args.extend([f"--{key}", str(value)])
    return args


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
    """Executes ASP recipes via Docker, local subprocess, or SLURM.

    When backend is "docker", attempts Docker execution first.  If Docker
    fails (missing image, daemon not running, non-zero exit), falls back to
    local subprocess execution with a warning.
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
        """Execute a recipe, dispatching to the configured backend.

        For the "docker" backend, falls back to local execution when Docker
        is unavailable or the container run fails.
        """
        cli_args = _build_cli_args(params or {}, universe_id)
        results_dir = self.project_root / "results" / universe_id
        results_dir.mkdir(parents=True, exist_ok=True)

        if self.backend == "slurm":
            return self._run_slurm(
                command=command,
                container=container or self.default_container,
                input_ids=inputs or [],
                output_id=output_id,
                universe_id=universe_id,
                resources=resources or {},
            )

        # Docker backend — try Docker first, fall back to local
        effective_container = container or self.default_container
        if effective_container:
            result = self._run_docker(
                command=command,
                container=effective_container,
                universe_id=universe_id,
                resources=resources or {},
                cli_args=cli_args,
            )
            if result.exit_code == 0:
                return result
            # Docker failed — fall back
            logger.warning(
                "Docker execution failed for '%s' (exit code %d). "
                "Falling back to local execution.\n  stderr: %s",
                output_id, result.exit_code,
                result.metadata.get("stderr", "")[:200],
            )

        return self._run_local(
            command=command,
            output_id=output_id,
            universe_id=universe_id,
            cli_args=cli_args,
            warn=effective_container is not None,
        )

    def _run_docker(
        self,
        command: str,
        container: str,
        universe_id: str,
        resources: dict[str, Any],
        cli_args: list[str],
    ) -> ExecutionResult:
        """Execute a recipe in a Docker container.

        Mounts the project root at /workspace so scripts can read data and
        write results using their normal relative paths.
        """
        full_command = command + " " + " ".join(cli_args)

        cmd = ["docker", "run", "--rm"]
        cmd.extend(translate_resources_to_docker_flags(resources))
        cmd.extend([
            "-v", f"{self.project_root}:/workspace",
            "-w", "/workspace",
            container,
            "sh", "-c", full_command,
        ])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            # Docker binary not found
            return ExecutionResult(
                exit_code=127,
                output_path=self.project_root / "results" / universe_id,
                metadata={"stderr": "docker: command not found"},
            )

        return ExecutionResult(
            exit_code=result.returncode,
            output_path=self.project_root / "results" / universe_id,
            metadata={
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "backend": "docker",
                "docker_command": " ".join(cmd),
            },
        )

    def _run_local(
        self,
        command: str,
        output_id: str,
        universe_id: str,
        cli_args: list[str],
        warn: bool = False,
    ) -> ExecutionResult:
        """Execute a recipe as a local subprocess.

        Uses the current Python environment.  Decision parameters are passed
        as CLI arguments.
        """
        if warn:
            logger.warning(
                "Executing '%s' locally (no container). "
                "Results may differ from containerised execution.",
                output_id,
            )

        full_command = command + " " + " ".join(cli_args)

        # Use the same Python that is running prism, unless the command
        # explicitly names an interpreter.
        env_python = sys.executable
        if full_command.startswith("python "):
            full_command = env_python + full_command[len("python"):]

        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(self.project_root),
        )

        output_path = self.project_root / "results" / universe_id
        return ExecutionResult(
            exit_code=result.returncode,
            output_path=output_path,
            metadata={
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "backend": "local",
            },
        )

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
