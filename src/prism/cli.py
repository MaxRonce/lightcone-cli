"""Command-line interface for Prism — the ASP-compliant agentic layer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console

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
def init(directory: Path, no_git: bool, no_venv: bool) -> None:
    """Create a new ASP analysis project with full agentic scaffolding.

    Creates the project with ASP specification files, Claude Code plugin
    configuration, skills, hooks, and a Python virtual environment.

    DIRECTORY is the project folder to create (default: current directory).

    Examples:
        prism init my-analysis
        prism init my-analysis --no-git
        prism init my-analysis --no-venv
    """
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

    # Create dagster.yaml for Dagster instance configuration
    dagster_yaml_content = {
        "storage": {
            "sqlite": {
                "base_dir": "results/.dagster",
            },
        },
    }
    (directory / "dagster.yaml").write_text(
        yaml.dump(dagster_yaml_content, default_flow_style=False, sort_keys=False)
    )

    # Create .gitignore
    gitignore = """# ASP Analysis
results/
results/.dagster/
__pycache__/
*.py[cod]
.venv/
.ipynb_checkpoints/
.DS_Store
"""
    (directory / ".gitignore").write_text(gitignore)

    # Create boilerplate asp.yaml
    _create_boilerplate_asp_yaml(directory)

    # Create CLAUDE.md with project conventions
    _create_claude_md(directory)

    # Create Claude Code settings with local skills
    _create_claude_settings(directory)

    # Create virtual environment
    _create_venv(directory, no_venv)

    # Initialize git repository
    _init_git_repo(directory, no_git)

    # Print success message
    console.print(f"[green]✓[/green] Created ASP analysis project: [cyan]{directory}[/cyan]")

    console.print(f"\n[bold]cd {directory}[/bold], then either:")
    console.print("  • [cyan]prism run[/cyan] to execute the analysis")
    console.print("  • [cyan]claude[/cyan] to work from the command line")
    console.print("\nThen run [cyan]/prism-new[/cyan] to scope your research question.")


def _create_boilerplate_asp_yaml(directory: Path) -> None:
    """Create boilerplate asp.yaml with TODOs."""

    name = directory.name if directory != Path(".") else "My Analysis"

    asp_yaml = f"""# ASP Analysis Specification
# Documentation: https://github.com/LightconeResearch/ASP

version: "1.0"
name: "{name}"
description: |
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
    recipe:
      command: python scripts/compute.py
      container: "python:3.12-slim"

  - id: conclusion
    type: report
    description: "Summary addressing the problem statement"
    recipe:
      command: python scripts/summarize.py
      inputs: [main_result]
      container: "python:3.12-slim"

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

decisions:
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


def _create_claude_md(directory: Path) -> None:
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

    (directory / "CLAUDE.md").write_text(content)


def _create_claude_settings(directory: Path) -> None:
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

    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


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
    lightcone_dir = Path.home() / ".lightcone"
    env = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.1.0"}
    try:
        if (lightcone_dir / "ASP").is_dir() and (lightcone_dir / "Prism").is_dir():
            # Use local clones from Lightcone installer
            install_targets = ["-e", str(lightcone_dir / "ASP")]
            install_targets += ["-e", str(lightcone_dir / "Prism")]
            subprocess.run(
                [str(pip_path), "install", *install_targets],
                capture_output=True,
                check=True,
                env=env,
            )
        else:
            # Fall back to HTTPS clone URLs
            subprocess.run(
                [str(pip_path), "install",
                 "git+https://github.com/LightconeResearch/Prism.git"],
                capture_output=True,
                check=True,
                env=env,
            )
        console.print("[green]✓[/green] Installed prism in virtual environment")
    except subprocess.CalledProcessError:
        console.print(
            "[yellow]Warning:[/yellow] Could not install prism automatically. "
            "You can install manually with: .venv/bin/pip install prism"
        )

    return True


# =============================================================================
# Dagster execution commands
# =============================================================================


def _require_dagster():
    """Check that dagster is installed, exit with helpful message if not."""
    try:
        import dagster  # noqa: F401
    except ImportError:
        console.print("[red]Error:[/red] Dagster is not installed.")
        console.print("  Install with: [cyan]pip install prism\\[dagster][/cyan]")
        raise SystemExit(1)


