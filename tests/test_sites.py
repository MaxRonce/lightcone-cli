"""Tests for HPC site defaults."""
from __future__ import annotations

from prism.dagster.sites import (
    SITE_DEFAULTS,
    detect_site,
    get_site_defaults,
    get_site_guidance,
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
        """saul is an alias hostname for perlmutter."""
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
        assert "gpu" in site["partitions"]
        assert site["connection"]["hostname"] == "perlmutter.nersc.gov"

    def test_perlmutter_gpu_partition(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        gpu = site["partitions"]["gpu"]
        assert gpu["constraint"] == "gpu"
        assert "--gpu" in gpu["container_flags"]

    def test_perlmutter_cpu_partition(self):
        site = get_site_defaults("perlmutter")
        assert site is not None
        cpu = site["partitions"]["cpu"]
        assert cpu["constraint"] == "cpu"
        assert cpu["container_flags"] == []

    def test_unknown(self):
        assert get_site_defaults("nonexistent") is None


class TestGetSiteGuidance:
    def test_perlmutter_has_guidance(self):
        guidance = get_site_guidance("perlmutter")
        assert guidance is not None
        assert "Perlmutter" in guidance
        assert "podman-hpc" in guidance

    def test_unknown(self):
        assert get_site_guidance("nonexistent") is None


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
                     "partitions", "resource_limits"}
        for key, site in SITE_DEFAULTS.items():
            missing = required - set(site.keys())
            assert not missing, f"Site '{key}' missing fields: {missing}"

    def test_all_sites_have_container_runtime(self):
        for key, site in SITE_DEFAULTS.items():
            assert "container_runtime" in site["scheduler"], \
                f"Site '{key}' missing scheduler.container_runtime"

    def test_all_partitions_have_constraint(self):
        for key, site in SITE_DEFAULTS.items():
            for pname, pinfo in site["partitions"].items():
                assert "constraint" in pinfo, \
                    f"Site '{key}' partition '{pname}' missing constraint"
                assert "container_flags" in pinfo, \
                    f"Site '{key}' partition '{pname}' missing container_flags"
