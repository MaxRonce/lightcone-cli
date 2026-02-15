"""Command-line interface for Prism — the ASP-compliant agentic layer."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel

console = Console()


def _get_plugin_source_dir() -> Path | None:
    """Find the Prism plugin source directory.

    Looks for the plugin files in:
    1. Bundled location (installed package): prism/claude/prism/
    2. Development location (repo): claude/prism/ relative to repo root
    """
    import prism

    package_dir = Path(prism.__file__).parent
    bundled_plugin = package_dir / "claude" / "prism"
    if bundled_plugin.exists():
        return bundled_plugin

    # Try development location (running from repo)
    repo_root = package_dir.parent.parent
    dev_plugin = repo_root / "claude" / "prism"
    if dev_plugin.exists():
        return dev_plugin

    return None


@click.group()
@click.version_option()
def main() -> None:
    """Prism - ASP-compliant Agentic Layer CLI."""
    pass


# =============================================================================
# Init command
# =============================================================================


@main.command()
@click.argument("directory", type=click.Path(path_type=Path), default=".")
@click.option("--no-git", is_flag=True, help="Don't initialize git repository")
@click.option("--no-venv", is_flag=True, help="Don't create Python virtual environment")
@click.option("--target", "-t", help="HPC/remote target (e.g., perlmutter)")
def init(directory: Path, no_git: bool, no_venv: bool, target: str | None) -> None:
    """Create a new ASP analysis project with full agentic scaffolding.

    Creates the project with ASP specification files, Claude Code plugin
    configuration, skills, hooks, and a Python virtual environment.

    DIRECTORY is the project folder to create (default: current directory).

    Examples:
        prism init my-analysis
        prism init my-analysis --no-git
        prism init my-analysis --no-venv
        prism init my-analysis --target perlmutter
    """
    # Resolve target configuration if specified
    target_config: dict[str, Any] | None = None
    if target is not None:
        target_config = _resolve_target_config(target)

    # Check if this is already an ASP project
    if (directory / "asp.yaml").exists():
        console.print(
            f"[red]Error:[/red] [cyan]{directory}[/cyan] is already an ASP project "
            f"(asp.yaml exists)."
        )
        console.print("Use [cyan]asp validate[/cyan] to check it, or delete asp.yaml to re-init.")
        raise SystemExit(1)

    # Create project directory
    if directory != Path("."):
        if directory.exists() and any(directory.iterdir()):
            if not click.confirm(
                f"[yellow]{directory}[/yellow] already exists and is not empty. Continue?"
            ):
                raise SystemExit(0)
        directory.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    subdirs = [
        "universes",
        "scripts",
        "results",
    ]
    for subdir in subdirs:
        (directory / subdir).mkdir(parents=True, exist_ok=True)

    # Create .gitignore
    gitignore = """# ASP Analysis
results/
__pycache__/
*.py[cod]
.venv/
.ipynb_checkpoints/
.DS_Store
"""
    if target_config is not None:
        gitignore += """\n# HPC (user-specific)
.claude/hpc.yaml
.claude/.hpc-session-usage
"""
    (directory / ".gitignore").write_text(gitignore)

    # Create boilerplate asp.yaml
    _create_boilerplate_asp_yaml(directory)

    # Create CLAUDE.md with project conventions
    _create_claude_md(directory, target_config=target_config, target_name=target)

    # Create Claude Code settings with local skills
    _create_claude_settings(directory, target_config=target_config)

    # Create project-level HPC config if target specified
    if target_config is not None:
        _create_project_hpc_config(directory, target_config)

    # Create virtual environment
    _create_venv(directory, no_venv)

    # Initialize git repository
    _init_git_repo(directory, no_git)

    # Print success message
    console.print(f"[green]✓[/green] Created ASP analysis project: [cyan]{directory}[/cyan]")
    if target_config is not None:
        display = target_config.get("target", {}).get("display_name", target)
        console.print(f"[green]✓[/green] Configured HPC target: [cyan]{display}[/cyan]")

    console.print(f"\n[bold]cd {directory}[/bold], then either:")
    console.print("  • [cyan]prism canvas[/cyan] to open the visual canvas")
    console.print("  • [cyan]claude[/cyan] to work from the command line")
    console.print("\nThen run [cyan]/prism-new[/cyan] to scope your research question.")


def _create_boilerplate_asp_yaml(directory: Path) -> None:
    """Create boilerplate asp.yaml with TODOs."""
    from asp.helpers import save_yaml

    name = directory.name if directory != Path(".") else "My Analysis"

    asp_yaml = f"""# ASP Analysis Specification
