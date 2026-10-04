"""Tests for the Tranco list loader."""

from vigil.detect.data.tranco import load_tranco


def test_load_tranco_reads_domain_column(tmp_path):
    path = tmp_path / "top.csv"
    path.write_text("1,Google.com\n2,alegra.com\n\n", encoding="utf-8")
    assert load_tranco(path) == frozenset({"google.com", "alegra.com"})


def test_load_tranco_missing_file_is_empty(tmp_path):
    assert load_tranco(tmp_path / "missing.csv") == frozenset()
