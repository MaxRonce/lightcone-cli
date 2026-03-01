"""Shared test fixtures for Prism tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _fake_config(tmp_path, monkeypatch):
    """Ensure a config.yaml exists so the CLI auto-trigger doesn't fire.

    The ``main`` group callback checks for ``~/.prism/config.yaml`` and
    launches the setup wizard when it is missing.  This fixture creates a
    temporary config so that tests which invoke CLI commands are not
    interrupted by the wizard.

    Individual tests that want to exercise the auto-trigger behaviour
    should override ``get_config_path`` themselves.
    """
    config_path = tmp_path / "prism_cfg" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("default_site: fake\n")
    monkeypatch.setattr(
        "prism.dagster.targets.get_config_path", lambda: config_path
    )
