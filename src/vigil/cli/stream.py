"""The async ingestion loop that prints certificates or detections."""

import asyncio
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from vigil.detect.data.watchlist import load_legitimate_domains
from vigil.detect.families.morphological import numeric_exceptions
from vigil.detect.pipeline import detect_event
from vigil.detect.registry import Rule
from vigil.ingest.base import Source
from vigil.ingest.filters import strip_wildcards
from vigil.reporting.metrics import DetectionMetrics


def _load_digit_exceptions(watchlist: Path) -> frozenset[str]:
    """Digit-run exceptions for M-04, empty if the watchlist is missing."""
    if not watchlist.exists():
        return frozenset()
    return numeric_exceptions(load_legitimate_domains(watchlist))


def _run_stream(
    src: Source,
    skip_wildcards: bool,
    detection: bool,
    digit_exceptions: frozenset[str] = frozenset(),
    rules: frozenset[Rule] | None = None,
    metrics: bool = False,
    metrics_interval: float = 10.0,
) -> None:
    """Drive the ingestion loop, printing certs or detections."""

    async def run() -> None:
        count = 0
        stats = DetectionMetrics() if (detection and metrics) else None
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
                    results = detect_event(cert, digit_exceptions, rules)
                    if stats is not None:
                        # metrics-only mode: count detections, skip per-line output
                        stats.record(len(cert.domains), time.perf_counter() - t0, results)
                        count += len(results)
                    else:
                        for domain, reasons in results:
                            count += 1
                            matched = ",".join(r.rule for r in reasons)
                            typer.echo(
                                f"[{count}] DETECT source={cert.source} "
                                f"serial={cert.serial_number} domain={domain} rules={matched}"
                            )
                else:
                    count += 1
                    typer.echo(
                        f"[{count}] source={cert.source} serial={cert.serial_number} "
                        f"domains={cert.domains}"
                    )
                if stats is not None and time.monotonic() >= next_report:
                    report()
                    next_report += metrics_interval
            if stats is not None:
                report()
        finally:
            if live is not None:
                live.stop()
        unit = "detection(s)" if detection else "certificate(s) processed"
        typer.echo(f"done: {count} {unit}", err=True)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
