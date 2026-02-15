"""Tests for HPC/remote target configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.remote import (
    create_project_hpc_config,
    list_saved_targets,
    load_target_config,
    merge_permissions_into_settings,
    save_target_config,
)


class TestTargetConfigRoundTrip:
    """Tests for saving and loading target configs."""

    def test_save_then_load(self, targets_dir: Path, sample_config: dict):
        save_target_config("perlmutter", sample_config)
        loaded = load_target_config("perlmutter")
        assert loaded is not None
        assert loaded["auth"]["account"] == "m9999"
        assert loaded["target"]["scheduler"] == "slurm"

    def test_load_nonexistent(self, targets_dir: Path):
        assert load_target_config("nonexistent") is None

    def test_list_empty(self, targets_dir: Path):
        assert list_saved_targets() == []

    def test_list_with_targets(self, targets_dir: Path, sample_config: dict):
        save_target_config("perlmutter", sample_config)
        save_target_config("other", {"target": {"name": "other"}})
        targets = list_saved_targets()
        assert targets == ["other", "perlmutter"]


class TestMergePermissions:
    """Tests for merging target permissions into settings."""

    def test_adds_auto_approve(self):
        settings: dict = {"permissions": {"allow": ["Edit"]}}
        config = {
            "permissions": {
                "auto_approve": ["python", "squeue"],
                "deny": [],
            }
        }
        merge_permissions_into_settings(settings, config)
        allow = settings["permissions"]["allow"]
        assert "Bash(python:*)" in allow
        assert "Bash(squeue:*)" in allow
        assert "Edit" in allow  # preserved

    def test_adds_deny_patterns(self):
        settings: dict = {"permissions": {"allow": []}}
        config = {
            "permissions": {
                "auto_approve": [],
                "deny": ["rm -rf /", "scancel --all"],
            }
        }
        merge_permissions_into_settings(settings, config)
        deny = settings["permissions"]["deny"]
        assert "Bash(rm -rf /)" in deny
        assert "Bash(scancel --all)" in deny

    def test_no_duplicates(self):
        settings: dict = {"permissions": {"allow": ["Bash(python:*)"]}}
        config = {"permissions": {"auto_approve": ["python"], "deny": []}}
        merge_permissions_into_settings(settings, config)
        assert settings["permissions"]["allow"].count("Bash(python:*)") == 1

    def test_creates_permissions_key(self):
        settings: dict = {}
        config = {"permissions": {"auto_approve": ["python"], "deny": []}}
        merge_permissions_into_settings(settings, config)
        assert "permissions" in settings
        assert "Bash(python:*)" in settings["permissions"]["allow"]


class TestCreateProjectHpcConfig:
    """Tests for creating project-level HPC configs."""

    def test_creates_subset(self, sample_config: dict):
        project = create_project_hpc_config(sample_config)
        assert "target" in project
        assert "auth" in project
        assert "compute" in project
        assert "resource_limits" in project
        assert "permissions" not in project

    def test_applies_overrides(self, sample_config: dict):
        overrides = {"resource_limits": {"max_nodes": 8}}
        project = create_project_hpc_config(sample_config, overrides=overrides)
        assert project["resource_limits"]["max_nodes"] == 8
        # Other limits preserved
        assert project["resource_limits"]["max_walltime_minutes"] == 120

    def test_includes_notes(self):
        config = {
            "target": {"name": "test"},
            "auth": {},
            "compute": {},
            "resource_limits": {},
            "notes": "Use debug QOS for development.",
        }
        project = create_project_hpc_config(config)
        assert project["notes"] == "Use debug QOS for development."

    def test_excludes_notes_when_empty(self, sample_config: dict):
        project = create_project_hpc_config(sample_config)
        assert "notes" not in project
