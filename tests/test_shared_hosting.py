"""Tests for the shared-hosting suffix loader."""

from pathlib import Path

from vigil.detect.data.shared_hosting import load_shared_hosting_suffixes


def test_loads_configured_suffixes():
    suffixes = load_shared_hosting_suffixes()
    assert "azure-api.net" in suffixes
    assert "meraki.direct" in suffixes


def test_missing_file_returns_empty():
    assert load_shared_hosting_suffixes(Path("/nonexistent/suffixes.yml")) == frozenset()


def test_custom_file(tmp_path):
    path = tmp_path / "suffixes.yml"
    path.write_text("suffixes:\n  - Example.PaaS.net\n", encoding="utf-8")
    assert load_shared_hosting_suffixes(path) == frozenset({"example.paas.net"})
