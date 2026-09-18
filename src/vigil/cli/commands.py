"""Typer commands: the `vigil` entry point and the `watch` command."""

import logging
from pathlib import Path

import typer

from vigil.cli.defaults import (
    DEFAULT_FIXTURES_PATH,
    DEFAULT_METRICS_INTERVAL,
    DEFAULT_WATCHLIST_PATH,
)
from vigil.cli.stream import (
    _load_allowlist,
    _load_digit_exceptions,
    _load_terms,
    _load_watched_brands,
    _run_stream,
)
from vigil.detect.data.rules_config import DEFAULT_RULES_CONFIG_PATH, load_enabled_rules
from vigil.detect.registry import Rule
from vigil.ingest.base import Source
from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource
from vigil.ingest.fixtures import FixtureSource

app = typer.Typer(add_completion=False)

logger = logging.getLogger("vigil")


@app.callback()
def main() -> None:
    """Vigil: phishing-infrastructure detection from Certificate Transparency logs."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


@app.command()
def watch(
    source: str = typer.Option("certstream", "--source", help="certstream|fixtures"),
    certstream_url: str = typer.Option(
        CERTSTREAM_URL,
        "--certstream-url",
        help="Websocket URL for --source certstream",
    ),
    watchlist: Path = typer.Option(
        DEFAULT_WATCHLIST_PATH, "--watchlist", help="Path to the watchlist YAML file"
    ),
    rules_config: Path = typer.Option(
        DEFAULT_RULES_CONFIG_PATH, "--rules-config", help="Path to the rule toggles YAML file"
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file for findings (JSONL). Unused until detection is implemented.",
    ),
    fixtures_path: Path = typer.Option(
        DEFAULT_FIXTURES_PATH,
        "--fixtures-path",
        help="Fixture JSONL file to replay when --source fixtures",
    ),
    skip_wildcards: bool = typer.Option(
        True,
        "--skip-wildcards/--no-skip-wildcards",
        help="Drop wildcard SANs from ingested certificates",
    ),
    detection: bool = typer.Option(
        False,
        "--detection/--no-detection",
        help="Run detection modules and print only detections (morphological, referential)",
    ),
    metrics: bool = typer.Option(
        False,
        "--metrics/--no-metrics",
        help="Print live throughput/timing metrics to stderr; hides individual detections",
    ),
    metrics_interval: float = typer.Option(
        DEFAULT_METRICS_INTERVAL, "--metrics-interval", help="Seconds between metrics snapshots"
    ),
) -> None:
    """Stream certificates from SOURCE and display them."""
    if not watchlist.exists():
        logger.warning("watchlist file not found: %s (continuing without it)", watchlist)

    if metrics and not detection:
        logger.warning("--metrics has no effect without --detection")

    if output is not None:
        logger.info(
            "findings output configured at %s (unused: detection is not implemented yet)", output
        )

    src: Source
    if source == "certstream":
        src = CertStreamSource(url=certstream_url)
    elif source == "fixtures":
        src = FixtureSource(fixtures_path)
    else:
        raise typer.BadParameter(f"unknown source: {source!r} (expected certstream|fixtures)")

    digit_exceptions: frozenset[str] = frozenset()
    watched: frozenset[str] = frozenset()
    terms: dict[Rule, frozenset[str]] | None = None
    allowlist: frozenset[str] = frozenset()
    rules: frozenset[Rule] | None = None
    if detection:
        digit_exceptions = _load_digit_exceptions(watchlist)
        watched = _load_watched_brands(watchlist)
        terms = _load_terms()
        allowlist = _load_allowlist(watchlist)
        rules = load_enabled_rules(rules_config)

    _run_stream(
        src,
        skip_wildcards,
        detection,
        digit_exceptions,
        watched,
        terms,
        rules,
        metrics=metrics,
        metrics_interval=metrics_interval,
        allowlist=allowlist,
    )


if __name__ == "__main__":
    app()
