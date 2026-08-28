"""CLI tests for the --detection flag and the interactive menu."""

import json
from pathlib import Path

from typer.testing import CliRunner

from vigil.cli import MenuConfig, app
from vigil.detect.rules import Rule
from vigil.ingest.fixtures import FixtureSource

runner = CliRunner()


def _write_fixture(path: Path, domains_per_cert: list[list[str]]) -> None:
    """Write a minimal certstream JSONL fixture, one cert per domain list."""
    with path.open("w", encoding="utf-8") as f:
        for i, domains in enumerate(domains_per_cert):
            message = {
                "message_type": "certificate_update",
                "data": {
                    "update_type": "X509LogEntry",
                    "leaf_cert": {
                        "serial_number": f"{i:04d}",
                        "signature_algorithm": "sha256WithRSAEncryption",
                        "not_before": 1731000000,
                        "not_after": 1738776000,
                        "all_domains": domains,
                    },
                    "source": {"name": "test"},
                },
            }
            f.write(json.dumps(message) + "\n")


def _detection_fixture(tmp_path: Path) -> Path:
    # one M-01 hit (3 hyphens), one M-03 hit (5 labels)
    path = tmp_path / "certs.jsonl"
    _write_fixture(path, [["secure-login-verify-my.example.com"], ["a.b.c.example.com"]])
    return path


def test_default_view_prints_certs_not_detections():
    result = runner.invoke(app, ["watch", "--source", "fixtures"])
    assert result.exit_code == 0
    assert "domains=[" in result.stdout
    assert "DETECT" not in result.stdout


def test_detection_view_prints_only_detections():
    result = runner.invoke(app, ["watch", "--source", "fixtures", "--detection"])
    assert result.exit_code == 0
    assert "domains=[" not in result.stdout
    for line in result.stdout.splitlines():
        if line.startswith("["):
            assert "DETECT" in line


def _menu_config(
    fixture: Path,
    detection: bool,
    rules: frozenset[Rule] | None,
    metrics: bool = False,) -> MenuConfig:
    return MenuConfig(
        src=FixtureSource(fixture),
        source_label=f"fixtures ({fixture})",
        detection=detection,
        rules=rules,
        metrics=metrics
    )


def test_menu_without_detection_prints_certs(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    monkeypatch.setattr("vigil.cli._prompt_menu", lambda: _menu_config(fixture, False, None))
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "domains=[" in result.stdout
    assert "DETECT" not in result.stdout


def _all_output(result) -> str:
    """stdout plus stderr, whichever the runner captured separately."""
    try:
        return result.stdout + result.stderr
    except (ValueError, AttributeError):
        return result.stdout


def test_menu_with_detection_all_rules(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    monkeypatch.setattr(
        "vigil.cli._prompt_menu", lambda: _menu_config(fixture, True, frozenset(Rule))
    )
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "domains=[" not in result.stdout
    assert "rules=M-01" in result.stdout
    assert "rules=M-03" in result.stdout


def test_menu_with_rule_subset_restricts_detections(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    monkeypatch.setattr(
        "vigil.cli._prompt_menu", lambda: _menu_config(fixture, True, frozenset({Rule.M_03}))
    )
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    detect_lines = [line for line in result.stdout.splitlines() if "DETECT" in line]
    assert len(detect_lines) == 1
    assert "rules=M-03" in detect_lines[0]
    assert "domain=a.b.c.example.com" in detect_lines[0]


def test_menu_recap_shows_configuration(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    monkeypatch.setattr(
        "vigil.cli._prompt_menu", lambda: _menu_config(fixture, True, frozenset({Rule.M_01}))
    )
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "run configuration" in result.stdout
    assert "M-01" in result.stdout


def test_watch_metrics_flag_emits_block():
    result = runner.invoke(
        app, ["watch", "--source", "fixtures", "--detection", "--metrics"]
    )
    assert result.exit_code == 0
    output = _all_output(result)
    assert "detection metrics" in output
    assert "analysis/domain" in output
    assert "detection metrics" not in result.stdout  # metrics stay off stdout


def test_watch_metrics_suppresses_detections():
    result = runner.invoke(
        app, ["watch", "--source", "fixtures", "--detection", "--metrics"]
    )
    assert result.exit_code == 0
    assert "DETECT" not in result.stdout
    assert "detection metrics" in _all_output(result)


def test_watch_without_metrics_flag_emits_no_block():
    result = runner.invoke(app, ["watch", "--source", "fixtures", "--detection"])
    assert result.exit_code == 0
    assert "detection metrics" not in _all_output(result)


def test_menu_metrics_recap(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    monkeypatch.setattr(
        "vigil.cli._prompt_menu",
        lambda: _menu_config(fixture, True, frozenset({Rule.M_01}), metrics=True),
    )
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "metrics    on" in result.stdout
    assert "detection metrics" in _all_output(result)
    assert "DETECT" not in result.stdout