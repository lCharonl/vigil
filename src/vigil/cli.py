"""Command-line entry point for Vigil."""

import asyncio
import logging
from pathlib import Path

import typer

from vigil.detect.morphological import numeric_exceptions
from vigil.detect.pipeline import detect_event
from vigil.detect.watchlist import load_legitimate_domains
from vigil.ingest.base import Source
from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource
from vigil.ingest.filters import strip_wildcards
from vigil.ingest.fixtures import FixtureSource

app = typer.Typer(add_completion=False, no_args_is_help=True)

DEFAULT_FIXTURES_PATH = Path("tests/fixtures/certs.jsonl")

logger = logging.getLogger("vigil")


@app.callback()
def main() -> None:
    """Vigil: phishing-infrastructure detection from Certificate Transparency logs."""


@app.command()
def watch(
    source: str = typer.Option("certstream", "--source", help="certstream|fixtures"),
    certstream_url: str = typer.Option(
        CERTSTREAM_URL,
        "--certstream-url",
        help="Websocket URL for --source certstream",
    ),
    watchlist: Path = typer.Option(
        Path("data/watchlist.yml"), "--watchlist", help="Path to the watchlist YAML file"
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
        help="Run detection modules and print only detections (morphological only for now)",
    ),
) -> None:
    """Stream certificates from SOURCE and display them.

    Detection is not implemented yet (see vigil.detect): this command exercises the
    ingestion pipeline end to end and prints every CertEvent it receives.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if not watchlist.exists():
        logger.warning("watchlist file not found: %s (continuing without it)", watchlist)

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
    if detection and watchlist.exists():
        digit_exceptions = numeric_exceptions(load_legitimate_domains(watchlist))

    async def run() -> None:
        count = 0
        async for cert in src.stream():
            if skip_wildcards:
                filtered = strip_wildcards(cert)
                if filtered is None:
                    continue
                cert = filtered
            if detection:
                for domain, reasons in detect_event(cert, digit_exceptions):
                    count += 1
                    rules = ",".join(r.rule for r in reasons)
                    typer.echo(
                        f"[{count}] DETECT source={cert.source} "
                        f"serial={cert.serial_number} domain={domain} rules={rules}"
                    )
            else:
                count += 1
                typer.echo(
                    f"[{count}] source={cert.source} serial={cert.serial_number} "
                    f"domains={cert.domains}"
                )
        unit = "detection(s)" if detection else "certificate(s) processed"
        typer.echo(f"done: {count} {unit}", err=True)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    app()
