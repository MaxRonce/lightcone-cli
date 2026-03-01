# `prism setup` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `prism remote setup` with a top-level `prism setup` command that auto-triggers on first use, derives constraints automatically from node type, and uses correct Perlmutter defaults.

**Architecture:** The setup wizard writes target configs to `~/.prism/targets/<name>.yaml` (existing location) and tracks the default target in a new `~/.prism/config.yaml`. The `main` click group callback enforces setup before any subcommand. Site defaults in `sites.py` are updated with `node_types` (replacing `partitions`), `qos_options`, and `container_runtimes`.

**Tech Stack:** Python 3.11+, Click, PyYAML, Rich, pytest

---

### Task 1: Update `sites.py` — rename `partitions` to `node_types`, add `qos_options`

**Files:**
- Modify: `src/prism/dagster/sites.py`
- Test: `tests/test_sites.py`

**Step 1: Write the failing tests**

Replace the contents of `tests/test_sites.py` with:

```python
"""Tests for HPC site defaults."""
from __future__ import annotations

from prism.dagster.sites import (
    SITE_DEFAULTS,
    detect_site,
    get_site_defaults,
    list_known_sites,
)


class TestDetectSite:
    def test_exact_match(self):
        assert detect_site("perlmutter") == "perlmutter"

    def test_hostname_match(self):
        assert detect_site("perlmutter.nersc.gov") == "perlmutter"

    def test_partial_match(self):
        assert detect_site("my-perlmutter-target") == "perlmutter"

    def test_case_insensitive(self):
        assert detect_site("Perlmutter") == "perlmutter"
        assert detect_site("PERLMUTTER") == "perlmutter"

    def test_saul_matches_perlmutter(self):
        assert detect_site("saul.nersc.gov") == "perlmutter"

    def test_unknown(self):
        assert detect_site("my-cluster") is None

    def test_empty(self):
        assert detect_site("") is None


class TestGetSiteDefaults:
    def test_perlmutter(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        assert site["backend"] == "slurm"
        assert site["scheduler"]["container_runtime"] == "podman-hpc"
        assert "gpu" in site["node_types"]
        assert site["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_perlmutter_gpu_node_type(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        gpu = site["node_types"]["gpu"]
        assert gpu["constraint"] == "gpu"
        assert "--gpu" in gpu["container_flags"]
        assert "description" in gpu

    def test_perlmutter_gpu_hbm80_node_type(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        gpu80 = site["node_types"]["gpu_hbm80"]
        assert gpu80["constraint"] == "gpu&hbm80g"
        assert "--gpu" in gpu80["container_flags"]

    def test_perlmutter_cpu_node_type(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        cpu = site["node_types"]["cpu"]
        assert cpu["constraint"] == "cpu"
        assert cpu["container_flags"] == []

    def test_perlmutter_qos_options(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        qos = site["qos_options"]
        assert "regular" in qos
        assert "debug" in qos
        assert qos["regular"].get("default") is True

    def test_perlmutter_container_runtimes(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        assert "podman-hpc" in site["container_runtimes"]
        assert "shifter" in site["container_runtimes"]

    def test_unknown(self):
        assert get_site_defaults("nonexistent") is None


class TestListKnownSites:
    def test_returns_all_sites(self):
        sites = list_known_sites()
        keys = [s[0] for s in sites]
        assert "perlmutter" in keys

    def test_has_display_names(self):
        sites = list_known_sites()
        for key, display in sites:
            assert len(display) > 0

    def test_matches_site_defaults(self):
        sites = list_known_sites()
        assert len(sites) == len(SITE_DEFAULTS)


class TestSiteDefaultsSchema:
    """Ensure all site entries have the required fields."""

    def test_all_sites_have_required_fields(self):
        required = {"hostname_patterns", "backend", "connection", "scheduler",
                     "node_types", "qos_options", "container_runtimes",
                     "resource_limits"}
        for key, site in SITE_DEFAULTS.items():
            missing = required - set(site.keys())
            assert not missing, f"Site '{key}' missing fields: {missing}"

    def test_all_sites_have_container_runtime(self):
        for key, site in SITE_DEFAULTS.items():
            assert "container_runtime" in site["scheduler"], \
                f"Site '{key}' missing scheduler.container_runtime"

    def test_all_node_types_have_required_fields(self):
        for key, site in SITE_DEFAULTS.items():
            for nname, ninfo in site["node_types"].items():
                assert "constraint" in ninfo, \
                    f"Site '{key}' node_type '{nname}' missing constraint"
                assert "container_flags" in ninfo, \
                    f"Site '{key}' node_type '{nname}' missing container_flags"
                assert "description" in ninfo, \
                    f"Site '{key}' node_type '{nname}' missing description"

    def test_all_qos_options_have_description(self):
        for key, site in SITE_DEFAULTS.items():
            for qname, qinfo in site["qos_options"].items():
                assert "description" in qinfo, \
                    f"Site '{key}' qos_option '{qname}' missing description"

    def test_exactly_one_default_qos(self):
        for key, site in SITE_DEFAULTS.items():
            defaults = [q for q, info in site["qos_options"].items()
                        if info.get("default")]
            assert len(defaults) == 1, \
                f"Site '{key}' has {len(defaults)} default QOS options (expected 1)"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sites.py -v`