@main.command()
@click.argument("outputs", nargs=-1)
@click.option("--universe", "-u", default=None, help="Universe to materialize for")
@click.option("--target", "-t", default=None, help="Execution target (e.g., perlmutter)")
def run(outputs: tuple[str, ...], universe: str | None, target: str | None) -> None:
    """Materialize ASP outputs via Dagster.

    Runs recipes to produce outputs. Without arguments, materializes all
    outputs for all universes.

    Examples:
        prism run                           # all outputs, all universes
        prism run accuracy                  # specific output
        prism run --universe baseline       # specific universe
        prism run accuracy -u baseline      # specific output + universe
        prism run --target perlmutter       # run on SLURM
    """
    _require_dagster()

    from prism.dagster.assets import build_definitions

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    universe_id = universe or "baseline"
    defs = build_definitions(project_path, target=target, universe_id=universe_id)

    console.print("[bold]Materializing outputs...[/bold]")

    import dagster as dg

    # Select assets to materialize
    all_assets = list(defs.get_all_asset_specs())
    if outputs:
        selection = list(outputs)
    else:
        selection = [spec.key.path[-1] for spec in all_assets]

    # Execute
    try:
        result = dg.materialize(
            assets=list(defs.assets),
            selection=selection,
        )
        if result.success:
            console.print("[green]✓[/green] Materialization complete")
        else:
            console.print("[red]✗[/red] Materialization failed")
            raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@main.command()
@click.option("--universe", "-u", default=None, help="Show status for specific universe")
def status(universe: str | None) -> None:
    """Show materialization status of all outputs.

    Displays a table of outputs vs universes with materialization state.

    Examples:
        prism status
        prism status --universe baseline
    """
    from asp.helpers import get_outputs, load_yaml

    from prism.dagster.status import get_all_universe_status, get_output_status

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    spec = load_yaml(project_path / "asp.yaml")
    name = spec.get("name", "Unknown")
    outputs = get_outputs(spec)

    if universe:
        all_status = {universe: get_output_status(project_path, universe)}
    else:
        all_status = get_all_universe_status(project_path)

    if not all_status:
        console.print("[yellow]No universes found.[/yellow]")
        return

    from rich.table import Table

    table = Table(title=f"{name} — Output Status")
    table.add_column("Output", style="cyan")
    for uid in all_status:
        table.add_column(uid)

    recipe_count = 0
    total_outputs = len(outputs)
    materialized = 0
    total_cells = 0
    for out in outputs:
        out_id = out.get("id")
        if not out_id:
            continue
        has_recipe = bool(out.get("recipe"))
        if has_recipe:
            recipe_count += 1
        row = [out_id]
        for uid, universe_status in all_status.items():
            s = universe_status.get(out_id, "no_recipe")
            if has_recipe:
                total_cells += 1
            if s == "materialized":
                materialized += 1
                row.append("[green]ok[/green]")
            elif s == "pending":
                row.append("[dim]pending[/dim]")
            else:
                row.append("[yellow]no recipe[/yellow]")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n  Recipes: {recipe_count}/{total_outputs} outputs integrated")
    console.print(f"  Materialized: {materialized}/{total_cells} runs")