# Documentation: https://github.com/LightconeResearch/ASP

version: "1.0"

analysis:
  name: "{name}"
  problem: |
    TODO: What research question are you trying to answer?

  inputs:
    - id: primary_data
      type: data
      description: "TODO: Describe your primary data source"

  outputs:
    - id: main_result
      type: metric
      dtype: float
      description: "TODO: Describe your primary output metric"

    - id: conclusion
      type: report
      description: "Summary addressing the problem statement"

chunks:
  main:
    decisions:
      example_method:
        label: "Example Method Choice"
        type: method
        importance: 3
        rationale: "TODO: Explain why this decision matters"
        default: option_a
        options:
          option_a:
            label: "Option A"
            description: "TODO: Describe option A"
          option_b:
            label: "Option B"
            description: "TODO: Describe option B"
"""
    (directory / "asp.yaml").write_text(asp_yaml)

    # Create baseline universe
    baseline_universe = """# Baseline Universe
# Default configuration using standard practices

id: baseline
description: "Default configuration using standard practices"

chunks:
  main:
    example_method: option_a
"""
    (directory / "universes" / "baseline.yaml").write_text(baseline_universe)

    # Create README
    _create_readme(directory, name)


def _create_readme(directory: Path, name: str) -> None:
    """Create a README.md for the project."""
    readme = f"""# {name}

An ASP (Agentic Science Protocol) analysis project, built with Prism.

## Quick Start

```bash
# Open in Claude Code
claude

# Scope the analysis
/prism-new

# Then start building (Claude reads CLAUDE.md for conventions)
```

## Structure

- `asp.yaml` — Analysis specification (source of truth)
- `CLAUDE.md` — Build conventions and project context for Claude Code
- `universes/` — Decision selections (one YAML per universe)
- `scripts/` — Implementation scripts
- `results/` — Execution outputs (gitignored)

## Documentation

