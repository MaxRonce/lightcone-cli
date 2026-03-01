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

PERMISSION_TIERS = {
    "yolo": {
        "allow": [
            "Bash(*)",
            "Edit",
            "Read",
            "Write",
            "WebSearch",
            "WebFetch",
            "mcp__*",
        ],
    },
    "recommended": {
        "allow": [
            "Bash(asp:*)",
            "Bash(prism:*)",
            "Bash(python:*)",
            "Bash(pip:*)",
            "Bash(git status:*)",
            "Bash(git log:*)",
            "Bash(git diff:*)",
            "Bash(git add:*)",
            "Bash(git commit:*)",
            "Bash(git branch:*)",
            "Bash(git checkout:*)",
            "Bash(git switch:*)",
            "Edit",
            "WebSearch",
            "WebFetch",
        ],
    },
    "minimal": {
        "allow": ["Read"],
    },
}


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
    if ctx.invoked_subcommand in ("setup", "profiles"):
        return
    from prism.dagster.targets import get_config_path
    if not get_config_path().exists():
        console.print(
            "\n[bold yellow]No execution environment configured.[/bold yellow]"
        )
        console.print(
            "  Prism needs a default site configured before you can use it.\n"
        )
        ctx.invoke(setup)


# =============================================================================
# Init command
# =============================================================================


