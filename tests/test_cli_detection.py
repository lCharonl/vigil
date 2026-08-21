"""CLI tests for the --detection flag over the fixture source."""

from typer.testing import CliRunner

from vigil.cli import app

runner = CliRunner()


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