@main.command()
@click.option("--port", "-p", default=3000, type=int, help="Port for Dagster webserver")
def dev(port: int) -> None:
    """Launch Dagster webserver UI for the current project.

    Opens a web UI showing the asset graph, run history, and
    materialization status.

    Examples:
        prism dev
        prism dev --port 8080
    """
    _require_dagster()

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    console.print(f"[bold]Starting Dagster webserver on port {port}...[/bold]")
    console.print(f"  Open [cyan]http://localhost:{port}[/cyan] in your browser")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        subprocess.run(
            ["dagster-webserver", "-h", "0.0.0.0", "-p", str(port)],
            check=True,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Dagster webserver stopped[/dim]")
    except FileNotFoundError:
        console.print("[red]Error:[/red] dagster-webserver not found.")
        console.print("  Install with: [cyan]pip install prism\\[dagster][/cyan]")
        raise SystemExit(1)


# =============================================================================
# Remote target commands (Dagster executor configuration)
# =============================================================================


@main.group()
def remote() -> None:
    """Manage execution targets (Docker, SLURM)."""
    pass


@remote.command("setup")
@click.argument("name", required=False)
@click.option("--list", "list_targets_flag", is_flag=True, help="List saved targets")
def remote_setup(name: str | None, list_targets_flag: bool) -> None:
    """Configure an execution target.

    Sets up connection details, scheduler config, and resource limits
    for remote execution backends (SLURM, etc.).

    Examples:
        prism remote setup perlmutter
        prism remote setup --list
    """
    from prism.dagster.targets import list_targets, save_target

    if list_targets_flag:
        saved = list_targets()
        if not saved:
            console.print("[dim]No saved targets.[/dim]")
            console.print("Run [cyan]prism remote setup <name>[/cyan] to configure one.")
        else:
            console.print("[bold]Saved targets:[/bold]")
            for t in saved:
                console.print(f"  - {t}")
        return

    if name is None:
        console.print("[red]Error:[/red] Provide a target name.")
        raise SystemExit(1)

    console.print(f"\n[bold]Setting up target: [cyan]{name}[/cyan][/bold]\n")

    backend = click.prompt(
        "  Backend", type=click.Choice(["slurm", "pbs"]), default="slurm"
    )
    hostname = click.prompt("  Hostname")
    username = click.prompt("  Username", default=os.environ.get("USER", ""))
    account = click.prompt("  Account/allocation")
    partition = click.prompt("  Partition", default="regular")
    container_runtime = click.prompt(
        "  Container runtime",
        type=click.Choice(["shifter", "podman-hpc", "singularity"]),
        default="shifter",
    )

    console.print("\n  [bold]Resource limits[/bold]")
    max_nodes = click.prompt("    Max nodes per job", type=int, default=4)
    max_walltime = click.prompt("    Max walltime (minutes)", type=int, default=240)
    max_concurrent = click.prompt("    Max concurrent jobs", type=int, default=8)
    max_node_hours = click.prompt("    Max node-hours per session", type=int, default=32)

    config = {
        "name": name,
        "backend": backend,
        "connection": {"hostname": hostname, "username": username},
        "scheduler": {
            "account": account,
            "partition": partition,
            "container_runtime": container_runtime,
        },
        "resource_limits": {
            "max_nodes": max_nodes,
            "max_walltime_minutes": max_walltime,
            "max_concurrent_jobs": max_concurrent,
            "max_node_hours_per_session": max_node_hours,
        },
    }

    path = save_target(name, config)
    console.print(f"\n[green]✓[/green] Saved to [cyan]{path}[/cyan]")
    console.print(f"Use with: [cyan]prism run --target {name}[/cyan]")


@remote.command("show")
@click.argument("name")
def remote_show(name: str) -> None:
    """Show a saved target configuration."""
    from prism.dagster.targets import load_target

    config = load_target(name)
    if config is None:
        console.print(f"[red]Error:[/red] No saved target '{name}'.")
        raise SystemExit(1)

    console.print(f"[bold]Target: {name}[/bold]\n")
    console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))


@remote.command("edit")
@click.argument("name")
def remote_edit(name: str) -> None:
    """Open a saved target configuration in your editor.

    Uses $EDITOR (or vi) to edit the target YAML file.

    Examples:
        prism remote edit perlmutter
    """
    from prism.dagster.targets import get_targets_dir, load_target

    if load_target(name) is None:
        console.print(f"[red]Error:[/red] No saved target '{name}'.")
        console.print(f"Run [cyan]prism remote setup {name}[/cyan] to create one.")
        raise SystemExit(1)

    target_file = get_targets_dir() / f"{name}.yaml"
    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(target_file)], check=True)
        console.print(f"[green]✓[/green] Target '{name}' updated.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] Could not open editor: {e}")
        console.print(f"Edit manually: [cyan]{target_file}[/cyan]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