@main.command()
@click.argument("directory", type=click.Path(path_type=Path), default=".")
@click.option("--no-git", is_flag=True, help="Don't initialize git repository")
@click.option("--no-venv", is_flag=True, help="Don't create Python virtual environment")
@click.option("--site", "-s", default=None, help="Site for default compute profile")
@click.option(
    "--permissions",
    type=click.Choice(["yolo", "recommended", "minimal"]),
    default=None,
    help="Claude Code permission tier (default: prompt or saved default)",
)
def init(
    directory: Path, no_git: bool, no_venv: bool,
    site: str | None, permissions: str | None,
) -> None:
    """Create a new ASP analysis project with full agentic scaffolding.

    Creates the project with ASP specification files, Claude Code plugin
    configuration, skills, hooks, and a Python virtual environment.

    DIRECTORY is the project folder to create (default: current directory).

    Examples:
        prism init my-analysis
        prism init my-analysis --site perlmutter
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
    _create_claude_md(directory)

    # Resolve permission tier and create Claude Code settings
    tier = _resolve_permission_tier(permissions)
    _create_claude_settings(directory, tier)

    # Write prism.yaml project config and ensure site is configured
    if site:
        _create_prism_config(directory, site)

        # Ensure the site has been set up (has a config in ~/.prism/sites/)
        if site != "local":
            from prism.dagster.targets import load_site
            if load_site(site) is None:
                console.print(
                    f"\n[yellow]Site [cyan]{site}[/cyan] is not configured yet.[/yellow]"
                )
                _run_setup_wizard(site)

    # Create virtual environment
    _create_venv(directory, no_venv)

    # Initialize git repository
    _init_git_repo(directory, no_git)

    # Print success message
    console.print(f"[green]✓[/green] Created ASP analysis project: [cyan]{directory}[/cyan]")
    if site:
        console.print(f"  Default site: [cyan]{site}[/cyan]")

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
- `prism.yaml` — Prism config (compute profiles)
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
            "Run `/prism-new` to scope a research question.\n\n"
            "---\n\n"
            "<!-- AUTOGENERATED: /prism-new populates below during specification -->\n"
            "## Analysis Details\n\n"
            "_Run `/prism-new` to scope the research question and populate this section._\n"
        )

    (directory / "CLAUDE.md").write_text(content)


def _create_prism_config(directory: Path, site_name: str) -> None:
    """Create prism.yaml with a default compute profile."""
    config = {
        "profiles": {
            "default": {
                "site": site_name,
            }
        }
    }
    (directory / "prism.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False)
    )
    console.print(f"[green]✓[/green] Created prism.yaml (default site: {site_name})")



def _prompt_permission_tier() -> str:
    """Interactively prompt the user to choose a permission tier.

    Returns one of: 'yolo', 'recommended', 'minimal'.
    Saves the choice as the default for future projects.
    """
    console.print("\n[bold]Claude Code permission level[/bold]")
    console.print("  Controls what Claude can do without asking.\n")
    console.print("    1. yolo — Everything auto-allowed. No prompts.")
    console.print("    2. recommended — Prism workflow auto-allowed. Prompts for the rest.")
    console.print("    3. minimal — Only file reading. Everything else prompts.")

    choice_map = {"1": "yolo", "2": "recommended", "3": "minimal"}
    raw = click.prompt(
        "\n  Select permission level",
        type=click.Choice(["1", "2", "3"]),
        default="2",
    )
    tier = choice_map.get(raw, "recommended")

    from prism.dagster.targets import load_user_config, save_user_config
    global_config = load_user_config()
    global_config["default_permission_tier"] = tier
    save_user_config(global_config)
    console.print(f"  [green]✓[/green] Permissions: {tier}")

    return tier


def _resolve_permission_tier(flag_value: str | None) -> str:
    """Resolve which permission tier to use.

    Priority:
    1. --permissions flag (explicit override)
    2. Saved default in ~/.prism/config.yaml
    3. Interactive prompt (first time only)
    """
    # 1. Explicit flag
    if flag_value is not None:
        console.print(f"  Permissions: [cyan]{flag_value}[/cyan] (--permissions flag)")
        return flag_value

    # 2. Saved default
    from prism.dagster.targets import load_user_config
    global_config = load_user_config()
    saved = global_config.get("default_permission_tier")
    if saved:
        console.print(f"  Permissions: [cyan]{saved}[/cyan] (saved default)")
        return saved

    # 3. Interactive prompt
    return _prompt_permission_tier()


def _create_claude_settings(directory: Path, tier: str = "recommended") -> None:
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

    permissions = PERMISSION_TIERS[tier]

    # Create settings.json with hooks configured directly
    settings: dict[str, Any] = {
        "permissions": permissions,
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


def _get_lightcone_venv_site_packages() -> Path | None:
    """Read ~/.lightcone/.config to find the Lightcone venv's site-packages."""
    config_file = Path.home() / ".lightcone" / ".config"
    if not config_file.exists():
        return None

    # Parse the simple KEY="VALUE" config file
    venv_path_str = None
    for line in config_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("VENV_PATH="):
            venv_path_str = line.split("=", 1)[1].strip().strip('"')
            break

    if not venv_path_str:
        return None

    venv_path = Path(venv_path_str)
    if not venv_path.is_dir():
        return None

    # Find site-packages inside the Lightcone venv
    candidates = list(venv_path.glob("lib/python*/site-packages"))
    if not candidates:
        candidates = list(venv_path.glob("Lib/site-packages"))  # Windows
    return candidates[0] if candidates else None


