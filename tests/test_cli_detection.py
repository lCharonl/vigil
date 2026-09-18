"""CLI tests for the --detection flag and rule-toggle config."""

import json
from pathlib import Path

from typer.testing import CliRunner

from vigil.cli import app

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
    # both certs are reinforced by a watched brand (chase, in the default
    # watchlist) so morphological alone isn't suppressed as too weak
    path = tmp_path / "certs.jsonl"
    _write_fixture(
        path,
        [
            ["chase.secure-login-verify-my.example.com"],  # M-01 + L-04 + R-01
            ["chase.a.b.c.example.com"],  # M-03 + R-01
        ],
    )
    return path


def _write_rules_config(tmp_path: Path, enabled: dict[str, bool]) -> Path:
    path = tmp_path / "rules.yml"
    body = "\n".join(f"  {rule}: {'true' if on else 'false'}" for rule, on in enabled.items())
    path.write_text(f"rules:\n{body}\n", encoding="utf-8")
    return path


def _all_output(result) -> str:
    """stdout plus stderr, whichever the runner captured separately."""
    try:
        return result.stdout + result.stderr
    except (ValueError, AttributeError):
        return result.stdout


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


def test_detection_with_all_rules_enabled(tmp_path):
    fixture = _detection_fixture(tmp_path)
    result = runner.invoke(
        app, ["watch", "--source", "fixtures", "--fixtures-path", str(fixture), "--detection"]
    )
    assert result.exit_code == 0
    assert "rules=R-01,L-04,M-01" in result.stdout
    assert "rules=R-01,M-03" in result.stdout


def test_rules_config_restricts_detections(tmp_path):
    fixture = _detection_fixture(tmp_path)
    all_rules = ["R-01", "R-02", "R-03", "R-04", "L-01", "L-02", "L-03", "L-04", "M-01", "M-02", "M-03", "M-04"]
    rules_config = _write_rules_config(tmp_path, {r: r == "M-03" for r in all_rules})
    result = runner.invoke(
        app,
        [
            "watch",
            "--source",
            "fixtures",
            "--fixtures-path",
            str(fixture),
            "--detection",
            "--rules-config",
            str(rules_config),
        ],
    )
    assert result.exit_code == 0
    detect_lines = [line for line in result.stdout.splitlines() if "DETECT" in line]
    # both fixture domains have 4+ labels, so both match M-03; nothing else is enabled
    assert len(detect_lines) == 2
    assert all("rules=M-03" in line for line in detect_lines)


def test_rules_config_missing_file_enables_everything(tmp_path):
    fixture = _detection_fixture(tmp_path)
    result = runner.invoke(
        app,
        [
            "watch",
            "--source",
            "fixtures",
            "--fixtures-path",
            str(fixture),
            "--detection",
            "--rules-config",
            str(tmp_path / "missing.yml"),
        ],
    )
    assert result.exit_code == 0
    assert "rules=R-01,L-04,M-01" in result.stdout


def test_config_file_drives_detection_and_metrics_without_flags(tmp_path):
    fixture = _detection_fixture(tmp_path)
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        f"""
source: fixtures
fixtures_path: {fixture}
detection: true
metrics: true
metrics_interval: 2.5
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["watch", "--config", str(config_path)])
    assert result.exit_code == 0
    # metrics=true hides individual DETECT lines, so check the metrics block instead
    assert "DETECT" not in result.stdout
    assert "detection metrics" in _all_output(result)
    assert "analysis/domain" in _all_output(result)


def test_explicit_flag_overrides_config_file(tmp_path):
    fixture = _detection_fixture(tmp_path)
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        f"""
source: fixtures
fixtures_path: {fixture}
detection: true
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app, ["watch", "--config", str(config_path), "--no-detection"]
    )
    assert result.exit_code == 0
    assert "DETECT" not in result.stdout
    assert "domains=[" in result.stdout


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


def test_watch_watchlist_path_is_used(monkeypatch, tmp_path):
    fixture = _detection_fixture(tmp_path)
    custom_watchlist = tmp_path / "custom_watchlist.yml"
    custom_watchlist.write_text("brands: []\n", encoding="utf-8")
    seen_paths: list[Path] = []
    monkeypatch.setattr(
        "vigil.cli.commands._load_watched_brands",
        lambda path: seen_paths.append(path) or frozenset(),
    )
    result = runner.invoke(
        app,
        [
            "watch",
            "--source",
            "fixtures",
            "--fixtures-path",
            str(fixture),
            "--detection",
            "--watchlist",
            str(custom_watchlist),
        ],
    )
    assert result.exit_code == 0
    assert seen_paths == [custom_watchlist]


def test_skip_wildcards_false_keeps_wildcard_domain(tmp_path):
    path = tmp_path / "certs.jsonl"
    _write_fixture(path, [["*.example.com"]])
    result = runner.invoke(
        app,
        [
            "watch",
            "--source",
            "fixtures",
            "--fixtures-path",
            str(path),
            "--no-skip-wildcards",
        ],
    )
    assert result.exit_code == 0
    assert "*.example.com" in result.stdout


def test_skip_wildcards_true_drops_wildcard_only_cert(tmp_path):
    path = tmp_path / "certs.jsonl"
    _write_fixture(path, [["*.example.com"]])
    result = runner.invoke(
        app, ["watch", "--source", "fixtures", "--fixtures-path", str(path)]
    )
    assert result.exit_code == 0
    assert "*.example.com" not in result.stdout
