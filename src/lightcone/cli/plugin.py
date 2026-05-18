"""Agent bundle discovery for skills/hooks shipped with lightcone-cli.

Kept deliberately leaf (no imports from :mod:`lightcone.cli.commands` or :mod:`lightcone.eval`)
so it can be used by both the CLI and the eval harness without introducing an import cycle.
"""

from __future__ import annotations

from pathlib import Path


def get_agent_bundle_source_dir(agent: str) -> Path | None:
    """Find the lightcone bundle source directory for *agent*.

    Looks for bundle files in:

    1. Bundled location (installed package): ``lightcone/cli/<agent>/lightcone/``
    2. Development location (repo): ``<agent>/lightcone/`` relative to repo root
    """
    if "/" in agent or "\\" in agent or agent in {"", ".", ".."}:
        raise ValueError(f"Invalid agent bundle name: {agent!r}")

    import lightcone.cli

    package_dir = Path(lightcone.cli.__file__).parent
    bundled_bundle = package_dir / agent / "lightcone"
    if bundled_bundle.exists():
        return bundled_bundle

    # Try development location (running from repo)
    # package_dir == <repo>/src/lightcone/cli → parents[2] == <repo>
    repo_root = package_dir.parents[2]
    dev_bundle = repo_root / agent / "lightcone"
    if dev_bundle.exists():
        return dev_bundle

    return None


def get_plugin_source_dir() -> Path | None:
    """Find the lightcone Claude plugin source directory.

    Backward-compatible wrapper for callers that still use the historical
    Claude-specific name.
    """
    return get_agent_bundle_source_dir("claude")