Expected: FAIL — tests reference `node_types`, `qos_options`, `container_runtimes` which don't exist yet.

**Step 3: Update `sites.py`**

Replace the full contents of `src/prism/dagster/sites.py` with:

```python
"""Known HPC site defaults for target configuration.

When ``prism setup`` detects a known site, it auto-populates scheduler
settings with site-specific defaults (node types, QOS options, container
runtimes, etc.).  Users can override any value during the wizard.

To add a new site, append an entry to ``SITE_DEFAULTS``.
"""
from __future__ import annotations

from typing import Any

# Each entry maps a site key to its defaults.  The ``hostname_patterns``
# list is used to auto-detect the site from user-provided hostnames.
SITE_DEFAULTS: dict[str, dict[str, Any]] = {
    "perlmutter": {
        "hostname_patterns": ["perlmutter", "saul"],
        "display_name": "NERSC Perlmutter",
        "backend": "slurm",
        "connection": {
            "hostname": "perlmutter.nersc.gov",
        },
        "scheduler": {
            "container_runtime": "podman-hpc",
        },
        "node_types": {
            "gpu": {
                "description": "GPU (A100 40GB) — 1,536 nodes, 4 GPUs/node",
                "constraint": "gpu",
                "container_flags": ["--gpu"],
            },
            "gpu_hbm80": {
                "description": "GPU (A100 80GB) — 256 nodes, 4 GPUs/node",
                "constraint": "gpu&hbm80g",
                "container_flags": ["--gpu"],
            },
            "cpu": {
                "description": "CPU only — 3,072 nodes, 128 cores/node",
                "constraint": "cpu",
                "container_flags": [],
            },
        },
        "qos_options": {
            "regular": {"description": "Standard priority, max 48h", "default": True},
            "debug": {"description": "Quick tests, max 30min, 8 nodes max"},
            "shared": {"description": "Fractional GPU (1-2 GPUs), max 48h"},
            "preempt": {"description": "0.25x cost, can be preempted after 2h"},
        },
        "container_runtimes": ["podman-hpc", "shifter"],
        "resource_limits": {
            "max_nodes": 4,
            "max_walltime_minutes": 360,
            "max_concurrent_jobs": 8,
            "max_node_hours_per_session": 64,
        },
    },
}


def detect_site(hostname_or_name: str) -> str | None:
    """Detect a known HPC site from a hostname or target name.

    Returns the site key (e.g. ``"perlmutter"``) or ``None`` if no match.
    """
    normalized = hostname_or_name.lower()
    for site_key, site in SITE_DEFAULTS.items():
        if site_key in normalized:
            return site_key
        for pattern in site.get("hostname_patterns", []):
            if pattern in normalized:
                return site_key
    return None


def get_site_defaults(site_key: str) -> dict[str, Any] | None:
    """Return defaults for a known site, or ``None``."""
    return SITE_DEFAULTS.get(site_key)


def list_known_sites() -> list[tuple[str, str]]:
    """Return list of (site_key, display_name) for all known sites."""
    return [
        (key, site.get("display_name", key))
        for key, site in SITE_DEFAULTS.items()
    ]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sites.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/prism/dagster/sites.py tests/test_sites.py
git commit -m "refactor: rename partitions to node_types, add qos_options and container_runtimes to site defaults"
```

---

### Task 2: Add user-level config functions to `targets.py`

**Files:**
- Modify: `src/prism/dagster/targets.py`
- Modify: `tests/test_targets.py`

**Step 1: Write the failing tests**

Append to `tests/test_targets.py`:

