"""Tests for the run-config YAML loader."""

from pathlib import Path

from vigil.cli.defaults import DEFAULT_FIXTURES_PATH, DEFAULT_METRICS_INTERVAL, DEFAULT_WATCHLIST_PATH
from vigil.cli.run_config import DEFAULT_RUN_CONFIG_PATH, RunConfig, load_run_config
from vigil.detect.data.rules_config import DEFAULT_RULES_CONFIG_PATH
from vigil.ingest.certstream import CERTSTREAM_URL


def test_missing_file_returns_hardcoded_defaults():
    config = load_run_config(Path("/nonexistent/config.yml"))
    assert config == RunConfig()
    assert config.source == "certstream"
    assert config.certstream_url == CERTSTREAM_URL
    assert config.fixtures_path == DEFAULT_FIXTURES_PATH
    assert config.watchlist == DEFAULT_WATCHLIST_PATH
    assert config.rules_config == DEFAULT_RULES_CONFIG_PATH
    assert config.skip_wildcards is True
    assert config.detection is False
    assert config.metrics is False
    assert config.metrics_interval == DEFAULT_METRICS_INTERVAL


def test_partial_file_keeps_defaults_for_missing_keys(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text("detection: true\nmetrics_interval: 2.5\n", encoding="utf-8")
    config = load_run_config(path)
    assert config.detection is True
    assert config.metrics_interval == 2.5
    assert config.source == "certstream"
    assert config.skip_wildcards is True


def test_full_file_overrides_every_field(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text(
        """
source: fixtures
certstream_url: ws://example.test/
fixtures_path: fixtures.jsonl
watchlist: my_watchlist.yml
rules_config: my_rules.yml
skip_wildcards: false
detection: true
metrics: true
metrics_interval: 3.0
""",
        encoding="utf-8",
    )
    config = load_run_config(path)
    assert config == RunConfig(
        source="fixtures",
        certstream_url="ws://example.test/",
        fixtures_path=Path("fixtures.jsonl"),
        watchlist=Path("my_watchlist.yml"),
        rules_config=Path("my_rules.yml"),
        skip_wildcards=False,
        detection=True,
        metrics=True,
        metrics_interval=3.0,
    )


def test_default_config_file_matches_hardcoded_defaults():
    """data/config.yml as committed must be a no-op vs. the hardcoded defaults."""
    assert load_run_config(DEFAULT_RUN_CONFIG_PATH) == RunConfig()
