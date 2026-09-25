"""The async ingestion loop that prints certificates or detections."""

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from vigil.cli.defaults import DEFAULT_METRICS_INTERVAL
from vigil.detect.data.shared_hosting import load_shared_hosting_suffixes
from vigil.detect.data.terms import DEFAULT_TERMS_PATH, load_terms
from vigil.detect.data.watchlist import load_brand_names, load_legitimate_domains
from vigil.detect.families.morphological import numeric_exceptions
from vigil.detect.pipeline import detect_event
from vigil.detect.registry import Rule
from vigil.ingest.base import Source
from vigil.ingest.filters import strip_wildcards
from vigil.output.jsonl import JSONLWriter
from vigil.reporting.metrics import DetectionMetrics


def _load_digit_exceptions(watchlist: Path) -> frozenset[str]:
    """Digit-run exceptions for M-04, empty if the watchlist is missing."""
    if not watchlist.exists():
        return frozenset()
    return numeric_exceptions(load_legitimate_domains(watchlist))


def _load_watched_brands(watchlist: Path) -> frozenset[str]:
    """Watched brand names for referential rules, empty if the watchlist is missing."""
    if not watchlist.exists():
        return frozenset()
    return load_brand_names(watchlist)


def _load_allowlist(watchlist: Path) -> frozenset[str]:
    """Known-legitimate domains and shared-hosting suffixes that suppress detection."""
    legit = frozenset(load_legitimate_domains(watchlist)) if watchlist.exists() else frozenset()
    return legit | load_shared_hosting_suffixes()


def _load_terms(path: Path = DEFAULT_TERMS_PATH) -> dict[Rule, frozenset[str]]:
    """Lexical terms for referential/lexical rules, empty if the file is missing."""
    if not path.exists():
        return {}
    return load_terms(path)


def _run_stream(
    src: Source,
    skip_wildcards: bool,
    detection: bool,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
    metrics: bool = False,
    metrics_interval: float = DEFAULT_METRICS_INTERVAL,
    allowlist: frozenset[str] = frozenset(),
    output: Path | None = None,
) -> None:
    """Drive the ingestion loop, writing certs or detections as JSONL."""

    async def run() -> None:
        count = 0
        stats = DetectionMetrics() if (detection and metrics) else None
        writer = JSONLWriter(output)
        err_console = Console(stderr=True)
        # one in-place panel on a real terminal, plain reprints otherwise
        live = (
            Live(console=err_console, auto_refresh=False)
            if stats is not None and err_console.is_terminal
            else None
        )

        def report() -> None:
            block = stats.snapshot()
            if live is not None:
                live.update(
                    Panel(block, title="detection metrics", border_style="cyan"),
                    refresh=True,
                )
            else:
                typer.echo(block, err=True)

        next_report = time.monotonic() + metrics_interval
        try:
            if live is not None:
                live.start()
            async for cert in src.stream():
                if skip_wildcards:
                    filtered = strip_wildcards(cert)
                    if filtered is None:
                        continue
                    cert = filtered
                if detection:
                    t0 = time.perf_counter()
                    results = detect_event(
                        cert, digit_exceptions, watched, terms, rules=rules, allowlist=allowlist
                    )
                    if stats is not None:
                        # metrics-only mode: count detections, skip per-line output
                        stats.record(len(cert.domains), time.perf_counter() - t0, results)
                        count += len(results)
                    else:
                        for domain, reasons in results:
                            count += 1
                            families = list(dict.fromkeys(r.family for r in reasons))
                            rule_ids = [r.rule for r in reasons]
                            writer.write(
                                {
                                    "detected_at": datetime.now(UTC).isoformat(),
                                    "source": cert.source,
                                    "serial_number": cert.serial_number,
                                    "domain": domain,
                                    "families": families,
                                    "rules": rule_ids,
                                }
                            )
                else:
                    count += 1
                    writer.write(
                        {
                            "detected_at": datetime.now(UTC).isoformat(),
                            "source": cert.source,
                            "serial_number": cert.serial_number,
                            "domains": cert.domains,
                        }
                    )
                if stats is not None and time.monotonic() >= next_report:
                    report()
                    next_report += metrics_interval
            if stats is not None:
                report()
        finally:
            if live is not None:
                live.stop()
            writer.close()
        unit = "detection(s)" if detection else "certificate(s) processed"
        err_console.print(f"done: {count} {unit}", style="bold green", highlight=False)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
