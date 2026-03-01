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
@click.pass_context
def main(ctx: click.Context) -> None:
    """Prism - ASP-compliant Agentic Layer CLI."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand == "setup":
        return
    from prism.dagster.targets import get_config_path
    if not get_config_path().exists():
        console.print(
            "\n[bold yellow]No execution environment configured.[/bold yellow]"
        )
        console.print(
            "  Prism needs a default execution target before you can use it.\n"
        )
        ctx.invoke(setup)


# =============================================================================
# Init command
# =============================================================================


@main.command()
@click.argument("directory", type=click.Path(path_type=Path), default=".")
@click.option("--no-git", is_flag=True, help="Don't initialize git repository")
@click.option("--no-venv", is_flag=True, help="Don't create Python virtual environment")
@click.option("--target", "-t", default=None, help="Default execution target (e.g., perlmutter)")
def init(directory: Path, no_git: bool, no_venv: bool, target: str | None) -> None:
    """Create a new ASP analysis project with full agentic scaffolding.

    Creates the project with ASP specification files, Claude Code plugin
    configuration, skills, hooks, and a Python virtual environment.

    DIRECTORY is the project folder to create (default: current directory).

    Examples:
        prism init my-analysis
        prism init my-analysis --target perlmutter
        prism init my-analysis --no-git --no-venv
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
    _create_claude_md(directory, target=target)

    # Create Claude Code settings with local skills
    _create_claude_settings(directory)

    # Write prism.yaml project config and ensure target is configured
    if target:
        _create_prism_config(directory, target)

        # Ensure the target has been set up (has a config in ~/.prism/targets/)
        from prism.dagster.targets import load_target

        if load_target(target) is None:
            console.print(
                f"\n[yellow]Target [cyan]{target}[/cyan] is not configured yet.[/yellow]"
            )
            _run_setup_wizard(target)

    # Create virtual environment
    _create_venv(directory, no_venv)

    # Initialize git repository
    _init_git_repo(directory, no_git)

    # Print success message
    console.print(f"[green]✓[/green] Created ASP analysis project: [cyan]{directory}[/cyan]")
    if target:
        console.print(f"  Default target: [cyan]{target}[/cyan]")

    console.print(f"\n[bold]cd {directory}[/bold] && [bold]claude[/bold]")
    console.print("Then run [cyan]/prism-new[/cyan] to scope your research question.")


def _create_boilerplate_asp_yaml(directory: Path) -> None:
    """Create boilerplate asp.yaml with TODOs."""

    name = directory.name if directory != Path(".") else "My Analysis"

    asp_yaml = f"""# ASP Analysis Specification
# Documentation: https://github.com/LightconeResearch/ASP

version: "1.0"
name: "{name}"
description: |
  TODO: What research question are you trying to answer?

container:
  build: Containerfile

inputs:
  - id: primary_data
    type: data
    description: "TODO: Describe your primary data source"

outputs:
  - id: main_result
    type: metric
    description: "TODO: Describe your primary output metric"
    recipe:
      command: python scripts/compute.py

  - id: conclusion
    type: report
    description: "Summary addressing the problem statement"
    recipe:
      command: python scripts/summarize.py
      inputs: [main_result]

decisions:
  example_method:
    label: "Example Method Choice"
    tags: [analysis]
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

    # Create Containerfile
    containerfile = """\
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
"""
    (directory / "Containerfile").write_text(containerfile)

    # Create requirements.txt
    requirements = """\
numpy
pandas
"""
    (directory / "requirements.txt").write_text(requirements)

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
- `prism.yaml` — Prism config (default target, etc.)
- `CLAUDE.md` — Build conventions and project context for Claude Code
- `universes/` — Decision selections (one YAML per universe)
- `scripts/` — Implementation scripts
- `results/` — Execution outputs (gitignored)

## Documentation

See [ASP documentation](https://github.com/LightconeResearch/ASP) for the specification.
See [Prism documentation](https://github.com/LightconeResearch/Prism) for the agentic layer.
"""
    (directory / "README.md").write_text(readme)


def _create_claude_md(directory: Path, target: str | None = None) -> None:
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