```python
from prism.dagster.targets import (
    get_config_path,
    load_user_config,
    save_user_config,
)


class TestUserConfig:
    def test_save_then_load(self, targets_dir):
        # targets_dir fixture already monkeypatches get_targets_dir;
        # we also need to monkeypatch get_config_path to use the same tmp dir.
        pass  # see step 3 for actual fixtures

    def test_load_missing_returns_empty(self, targets_dir, monkeypatch):
        config_path = targets_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        assert load_user_config() == {}

    def test_save_and_load_default_target(self, targets_dir, monkeypatch):
        config_path = targets_dir.parent / "config.yaml"
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        save_user_config({"default_target": "perlmutter"})
        config = load_user_config()
        assert config["default_target"] == "perlmutter"

    def test_config_path_is_in_prism_dir(self):
        path = get_config_path()
        assert path.name == "config.yaml"
        assert ".prism" in str(path)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_targets.py::TestUserConfig -v`
Expected: FAIL — `get_config_path`, `load_user_config`, `save_user_config` don't exist.

**Step 3: Add functions to `targets.py`**

Add the following to `src/prism/dagster/targets.py` after the existing functions:

```python
def get_config_path() -> Path:
    """Return the user-level config file path (~/.prism/config.yaml)."""
    return Path.home() / ".prism" / "config.yaml"


def load_user_config() -> dict[str, Any]:
    """Load the user-level Prism configuration.

    Returns an empty dict if the config file doesn't exist.
    """
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def save_user_config(config: dict[str, Any]) -> Path:
    """Save user-level Prism configuration to ~/.prism/config.yaml.

    Returns the path where it was saved.
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_targets.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/prism/dagster/targets.py tests/test_targets.py
git commit -m "feat: add user-level config (config.yaml) read/write functions to targets module"
```

---

### Task 3: Rewrite the setup wizard in `cli.py`

This is the largest task. Replace the old `_run_target_setup_wizard` and `remote` group with the new `prism setup` command.

**Files:**
- Modify: `src/prism/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
from unittest.mock import patch


class TestSetupCommand:
    """Tests for the prism setup command."""

    def test_setup_help(self, runner: CliRunner):
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0
        assert "execution environment" in result.output.lower() or "Setup" in result.output

    def test_setup_list_empty(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: tmp_path / "targets")
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        result = runner.invoke(main, ["setup", "--list"])
        assert result.exit_code == 0
        assert "No saved targets" in result.output

    def test_setup_list_with_targets(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        targets_dir = tmp_path / "targets"
        targets_dir.mkdir()
        (targets_dir / "perlmutter.yaml").write_text("name: perlmutter\n")
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: targets_dir)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("default_target: perlmutter\n")
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: config_path)
        result = runner.invoke(main, ["setup", "--list"])
        assert result.exit_code == 0
        assert "perlmutter" in result.output

    def test_setup_show(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        targets_dir = tmp_path / "targets"
        targets_dir.mkdir()
        (targets_dir / "perlmutter.yaml").write_text("name: perlmutter\nbackend: slurm\n")
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: targets_dir)
        result = runner.invoke(main, ["setup", "--show", "perlmutter"])
        assert result.exit_code == 0
        assert "slurm" in result.output

    def test_setup_show_nonexistent(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: tmp_path / "targets")
        result = runner.invoke(main, ["setup", "--show", "nonexistent"])
        assert result.exit_code == 1

    def test_setup_wizard_known_site(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Test the wizard flow with a known site (perlmutter)."""
        targets_dir = tmp_path / "targets"
        targets_dir.mkdir(parents=True)
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: targets_dir)
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")

        # Simulate wizard input: site=1(perlmutter), username=testuser,
        # account=m1234, node_type=1(gpu), qos=1(regular),
        # runtime=1(podman-hpc), max_nodes=4, max_walltime=360,
        # max_concurrent=8, target_name=perlmutter
        input_lines = "1\ntestuser\nm1234\n1\n1\n1\n4\n360\n8\nperlmutter\n"
        result = runner.invoke(main, ["setup"], input=input_lines)
        assert result.exit_code == 0
        assert "Saved target" in result.output
        assert (targets_dir / "perlmutter.yaml").exists()
        assert (tmp_path / "config.yaml").exists()

        # Verify constraint was auto-derived
        import yaml
        target = yaml.safe_load((targets_dir / "perlmutter.yaml").read_text())
        assert target["scheduler"]["constraint"] == "gpu"
        assert target["scheduler"]["node_type"] == "gpu"

    def test_setup_wizard_sets_default(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Test that wizard sets the default_target in config.yaml."""
        targets_dir = tmp_path / "targets"
        targets_dir.mkdir(parents=True)
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: targets_dir)
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")

        input_lines = "1\ntestuser\nm1234\n1\n1\n1\n4\n360\n8\nmypm\n"
        result = runner.invoke(main, ["setup"], input=input_lines)
        assert result.exit_code == 0

        import yaml
        config = yaml.safe_load((tmp_path / "config.yaml").read_text())
        assert config["default_target"] == "mypm"


class TestAutoTrigger:
    """Tests for the auto-trigger setup check."""

    def test_init_without_setup_triggers_wizard(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """Commands should trigger setup when no config exists."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        # The init command should be blocked by the auto-trigger
        result = runner.invoke(main, ["init", str(tmp_path / "proj"), "--no-git", "--no-venv"])
        # Should see the setup prompt, not the init output
        assert "Prism Setup" in result.output or "No execution environment" in result.output

    def test_setup_command_skips_auto_trigger(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        """prism setup itself should not trigger the auto-trigger."""
        monkeypatch.setattr("prism.dagster.targets.get_config_path",
                            lambda: tmp_path / "config.yaml")
        monkeypatch.setattr("prism.dagster.targets.get_targets_dir",
                            lambda: tmp_path / "targets")
        result = runner.invoke(main, ["setup", "--list"])
        # Should show list output, not setup wizard
        assert "No saved targets" in result.output

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
        config_path.write_text("default_target: perlmutter\n")
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py::TestSetupCommand -v`
Expected: FAIL — `setup` command doesn't exist yet.