See [ASP documentation](https://github.com/LightconeResearch/ASP) for the specification.
See [Prism documentation](https://github.com/LightconeResearch/Prism) for the agentic layer.
"""
    (directory / "README.md").write_text(readme)


def _create_claude_md(
    directory: Path,
    target_config: dict[str, Any] | None = None,
    target_name: str | None = None,
) -> None:
    """Create CLAUDE.md from the template in the plugin source."""
    name = directory.name if directory != Path(".") else "My Analysis"

    # Find the template
    plugin_source = _get_plugin_source_dir()
    template_path = plugin_source / "templates" / "CLAUDE.md" if plugin_source else None

    if template_path and template_path.exists():
        content = template_path.read_text()
        content = content.replace("{{name}}", name)
    else:
        # Fallback: minimal CLAUDE.md if template not found
        content = (
            f"# CLAUDE.md\n\n## Project: {name}\n\n"
            "This is an ASP analysis project. Read `asp.yaml` for the specification.\n\n"
            "Read `.claude/skills/prism/SKILL.md` for how ASP works.\n\n"
            "---\n\n"
            "<!-- AUTOGENERATED: /prism-new populates below during specification -->\n"
            "## Analysis Details\n\n"
            "_Run `/prism-new` to scope the research question and populate this section._\n"
        )

    # Insert compute notes before Analysis Details section
    if target_config is not None:
        notes = target_config.get("notes")
        if notes:
            notes_section = f"### Compute Notes\n\n{notes.strip()}\n\n"
            marker = "<!-- AUTOGENERATED: /prism-new populates below during specification -->"
            if marker in content:
                content = content.replace(marker, notes_section + marker)
            else:
                content += "\n" + notes_section

    (directory / "CLAUDE.md").write_text(content)


def _create_claude_settings(
    directory: Path, target_config: dict[str, Any] | None = None
) -> None:
    """Create Claude Code settings with Prism skills and agents."""
    claude_dir = directory / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Find the plugin source directory
    plugin_source = _get_plugin_source_dir()
    if plugin_source is None:
        console.print(
            "[yellow]Warning:[/yellow] Could not find Prism plugin source files. "
            "Claude Code skills will not be available."
        )
        return

    # Copy scripts
    scripts_src = plugin_source / "scripts"
    scripts_dst = claude_dir / "scripts"
    if scripts_src.exists():
        if scripts_dst.exists():
            shutil.rmtree(scripts_dst)
        shutil.copytree(scripts_src, scripts_dst)
        # Make scripts executable
        for script in scripts_dst.glob("*.sh"):
            script.chmod(script.stat().st_mode | 0o111)

    # Copy skills
    skills_src = plugin_source / "skills"
    skills_dst = claude_dir / "skills"
    if skills_src.exists():
        if skills_dst.exists():
            shutil.rmtree(skills_dst)
        shutil.copytree(skills_src, skills_dst)

    # Create settings.json with hooks configured directly
    settings: dict[str, Any] = {
        "permissions": {
            "allow": [
                "Bash(asp:*)",
                "Bash(prism:*)",
                "Bash(python:*)",
                "Edit",
                "WebSearch",
                "WebFetch",
            ],
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": ".claude/scripts/activate-venv.sh",
                            "timeout": 5,
                        },
                        {
                            "type": "command",
                            "command": ".claude/scripts/session-start.sh",
                            "timeout": 10,
                        },
                    ],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ".claude/scripts/validate-on-save.sh",
                            "timeout": 15,
                        },
                    ],
                },
            ],
        },
    }

    # Add HPC-specific permissions and hooks if target configured
    if target_config is not None:
        from prism.remote import merge_permissions_into_settings

        merge_permissions_into_settings(settings, target_config)

        # Add HPC guard hook (PreToolUse on Bash)
        if "PreToolUse" not in settings["hooks"]:
            settings["hooks"]["PreToolUse"] = []
        settings["hooks"]["PreToolUse"].append(
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/hpc-guard.sh",
                        "timeout": 5,
                    },
                ],
            },
        )

        # Add HPC session start hook
        settings["hooks"]["SessionStart"][0]["hooks"].append(
            {
                "type": "command",
                "command": ".claude/scripts/hpc-session-start.sh",
                "timeout": 5,
            },
        )

    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


def _resolve_target_config(target: str) -> dict[str, Any]:
    """Resolve a target name to a full configuration."""
    import os

    from prism.remote import load_target_config

    saved = load_target_config(target)
    if saved is None:
        console.print(
            f"[red]Error:[/red] No saved target '{target}'. "
            f"Run [cyan]prism remote setup {target}[/cyan] first."
        )
        raise SystemExit(1)

    console.print(f"[green]✓[/green] Using saved target: [cyan]{target}[/cyan]")

    # Auto-detect username if missing
    auth = saved.get("auth", {})
    if not auth.get("username"):
        username = os.environ.get("USER", "")
        if username:
            auth["username"] = username
            saved["auth"] = auth

    return saved


def _create_project_hpc_config(directory: Path, target_config: dict[str, Any]) -> None:
    """Create .claude/hpc.yaml with project-level HPC configuration."""
    from prism.remote import create_project_hpc_config

    claude_dir = directory / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    project_config = create_project_hpc_config(target_config)
    hpc_path = claude_dir / "hpc.yaml"
    with open(hpc_path, "w") as f:
        yaml.dump(project_config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]✓[/green] Created HPC config: [cyan]{hpc_path}[/cyan]")


def _init_git_repo(directory: Path, no_git: bool) -> None:
    """Initialize git repository if requested."""
    if no_git or (directory / ".git").exists():
        return

    try:
        subprocess.run(
            ["git", "init"],
            cwd=directory,
            capture_output=True,
            check=True,
        )
        console.print("[green]✓[/green] Initialized git repository")
        try:
            subprocess.run(["git", "add", "."], cwd=directory, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial ASP analysis structure"],
                cwd=directory,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            pass
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


def _create_venv(directory: Path, no_venv: bool) -> bool:
    """Create a virtual environment with asp and prism installed."""
    if no_venv:
        return False

    venv_path = directory / ".venv"

    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning:[/yellow] Failed to create virtual environment: {e}")
        return False

    console.print("[green]✓[/green] Created virtual environment (.venv)")

    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip"
    else:
        pip_path = venv_path / "bin" / "pip"

    # Try to install prism (which pulls in asp as a dependency)
    try:
        subprocess.run(
            [str(pip_path), "install", "git+ssh://git@github.com/LightconeResearch/Prism.git"],
            capture_output=True,
            check=True,
        )
        console.print("[green]✓[/green] Installed prism in virtual environment")
    except subprocess.CalledProcessError:
        console.print(
            "[yellow]Warning:[/yellow] Could not install prism (SSH auth may have failed). "
            "You can install manually with: .venv/bin/pip install prism"
        )

    return True


# =============================================================================
# Remote/HPC target commands
# =============================================================================


@main.group()
def remote() -> None:
    """HPC/remote target management commands."""
    pass


@remote.command("setup")
@click.argument("name", required=False)
@click.option("--list", "list_targets", is_flag=True, help="List saved targets")
def remote_setup(name: str | None, list_targets: bool) -> None:
    """Set up a remote target configuration.

    Interactive CLI setup that configures scheduler, account, resource limits,
    permissions, and optional notes for any HPC cluster.

    Examples:
        prism remote setup perlmutter
        prism remote setup --list
    """
    from prism.remote import list_saved_targets, save_target_config

    if list_targets:
        saved = list_saved_targets()
        if not saved:
            console.print("[dim]No saved targets.[/dim]")
            console.print("Run [cyan]prism remote setup <name>[/cyan] to configure one.")
        else:
            console.print("[bold]Saved targets:[/bold]")
            for t in saved:
                console.print(f"  • {t}")
        return

    if name is None:
        console.print("[red]Error:[/red] Provide a target name.")
        console.print("  prism remote setup perlmutter")
        console.print("  prism remote setup my-cluster")
        raise SystemExit(1)

    console.print(f"\n[bold]Setting up target: [cyan]{name}[/cyan][/bold]\n")

    # 1. Scheduler
    scheduler = click.prompt(
        "  Scheduler", type=click.Choice(["slurm", "pbs", "sge"]), default="slurm"
    )

    # 2. Account/allocation
    account = click.prompt("  Account/allocation")

    # 3. Resource limits
    console.print("\n  [bold]Resource limits[/bold] [dim](Enter to accept defaults)[/dim]")
    defaults = _default_resource_limits()
    limits = _prompt_resource_limits(defaults)

    # 4. Permissions
    permissions = _default_permissions_for_scheduler(scheduler)
    console.print("\n  [bold]Default permissions:[/bold]")
    _show_permissions(permissions)
    if click.confirm("  Customize permissions?", default=False):
        permissions = _customize_permissions(permissions)

    # 5. Notes
    notes = _prompt_notes()

    # Build config
    config: dict[str, Any] = {
        "target": {
            "name": name,
            "scheduler": scheduler,
        },
        "auth": {
            "account": account,
        },
        "resource_limits": limits,
        "permissions": permissions,
    }
    if notes:
        config["notes"] = notes

    # Summary and confirm
    _print_setup_summary(config, name)

    if not click.confirm("\n  Save this configuration?", default=True):
        console.print("Aborted.")
        return

    path = save_target_config(name, config)
    console.print(f"\n[green]✓[/green] Saved to [cyan]{path}[/cyan]")
    console.print(f"Use with: [cyan]prism init my-analysis --target {name}[/cyan]")


@remote.command("show")
@click.argument("name")
def remote_show(name: str) -> None:
    """Show a saved target configuration.

    Example:
        prism remote show perlmutter
    """
    from prism.remote import load_target_config

    config = load_target_config(name)
    if config is None:
        console.print(f"[red]Error:[/red] No saved target '{name}'.")
        console.print("Run [cyan]prism remote setup --list[/cyan] to see available targets.")
        raise SystemExit(1)

    console.print(f"[bold]Target: {name}[/bold]\n")
    console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))


@remote.command("edit")
@click.argument("name")
def remote_edit(name: str) -> None:
    """Show the path to a target config for manual editing.

    Example:
        prism remote edit perlmutter
    """
    from prism.remote import get_targets_dir, load_target_config

    config = load_target_config(name)
    if config is None:
        console.print(f"[red]Error:[/red] No saved target '{name}'.")
        raise SystemExit(1)

    path = get_targets_dir() / f"{name}.yaml"
    console.print(f"Edit: [cyan]{path}[/cyan]")


# =============================================================================
# Remote helper functions
# =============================================================================


def _default_resource_limits() -> dict[str, int]:
    """Return sensible default resource limits."""
    return {
        "max_nodes": 4,
        "max_walltime_minutes": 120,
        "max_concurrent_jobs": 3,
        "max_node_hours_per_session": 16,
    }


def _prompt_resource_limits(defaults: dict[str, int]) -> dict[str, int]:
    """Prompt for resource limits with defaults."""
    return {
        "max_nodes": click.prompt(
            "    Max nodes per job", type=int, default=defaults["max_nodes"]
        ),
        "max_walltime_minutes": click.prompt(
            "    Max walltime (minutes)", type=int, default=defaults["max_walltime_minutes"]
        ),
        "max_concurrent_jobs": click.prompt(
            "    Max concurrent jobs", type=int, default=defaults["max_concurrent_jobs"]
        ),
        "max_node_hours_per_session": click.prompt(
            "    Max node-hours per session",
            type=int,
            default=defaults["max_node_hours_per_session"],
        ),
    }


def _default_permissions_for_scheduler(scheduler: str) -> dict[str, list[str]]:
    """Return default permission tiers for a given scheduler type."""
    auto_approve = ["python", "python3", "asp", "prism", "ls", "cat", "head", "tail", "grep", "du", "df"]
    deny = ["rm -rf /", "rm -rf ~", "rm -rf $HOME"]

    if scheduler == "slurm":
        auto_approve.extend(["squeue", "sacct", "scontrol show"])
        deny.extend(["scancel --all", "scancel -u"])
    elif scheduler == "pbs":
        auto_approve.extend(["qstat", "showq"])
        deny.extend(["qdel all"])
    elif scheduler == "sge":
        auto_approve.extend(["qstat", "qhost"])
        deny.extend(["qdel '*'"])

    return {
        "auto_approve": auto_approve,
        "deny": deny,
    }


def _show_permissions(permissions: dict[str, list[str]]) -> None:
    """Display permission tiers."""
    auto = permissions.get("auto_approve", [])
    deny = permissions.get("deny", [])

    console.print(f"    [green]Auto-approve:[/green] {', '.join(auto)}")
    console.print(f"    [red]Deny:[/red] {', '.join(deny)}")


def _customize_permissions(permissions: dict[str, list[str]]) -> dict[str, list[str]]:
    """Let user add/remove from permission tiers."""
    import copy

    result = copy.deepcopy(permissions)

    add_auto = click.prompt(
        "    Add to auto-approve (comma-separated, or Enter to skip)",
        default="",
        show_default=False,
    )
    if add_auto.strip():
        result["auto_approve"].extend(cmd.strip() for cmd in add_auto.split(",") if cmd.strip())

    remove_auto = click.prompt(
        "    Remove from auto-approve (comma-separated, or Enter to skip)",
        default="",
        show_default=False,
    )
    if remove_auto.strip():
        to_remove = {cmd.strip() for cmd in remove_auto.split(",")}
        result["auto_approve"] = [cmd for cmd in result["auto_approve"] if cmd not in to_remove]

    add_deny = click.prompt(
        "    Add to deny (comma-separated, or Enter to skip)", default="", show_default=False
    )
    if add_deny.strip():
        result["deny"].extend(cmd.strip() for cmd in add_deny.split(",") if cmd.strip())

    return result


def _prompt_notes() -> str:
    """Prompt for multi-line notes. Blank line to finish."""
    console.print("\n  [bold]Notes/guidelines for Claude[/bold] [dim](blank line to finish)[/dim]")
    lines: list[str] = []
    while True:
        line = click.prompt("  ", default="", show_default=False)
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def _print_setup_summary(config: dict[str, Any], name: str) -> None:
    """Print a Rich summary of the target configuration."""
    target = config.get("target", {})
    auth = config.get("auth", {})
    limits = config.get("resource_limits", {})
    notes = config.get("notes", "")

    lines = [
        f"[bold]Scheduler:[/bold] {target.get('scheduler', 'N/A')}",
        f"[bold]Account:[/bold] {auth.get('account', 'N/A')}",
        f"[bold]Max nodes:[/bold] {limits.get('max_nodes', 'N/A')}",
        f"[bold]Max walltime:[/bold] {limits.get('max_walltime_minutes', 'N/A')} min",
        f"[bold]Max concurrent:[/bold] {limits.get('max_concurrent_jobs', 'N/A')}",
        f"[bold]Session budget:[/bold] {limits.get('max_node_hours_per_session', 'N/A')} node-hrs",
    ]
    if notes:
        lines.append(f"[bold]Notes:[/bold] {notes[:60]}{'...' if len(notes) > 60 else ''}")

    panel = Panel("\n".join(lines), title=f"Target: {name}", border_style="cyan")
    console.print(panel)


# =============================================================================
# Canvas command
# =============================================================================


@main.command()
@click.argument("target", default=".")
@click.option("--port", default=8080, type=int, help="Port to serve on")
@click.option("--no-browser", is_flag=True, help="Don't auto-open browser")
@click.option("--jupyter", is_flag=True, help="Print JupyterHub proxied URL")
def canvas(target: str, port: int, no_browser: bool, jupyter: bool) -> None:
    """Open the ASP Canvas visual editor.

    Launches a Python-served web UI for visualizing and interacting with
    ASP projects. No Node.js required.

    Install with: pip install prism[canvas]

    Examples:
        prism canvas
        prism canvas /some/path
        prism canvas --port 9000
        prism canvas --jupyter
    """
    try:
        from asp_canvas.cli import main as canvas_main  # type: ignore[import-not-found]
    except ImportError:
        console.print("[red]Error:[/red] Canvas not installed.")
        console.print("  Install with: [cyan]pip install prism[canvas][/cyan]")
        raise SystemExit(1)

    args = [target]
    if port != 8080:
        args.extend(["--port", str(port)])
    if no_browser:
        args.append("--no-browser")
    if jupyter:
        args.append("--jupyter")

    canvas_main(args, standalone_mode=False)


# =============================================================================
# Navigator command
# =============================================================================


def _get_prism_config_path() -> Path:
    """Get the path to the Prism global config file."""
    return Path.home() / ".prism" / "config.yaml"


def _load_prism_config() -> dict[str, Any]:
    """Load Prism global config from ~/.prism/config.yaml."""
    config_path = _get_prism_config_path()
    if not config_path.exists():
        return {}
    from asp.helpers import load_yaml

    return load_yaml(config_path)


def _save_prism_config(config: dict[str, Any]) -> None:
    """Save Prism global config to ~/.prism/config.yaml."""
    config_path = _get_prism_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    from asp.helpers import save_yaml

    save_yaml(config, config_path)


def _get_navigator_path() -> Path | None:
    """Get Navigator path from config or environment variable."""
    import os

    env_path = Path(p) if (p := os.environ.get("ASP_NAVIGATOR_PATH")) else None
    if env_path and env_path.exists():
        return env_path

    config = _load_prism_config()
    config_path = config.get("navigator", {}).get("path")
    if config_path:
        path = Path(config_path)
        if path.exists():
            return path

    return None


@main.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    help="Project path (default: current directory)",
)
@click.option(
    "--configure",
    is_flag=True,
    help="Reconfigure Navigator path",
)
def navigator(path: Path | None, configure: bool) -> None:
    """Open the current project in Navigator.

    Navigator is the visual canvas editor for ASP projects. This command
    starts Navigator for the current project.

    Press Ctrl+C to stop Navigator.

    Examples:
        prism navigator
        prism navigator -p /some/path
        prism navigator --configure
    """
    from asp.cli import find_analysis_file

    navigator_path = _get_navigator_path()

    if configure or navigator_path is None:
        if navigator_path is None:
            console.print("[yellow]Navigator path not configured.[/yellow]")
        default_hint = navigator_path or ""
        user_path = click.prompt(
            "Where is Navigator installed?",
            default=str(default_hint) if default_hint else None,
            type=click.Path(exists=True, path_type=Path),
        )
        navigator_path = Path(user_path)

        if not (navigator_path / "package.json").exists():
            console.print(f"[red]Error:[/red] {navigator_path} doesn't look like Navigator")
            console.print("  (No package.json found)")
            raise SystemExit(1)

        config = _load_prism_config()
        if "navigator" not in config:
            config["navigator"] = {}
        config["navigator"]["path"] = str(navigator_path)
        _save_prism_config(config)
        console.print("[green]✓[/green] Saved Navigator path to ~/.prism/config.yaml")

        if configure:
            return

    if path is None:
        path = Path.cwd()

    analysis_file = find_analysis_file(path)
    if analysis_file is None:
        console.print(f"[red]Error:[/red] No asp.yaml found in {path}")
        raise SystemExit(1)

    project_path = analysis_file.parent.resolve()
    from urllib.parse import quote

    url = f"http://localhost:3000?project={quote(str(project_path), safe='')}"

    console.print(f"[bold]Starting Navigator for:[/bold] {project_path}")
    console.print()
    console.print("[bold green]Open this URL in your browser:[/bold green]")
    console.print(f"  {url}")
    console.print()
    console.print("[dim]Press Ctrl+C to stop (ignore the localhost:3000 URL below)[/dim]\n")

    try:
        subprocess.run(
            ["npm", "run", "dev:all"],
            cwd=navigator_path,
            check=True,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Navigator stopped[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error:[/red] Navigator exited with code {e.returncode}")
        raise SystemExit(e.returncode)


if __name__ == "__main__":
    main()