def _create_prism_config(directory: Path, target: str) -> None:
    """Create prism.yaml with project-level configuration."""
    config = {"target": target}
    (directory / "prism.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False)
    )
    console.print(f"[green]✓[/green] Created prism.yaml (default target: {target})")


def _load_prism_config(project_path: Path) -> dict[str, Any]:
    """Load project-level prism.yaml configuration."""
    config_path = project_path / "prism.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text()) or {}
    return {}


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
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": ".claude/scripts/check-prism-run.sh",
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


@main.command()
@click.argument("outputs", nargs=-1)
@click.option("--universe", "-u", default=None, help="Universe to materialize for")
@click.option("--target", "-t", default=None, help="Execution target (e.g., perlmutter)")
@click.option("--no-build", is_flag=True, help="Skip automatic container image builds")
def run(
    outputs: tuple[str, ...],
    universe: str | None,
    target: str | None,
    no_build: bool,
) -> None:
    """Materialize ASP outputs via Dagster.

    Runs recipes to produce outputs. Without arguments, materializes all
    outputs for all universes. Container build specs are automatically
    built before execution unless --no-build is given.

    Examples:
        prism run                           # all outputs, all universes
        prism run accuracy                  # specific output
        prism run --universe baseline       # specific universe
        prism run accuracy -u baseline      # specific output + universe
        prism run --target perlmutter       # run on SLURM
        prism run --no-build                # skip container builds
    """
    from prism.dagster.assets import build_definitions

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    # Read default target from prism.yaml if not specified on command line
    if target is None:
        prism_config = _load_prism_config(project_path)
        target = prism_config.get("target")

    universe_id = universe or "baseline"
    defs = build_definitions(
        project_path, target=target, universe_id=universe_id, no_build=no_build,
    )

    console.print("[bold]Materializing outputs...[/bold]")

    import dagster as dg

    # Select assets to materialize
    all_assets = list(defs.get_all_asset_specs())
    if outputs:
        selection = list(outputs)
    else:
        selection = [spec.key.path[-1] for spec in all_assets]

    # Use a persistent DagsterInstance so run history is recorded for the
    # Dagster webserver (prism dev) to display.
    dagster_yaml = project_path / "dagster.yaml"
    if dagster_yaml.exists():
        instance = dg.DagsterInstance.from_config(str(project_path))
    else:
        instance = None

    # Execute
    try:
        result = dg.materialize(
            assets=list(defs.assets),
            selection=selection,
            instance=instance,
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
@click.option("--force", is_flag=True, help="Rebuild images even if they already exist")
@click.option(
    "--runtime", "-r",
    type=click.Choice(["docker", "podman-hpc", "shifter"]),
    default="docker",
    help="Container runtime to build with (default: docker)",
)
def build(force: bool, runtime: str) -> None:
    """Build container images from Containerfile specs in asp.yaml.

    Scans the analysis specification for container build specs (both
    analysis-level and per-recipe) and builds any missing images.
    Images are content-addressed — rebuilds only happen when the
    Containerfile or dependency files change.

    For NERSC targets, use --runtime to build with podman-hpc (which
    also migrates images for compute nodes) or pull pre-built images
    with shifter.

    Examples:
        prism build                      # build with docker
        prism build --runtime podman-hpc # build + migrate for NERSC
        prism build --force              # rebuild all images
    """
    from asp.helpers import get_outputs, load_yaml

    from prism.container import (
        ContainerBuildError,
        resolve_container_for_slurm,
        resolve_container_spec,
    )

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    spec = load_yaml(project_path / "asp.yaml")
    project_name = spec.get("name") or project_path.name

    # Collect all unique container build specs.
    build_specs: list[tuple[str, str | dict]] = []  # (label, spec)
    raw_default = spec.get("container")
    if raw_default is not None:
        if isinstance(raw_default, dict) and "build" in raw_default:
            build_specs.append(("analysis-level", raw_default))
        elif isinstance(raw_default, str) and runtime != "docker":
            # Pre-built images need pull/migrate for HPC runtimes
            build_specs.append(("analysis-level", raw_default))

    for output_def in get_outputs(spec):
        recipe = output_def.get("recipe")
        if not recipe:
            continue
        raw = recipe.get("container")
        if raw is not None:
            if isinstance(raw, dict) and "build" in raw:
                label = f"recipe:{output_def.get('id', '?')}"
                build_specs.append((label, raw))
            elif isinstance(raw, str) and runtime != "docker":
                label = f"recipe:{output_def.get('id', '?')}"
                build_specs.append((label, raw))

    if not build_specs:
        console.print("[dim]No container build specs found in asp.yaml.[/dim]")
        return

    console.print(
        f"[bold]Found {len(build_specs)} container spec(s) "
        f"(runtime: {runtime})[/bold]\n"
    )

    for label, bspec in build_specs:
        try:
            if runtime in ("podman-hpc", "shifter"):
                tag = resolve_container_for_slurm(
                    bspec, project_path, project_name, runtime, force=force,
                )
            else:
                tag = resolve_container_spec(
                    bspec, project_path, project_name, force=force,
                )
            console.print(f"  [green]ready[/green]  {label} -> {tag}")
        except ContainerBuildError as e:
            console.print(f"  [red]fail[/red]   {label}: {e}")


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

    # Show container status
    from prism.container import get_container_status

    raw_container = spec.get("container")
    cstatus = get_container_status(raw_container, project_path, name)
    if cstatus.type == "prebuilt":
        console.print(f"  Container: prebuilt [cyan]{cstatus.image}[/cyan]")
    elif cstatus.type == "build":
        if cstatus.extra.get("error"):
            console.print(
                f"  Container: build [red]{cstatus.extra['error']}[/red]"
            )
        elif cstatus.exists:
            console.print(
                f"  Container: build {cstatus.containerfile} "
                f"[green]{cstatus.image} (built)[/green]"
            )
        else:
            console.print(
                f"  Container: build {cstatus.containerfile} "
                f"[yellow]{cstatus.image} (not built)[/yellow]"
            )


@main.command()
@click.option("--port", "-p", default=3000, type=int, help="Port for Dagster webserver")
@click.option("--universe", "-u", default="baseline", help="Universe to load definitions for")
def dev(port: int, universe: str) -> None:
    """Launch Dagster webserver UI for the current project.

    Opens a web UI showing the asset graph, run history, and
    materialization status.

    Examples:
        prism dev
        prism dev --port 8080
        prism dev --universe experiment1
    """
    import tempfile

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    console.print(f"[bold]Starting Dagster webserver on port {port}...[/bold]")
    console.print(f"  Open [cyan]http://localhost:{port}[/cyan] in your browser")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # Generate a temporary Python file that builds Dagster Definitions from
    # the current ASP project.  dagster-webserver discovers assets via -f.
    defs_code = (
        "from pathlib import Path\n"
        "from prism.dagster.assets import build_definitions\n"
        f"defs = build_definitions(Path({str(project_path)!r}), "
        f"universe_id={universe!r}, no_build=True)\n"
    )

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="prism_defs_", delete=False,
        ) as f:
            f.write(defs_code)
            defs_file = f.name

        env = {**os.environ, "DAGSTER_HOME": str(project_path)}
        subprocess.run(
            ["dagster-webserver", "-f", defs_file, "-h", "0.0.0.0", "-p", str(port)],
            check=True,
            env=env,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Dagster webserver stopped[/dim]")
    except FileNotFoundError:
        console.print("[red]Error:[/red] dagster-webserver not found.")
        console.print("  Install with: [cyan]pip install prism\\[dagster][/cyan]")
        raise SystemExit(1)
    finally:
        # Clean up the temporary definitions file
        try:
            Path(defs_file).unlink(missing_ok=True)
        except NameError:
            pass


# =============================================================================
# Setup command
# =============================================================================


def _run_setup_wizard(name: str | None = None) -> Path:
    """Run the interactive setup wizard.

    Prompts for site selection, node type, QOS, and resource limits.
    Constraint and container flags are derived automatically from node type.

    Returns the path where the target config was saved.
    """
    from prism.dagster.sites import get_site_defaults, list_known_sites
    from prism.dagster.targets import save_target, save_user_config

    console.print("\n[bold]Prism Setup — Default Execution Environment[/bold]")
    console.print(
        "  These settings are stored in [cyan]~/.prism/[/cyan] and can be "
        "overridden per-project.\n"
    )

    # --- Site selection ---
    known = list_known_sites()
    console.print("  [bold]Known HPC sites:[/bold]")
    for i, (key, display) in enumerate(known, 1):
        console.print(f"    {i}. {display}")
    console.print(f"    {len(known) + 1}. Custom")

    site_choices = [str(i) for i in range(1, len(known) + 2)]
    site_idx = click.prompt(
        "\n  Select site",
        type=click.Choice(site_choices),
        default="1",
    )
    site_idx_int = int(site_idx)

    site: dict[str, Any] = {}
    site_key: str | None = None
    if site_idx_int <= len(known):
        site_key = known[site_idx_int - 1][0]
        site = get_site_defaults(site_key) or {}
        display = site.get("display_name", site_key)
        hostname = site.get("connection", {}).get("hostname", "")
        console.print(
            f"  Detected: [cyan]{display}[/cyan] ({hostname})\n"
        )
    else:
        # Custom site
        pass

    # --- Connection ---
    site_conn = site.get("connection", {})
    if not site_key:
        hostname = click.prompt("  Hostname", default="")

    username = click.prompt(
        "  Username",
        default=os.environ.get("USER", ""),
    )
    account = click.prompt("  Account/allocation")

    # --- Node type (auto-derives constraint) ---
    site_node_types = site.get("node_types", {})
    constraint = ""
    container_flags: list[str] = []
    node_type_key = ""

    if site_node_types:
        nt_keys = list(site_node_types.keys())
        console.print("\n  [bold]Node type:[/bold]")
        for i, ntk in enumerate(nt_keys, 1):
            ntinfo = site_node_types[ntk]
            desc = ntinfo.get("description", ntk)
            console.print(f"    {i}. {desc}")

        nt_choices = [str(i) for i in range(1, len(nt_keys) + 1)]
        nt_idx = click.prompt(
            "  Select node type",
            type=click.Choice(nt_choices),
            default="1",
        )
        nt_idx_int = int(nt_idx)
        node_type_key = nt_keys[nt_idx_int - 1]
        ntinfo = site_node_types[node_type_key]
        constraint = ntinfo["constraint"]
        container_flags = ntinfo.get("container_flags", [])
        console.print(f"    [dim]→ Constraint: {constraint}[/dim]")
        if container_flags:
            console.print(
                f"    [dim]→ Container flags: {' '.join(container_flags)}[/dim]"
            )
    else:
        constraint = click.prompt(
            "  Constraint (e.g., cpu, gpu, gpu&hbm80g)",
            default="",
        )

    # --- QOS ---
    site_qos = site.get("qos_options", {})
    if site_qos:
        qos_keys = list(site_qos.keys())
        default_qos_idx = "1"
        for i, qk in enumerate(qos_keys, 1):
            if site_qos[qk].get("default"):
                default_qos_idx = str(i)

        console.print("\n  [bold]QOS:[/bold]")
        for i, qk in enumerate(qos_keys, 1):
            desc = site_qos[qk].get("description", "")
            console.print(f"    {i}. {qk} — {desc}")

        qos_choices = [str(i) for i in range(1, len(qos_keys) + 1)]
        qos_idx = click.prompt(
            "  Select QOS",
            type=click.Choice(qos_choices),
            default=default_qos_idx,
        )
        qos = qos_keys[int(qos_idx) - 1]
    else:
        qos = click.prompt("  QOS", default="regular")

    # --- Container runtime ---
    site_runtimes = site.get("container_runtimes", [])
    if site_runtimes:
        console.print("\n  [bold]Container runtime:[/bold]")
        for i, rt in enumerate(site_runtimes, 1):
            console.print(f"    {i}. {rt}")

        rt_choices = [str(i) for i in range(1, len(site_runtimes) + 1)]
        rt_idx = click.prompt(
            "  Select runtime",
            type=click.Choice(rt_choices),
            default="1",
        )
        container_runtime = site_runtimes[int(rt_idx) - 1]
    else:
        container_runtime = click.prompt(
            "  Container runtime",
            type=click.Choice(["podman-hpc", "shifter", "singularity"]),
            default=site.get("scheduler", {}).get("container_runtime", "podman-hpc"),
        )

    # --- Resource limits ---
    site_limits = site.get("resource_limits", {})
    console.print("\n  [bold]Resource limits[/bold]")
    max_nodes = click.prompt(
        "    Max nodes per job", type=int,
        default=site_limits.get("max_nodes", 4),
    )
    max_walltime = click.prompt(
        "    Max walltime (minutes)", type=int,
        default=site_limits.get("max_walltime_minutes", 240),
    )
    max_concurrent = click.prompt(
        "    Max concurrent jobs", type=int,
        default=site_limits.get("max_concurrent_jobs", 8),
    )

    # --- Target name ---
    default_name = name or site_key or "default"
    target_name = click.prompt(
        "\n  Target name",
        default=default_name,
    )

    # --- Build and save config ---
    scheduler_config: dict[str, Any] = {
        "account": account,
        "node_type": node_type_key or "custom",
        "constraint": constraint,
        "qos": qos,
        "container_runtime": container_runtime,
    }
    if container_flags:
        scheduler_config["container_flags"] = container_flags

    config: dict[str, Any] = {
        "name": target_name,
        "backend": site.get("backend", "slurm"),
        "connection": {
            "hostname": site_conn.get("hostname", hostname),
            "username": username,
        },
        "scheduler": scheduler_config,
        "resource_limits": {
            "max_nodes": max_nodes,
            "max_walltime_minutes": max_walltime,
            "max_concurrent_jobs": max_concurrent,
        },
    }
    if site_key:
        config["site"] = site_key

    path = save_target(target_name, config)
    console.print(f"\n  [green]✓[/green] Saved target: [cyan]{path}[/cyan]")

    # Set as default
    save_user_config({"default_target": target_name})
    console.print(
        f"  [green]✓[/green] Set as default target in "
        f"[cyan]~/.prism/config.yaml[/cyan]"
    )
    console.print(
        "\n  To override per-project, add to [cyan]prism.yaml[/cyan]:"
    )
    console.print("    [dim]target: <other-target-name>[/dim]\n")

    return path


@main.command()
@click.argument("name", required=False)
@click.option("--list", "list_flag", is_flag=True, help="List saved targets")
@click.option("--show", "show_name", default=None, help="Show a target's config")
def setup(name: str | None, list_flag: bool, show_name: str | None) -> None:
    """Set up or manage execution environments.

    Configures connection details, node type, QOS, and resource limits
    for remote execution backends (SLURM). Constraint and container flags
    are derived automatically from the chosen node type.

    Settings are stored at the user level (~/.prism/) and can be overridden
    per-project via prism.yaml.

    Known HPC sites (NERSC Perlmutter, etc.) are auto-detected and
    pre-filled with sensible defaults.

    Examples:
        prism setup                   # interactive wizard
        prism setup perlmutter        # configure a named target
        prism setup --list            # list saved targets
        prism setup --show perlmutter # show a target's config
    """
    from prism.dagster.sites import list_known_sites
    from prism.dagster.targets import list_targets, load_target, load_user_config

    if show_name:
        config = load_target(show_name)
        if config is None:
            console.print(f"[red]Error:[/red] No saved target '{show_name}'.")
            raise SystemExit(1)
        console.print(f"[bold]Target: {show_name}[/bold]\n")
        console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))
        return

    if list_flag:
        saved = list_targets()
        user_config = load_user_config()
        default = user_config.get("default_target", "")

        if not saved:
            console.print("[dim]No saved targets.[/dim]")
        else:
            console.print("[bold]Saved targets:[/bold]")
            for t in saved:
                marker = " [green](default)[/green]" if t == default else ""
                console.print(f"  - {t}{marker}")

        known = list_known_sites()
        console.print(f"\n[bold]Known sites[/bold] (auto-detected defaults):")
        for key, display in known:
            console.print(f"  - [cyan]{key}[/cyan]  ({display})")
        console.print(
            "\nRun [cyan]prism setup <name>[/cyan] to configure a target."
        )
        return

    _run_setup_wizard(name)


if __name__ == "__main__":
    main()