**Step 3: Rewrite the CLI**

In `src/prism/cli.py`, make the following changes:

**3a.** Replace the `main` group definition (lines 43-47) with an auto-trigger callback:

```python
@click.group()
@click.version_option()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Prism - ASP-compliant Agentic Layer CLI."""
    # Auto-trigger: ensure prism setup has been run before any command.
    # Skip for: setup command itself, --help, --version.
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
```

**3b.** Add the new `setup` command and wizard (replace everything from line 827 `# Remote target commands` to end of file):

```python
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
```

**3c.** Remove the entire `remote` group and its commands (`remote`, `remote_setup`, `remote_show`, `remote_edit`) — lines 832-1071 in the original file. These are replaced by the `setup` command above.

**3d.** Update the reference in the `init` command. Replace the call to `_run_target_setup_wizard(target)` at line 144 with `_run_setup_wizard(target)`.

**Step 4: Run all tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All PASS (including new tests, and existing tests that don't reference `remote`).

Run: `pytest tests/ -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/prism/cli.py tests/test_cli.py
git commit -m "feat: add prism setup command with auto-trigger, remove prism remote group"
```

---

### Task 4: Update existing test references and run full suite

**Files:**
- Modify: `tests/test_cli.py` (update `TestHelpOption.test_remote_help`)

**Step 1: Remove or update the old remote help test**

In `tests/test_cli.py`, remove the `test_remote_help` method from `TestHelpOption` class:

```python
# DELETE this test:
def test_remote_help(self, runner: CliRunner):
    result = runner.invoke(main, ["remote", "--help"])
    assert result.exit_code == 0
```

Add a `test_setup_help` to replace it:

```python
def test_setup_help(self, runner: CliRunner):
    result = runner.invoke(main, ["setup", "--help"])
    assert result.exit_code == 0
```

**Step 2: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All PASS.

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: update help tests for setup command, remove remote references"
```

---

### Task 5: Final verification and cleanup

**Step 1: Run linting**

Run: `ruff check src/ tests/`
Expected: Clean (no errors).

**Step 2: Run type checking (if mypy works)**

Run: `mypy src/prism/cli.py src/prism/dagster/sites.py src/prism/dagster/targets.py`
Expected: Clean or only pre-existing issues.

**Step 3: Run the full test suite one more time**

Run: `pytest tests/ -v`
Expected: All PASS.

**Step 4: Manual smoke test**

Run: `prism setup --list`
Expected: Shows saved targets (or "No saved targets") and known sites.

Run: `prism setup --help`
Expected: Shows help text for the setup command.

**Step 5: Final commit if any cleanup was needed**

```bash
git add -A && git commit -m "chore: cleanup after prism setup implementation"
```