def _create_venv(directory: Path, no_venv: bool) -> bool:
    """Create a virtual environment with asp and prism installed."""
    if no_venv:
        return False

    venv_path = directory / ".venv"

    try:
        subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages", str(venv_path)],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning:[/yellow] Failed to create virtual environment: {e}")
        return False

    console.print("[green]✓[/green] Created virtual environment (.venv)")

    # --system-site-packages only exposes the *real* system Python's packages.
    # If Lightcone was installed into its own venv (the common case), we need
    # to bridge the new project venv to the Lightcone venv's site-packages
    # via a .pth file.
    lightcone_sp = _get_lightcone_venv_site_packages()
    if lightcone_sp:
        inner_sp_dirs = list(venv_path.glob("lib/python*/site-packages"))
        if not inner_sp_dirs and sys.platform == "win32":
            inner_sp_dirs = list(venv_path.glob("Lib/site-packages"))
        if inner_sp_dirs:
            pth_file = inner_sp_dirs[0] / "_lightcone.pth"
            pth_file.write_text(str(lightcone_sp) + "\n")

    # Check if prism is now importable in the new venv
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python"
    else:
        python_path = venv_path / "bin" / "python"

    try:
        subprocess.run(
            [str(python_path), "-c", "import prism"],
            capture_output=True,
            check=True,
        )
        console.print("[green]✓[/green] prism available (via Lightcone environment)")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not available — install it
        pip_path = python_path.parent / "pip"
        lightcone_dir = Path.home() / ".lightcone"
        env = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.1.0"}
        try:
            if (lightcone_dir / "ASP").is_dir() and (lightcone_dir / "Prism").is_dir():
                install_targets = ["-e", str(lightcone_dir / "ASP")]
                install_targets += ["-e", str(lightcone_dir / "Prism")]
                subprocess.run(
                    [str(pip_path), "install", *install_targets],
                    capture_output=True,
                    check=True,
                    env=env,
                )
            else:
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
@click.option("--profile", "-p", default=None, help="Compute profile name")
@click.option("--no-build", is_flag=True, help="Skip automatic container image builds")
def run(
    outputs: tuple[str, ...],
    universe: str | None,
    profile: str | None,
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
        prism run --profile perlmutter      # run on SLURM
        prism run --no-build                # skip container builds
    """
    from prism.dagster.assets import build_definitions
    from prism.dagster.profiles import load_profiles, resolve_profile
    from prism.dagster.targets import load_site, load_user_config

    project_path = Path.cwd()
    if not (project_path / "asp.yaml").exists():
        console.print("[red]Error:[/red] No asp.yaml found in current directory.")
        raise SystemExit(1)

    # Resolve profile
    profile_name = profile or "default"
    profiles = load_profiles(project_path)
    profile_data = profiles.get(profile_name, {})

    # Determine site
    site_name = profile_data.get("site")
    if not site_name:
        user_config = load_user_config()
        site_name = user_config.get("default_site")

    # Load site and resolve
    profile_config = None
    if site_name:
        if site_name == "local":
            profile_config = resolve_profile(profile_data, {"backend": "local"})
        else:
            site_config = load_site(site_name)
            if site_config:
                profile_config = resolve_profile(profile_data, site_config)

    universe_id = universe or "baseline"
    defs = build_definitions(
        project_path, profile_config=profile_config, universe_id=universe_id,
        no_build=no_build,
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

    For NERSC sites, use --runtime to build with podman-hpc (which
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
# Profiles command
# =============================================================================


@main.group(invoke_without_command=True)
@click.pass_context
def profiles(ctx: click.Context) -> None:
    """List and manage compute profiles for this project."""
    if ctx.invoked_subcommand is not None:
        return

    project_path = Path.cwd()
    prism_yaml = project_path / "prism.yaml"
    if not prism_yaml.exists():
        click.echo("No prism.yaml found. Run 'prism init' first.")
        return

    from prism.dagster.profiles import load_profiles

    profile_data = load_profiles(project_path)
    if not profile_data:
        click.echo("No profiles defined in prism.yaml.")
        return

    # Get project name from asp.yaml
    asp_yaml = project_path / "asp.yaml"
    project_name = project_path.name
    if asp_yaml.exists():
        with open(asp_yaml) as f:
            asp_data = yaml.safe_load(f) or {}
        project_name = asp_data.get("name", project_name)

    click.echo(f"\n  {project_name} — Compute Profiles\n")
    click.echo(f"  {'PROFILE':<14}{'SITE':<14}{'QOS':<10}{'NODES':<7}{'TIME'}")
    for name, prof in profile_data.items():
        site = prof.get("site", "—")
        qos = prof.get("qos", "—")
        nodes = prof.get("nodes", "—")
        time_limit = prof.get("time_limit", "—")
        click.echo(f"  {name:<14}{site:<14}{qos:<10}{str(nodes):<7}{time_limit}")
    click.echo("\n  Use: prism run --profile <name>\n")


@profiles.command()
@click.argument("name")
def add(name: str) -> None:
    """Add a compute profile to this project."""
    from prism.dagster.sites import get_site_defaults
    from prism.dagster.targets import load_site, load_user_config

    project_path = Path.cwd()
    prism_yaml = project_path / "prism.yaml"
    if not prism_yaml.exists():
        click.echo("No prism.yaml found. Run 'prism init' first.")
        raise SystemExit(1)

    with open(prism_yaml) as f:
        data = yaml.safe_load(f) or {}

    profiles_data = data.setdefault("profiles", {})

    # Determine default site from existing profiles or user config
    existing_site = None
    if "default" in profiles_data:
        existing_site = profiles_data["default"].get("site")
    if not existing_site:
        user_config = load_user_config()
        existing_site = user_config.get("default_site", "local")

    site_name = click.prompt("  Site", default=existing_site)

    profile: dict[str, Any] = {"site": site_name}

    # Load site info for QOS options
    site_config = load_site(site_name)
    site_defaults = get_site_defaults(site_name)

    # QOS selection
    qos_options = {}
    if site_defaults and site_defaults.get("qos_options"):
        qos_options = site_defaults["qos_options"]

    if qos_options:
        click.echo("  QOS:")
        qos_list = list(qos_options.items())
        for i, (qos_key, qos_info) in enumerate(qos_list, 1):
            click.echo(f"    {i}. {qos_key} — {qos_info['description']}")
        qos_choices = [str(i) for i in range(1, len(qos_list) + 1)]
        choice = click.prompt(
            "  Select QOS",
            type=click.Choice(qos_choices),
            default="1",
        )
        profile["qos"] = qos_list[int(choice) - 1][0]
    else:
        qos = click.prompt("  QOS", default="")
        if qos:
            profile["qos"] = qos

    # Nodes
    default_nodes = 1
    if site_config and "defaults" in site_config:
        default_nodes = site_config["defaults"].get("nodes", 1)
    nodes = click.prompt("  Nodes", default=default_nodes, type=int)
    profile["nodes"] = nodes

    # Time limit
    default_time = "30m"
    if site_config and "defaults" in site_config:
        default_time = str(site_config["defaults"].get("time_limit", "30m"))
    time_limit = click.prompt("  Time limit", default=default_time)
    profile["time_limit"] = time_limit

    # Save
    profiles_data[name] = profile
    with open(prism_yaml, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    click.echo(f"\n  Added profile '{name}' to prism.yaml")


# =============================================================================
# Setup command
# =============================================================================


def _run_setup_wizard(name: str | None = None) -> Path:
    """Run the interactive setup wizard.

    Prompts for site selection, username, account, and container runtime.
    Compute defaults (node type, QOS, nodes, time limit) are populated
    automatically from the site's safe defaults — those belong in profiles.

    Returns the path where the site config was saved.
    """
    from prism.dagster.sites import get_site_defaults, list_known_sites
    from prism.dagster.targets import load_user_config, save_site, save_user_config

    console.print("\n[bold]Prism Setup — Site Configuration[/bold]")
    console.print(
        "  These settings are stored in [cyan]~/.prism/[/cyan] and can be "
        "overridden per-project via compute profiles.\n"
    )

    # --- Configure HPC? ---
    configure_hpc = click.confirm(
        "  Configure a remote execution site (HPC)?",
        default=False,
    )

    if not configure_hpc:
        site_name = name or "local"
        site_config: dict[str, Any] = {
            "site": "local",
            "backend": "local",
            "connection": {},
            "defaults": {},
        }
    else:
        # --- HPC site selection ---
        known = list_known_sites()
        hpc_sites = [(k, d) for k, d in known if k != "local"]
        console.print("\n  [bold]Known HPC sites:[/bold]")
        for i, (_key, display) in enumerate(hpc_sites, 1):
            console.print(f"    {i}. {display}")

        site_choices = [str(i) for i in range(1, len(hpc_sites) + 1)]
        site_idx = click.prompt(
            "\n  Select site",
            type=click.Choice(site_choices),
            default="1",
        )
        site_key = hpc_sites[int(site_idx) - 1][0]
        site = get_site_defaults(site_key) or {}

        display = site.get("display_name", site_key)
        hostname = site.get("connection", {}).get("hostname", "")
        console.print(
            f"  Detected: [cyan]{display}[/cyan] ({hostname})\n"
        )

        # --- Connection ---
        username = click.prompt(
            "  Username",
            default=os.environ.get("USER", ""),
        )
        account = click.prompt("  Account/allocation")

        # --- Container runtime ---
        site_runtimes = site.get("container_runtimes", [])
        if len(site_runtimes) > 1:
            console.print("\n  [bold]Container runtime:[/bold]")
            for i, rt in enumerate(site_runtimes, 1):
                console.print(f"    {i}. {rt}")

            rt_choices = [
                str(i) for i in range(1, len(site_runtimes) + 1)
            ]
            rt_idx = click.prompt(
                "  Select runtime",
                type=click.Choice(rt_choices),
                default="1",
            )
            container_runtime = site_runtimes[int(rt_idx) - 1]
        elif site_runtimes:
            container_runtime = site_runtimes[0]
        else:
            container_runtime = site.get(
                "scheduler", {},
            ).get("container_runtime", "docker")

        site_name = name or site_key or "default"
        site_config = {
            "site": site_key,
            "backend": site.get("backend", "slurm"),
            "connection": {
                "hostname": hostname,
                "username": username,
            },
            "account": account,
            "container_runtime": container_runtime,
            "defaults": site.get("safe_defaults", {}),
        }

    # --- Save site and set as default ---
    path = save_site(site_name, site_config)
    user_config = load_user_config()
    user_config["default_site"] = site_name
    save_user_config(user_config)
    console.print(f"\n  [green]✓[/green] Default site: {site_name}")

    return path


@main.command()
@click.argument("name", required=False)
@click.option("--list", "list_flag", is_flag=True, help="List configured sites")
@click.option("--show", "show_name", default=None, help="Show a site's config")
@click.option("--default", "set_default", default=None, help="Set default site")
def setup(
    name: str | None, list_flag: bool,
    show_name: str | None, set_default: str | None,
) -> None:
    """Set up or manage site configurations.

    Configures connection details and container runtime for remote
    execution backends (SLURM). Compute settings (node type, QOS,
    nodes, time limit) are populated from safe site defaults and
    can be customized per-project via ``prism profiles add``.

    Settings are stored at the user level (~/.prism/sites/) and
    referenced by compute profiles in prism.yaml.

    Examples:
        prism setup                    # interactive wizard
        prism setup perlmutter         # configure a named site
        prism setup --list             # list configured sites
        prism setup --show perlmutter  # show a site's config
        prism setup --default local    # change default site
    """
    if set_default:
        from prism.dagster.targets import load_site, load_user_config, save_user_config
        # Validate site exists (or is "local")
        if set_default != "local":
            site_config = load_site(set_default)
            if site_config is None:
                console.print(f"[red]Error:[/red] No configured site '{set_default}'.")
                raise SystemExit(1)
        user_config = load_user_config()
        user_config["default_site"] = set_default
        save_user_config(user_config)
        console.print(f"[green]✓[/green] Default site set to '{set_default}'")
        return

    if show_name:
        from prism.dagster.targets import load_site
        config = load_site(show_name)
        if config is None:
            console.print(f"[red]Error:[/red] No configured site '{show_name}'.")
            raise SystemExit(1)
        console.print(f"[bold]Site: {show_name}[/bold]\n")
        console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))
        return

    if list_flag:
        from prism.dagster.targets import list_sites, load_user_config
        saved = list_sites()
        user_config = load_user_config()
        default = user_config.get("default_site", "")

        console.print("[bold]Configured sites:[/bold]")
        # Always show local
        local_marker = " [green](default)[/green]" if default == "local" else ""
        console.print(f"  - local  (built-in){local_marker}")
        if saved:
            for s in saved:
                marker = " [green](default)[/green]" if s == default else ""
                console.print(f"  - {s}{marker}")
        elif not saved:
            console.print("  [dim](no additional sites configured)[/dim]")
        console.print(
            "\nRun [cyan]prism setup[/cyan] to configure a new site."
        )
        return

    _run_setup_wizard(name)


if __name__ == "__main__":
    main()
