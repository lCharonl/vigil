"""Command-line entry point for Vigil."""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import questionary
import typer
from questionary import Choice
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from vigil.detect import config
from vigil.detect.metrics import DetectionMetrics
from vigil.detect.morphological import numeric_exceptions
from vigil.detect.pipeline import IMPLEMENTED_FAMILIES, detect_event
from vigil.detect.rules import RULE_FAMILY, Rule
from vigil.detect.watchlist import load_legitimate_domains
from vigil.ingest.base import Source
from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource
from vigil.ingest.filters import strip_wildcards
from vigil.ingest.fixtures import FixtureSource

app = typer.Typer(add_completion=False)

DEFAULT_FIXTURES_PATH = Path("tests/fixtures/certs.jsonl")
DEFAULT_WATCHLIST_PATH = Path("data/watchlist.yml")

logger = logging.getLogger("vigil")
console = Console()

RULE_LABELS: dict[Rule, str] = {
    Rule.M_01: f"{config.MIN_HYPHENS}+ hyphens in hostname",
    Rule.M_02: f"registrable domain > {config.MAX_REGISTRABLE_LENGTH} chars",
    Rule.M_03: f"{config.MIN_LABELS}+ labels in hostname",
    Rule.M_04: f"{config.MIN_CONSECUTIVE_DIGITS}+ consecutive digits",
}


@dataclass
class MenuConfig:
    """Choices collected by the interactive menu."""

    src: Source
    source_label: str
    detection: bool
    rules: frozenset[Rule] | None = None
    metrics: bool = False


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


def _ask(prompt: questionary.Question):
    """Run a questionary prompt, exiting cleanly on ctrl-c."""
    answer = prompt.ask()
    if answer is None:
        console.print("[yellow]cancelled[/]")
        raise typer.Exit(code=0)
    return answer


def _prompt_menu() -> MenuConfig:
    """Collect source, detection and enabled rules interactively."""
    console.print(
        Panel.fit(
            "[bold cyan]Vigil[/] — phishing-infrastructure detection\n"
            "[dim]arrows: move · space: toggle · enter: confirm · ctrl-c: quit[/]",
            border_style="cyan",
        )
    )

    source = _ask(
        questionary.select(
            "Source:",
            choices=[
                Choice("certstream (live)", "certstream"),
                Choice("fixtures (replay)", "fixtures"),
            ],
        )
    )
    src: Source
    if source == "certstream":
        url = _ask(questionary.text("CertStream URL:", default=CERTSTREAM_URL))
        src = CertStreamSource(url=url)
        source_label = f"certstream ({url})"
    else:
        fixtures_path = _ask(
            questionary.path("Fixtures path:", default=str(DEFAULT_FIXTURES_PATH))
        )
        src = FixtureSource(Path(fixtures_path))
        source_label = f"fixtures ({fixtures_path})"

    detection = _ask(questionary.confirm("Enable detection?", default=False))
    rules: frozenset[Rule] | None = None
    if detection:
        families = _ask(
            questionary.checkbox(
                "Detection families:",
                choices=[Choice(f.value, f, checked=True) for f in IMPLEMENTED_FAMILIES],
            )
        )
        selected: set[Rule] = set()
        for family in families:
            family_rules = [r for r in Rule if RULE_FAMILY[r] is family]
            picked = _ask(
                questionary.checkbox(
                    f"{family.value} rules:",
                    choices=[
                        Choice(f"{r.value} — {RULE_LABELS.get(r, r.value)}", r, checked=True)
                        for r in family_rules
                    ],
                )
            )
            selected.update(picked)
        rules = frozenset(selected)
        if not rules:
            console.print("[yellow]no rules selected: detection will match nothing[/]")

    metrics = False
    if detection:
        metrics = _ask(
            questionary.confirm(
                "Metrics only (hide individual detections)?", default=True
            )
        )

    return MenuConfig(
        src=src,
        source_label=source_label,
        detection=detection,
        rules=rules,
        metrics=metrics,
    )


def _print_recap(menu: MenuConfig) -> None:
    """Show the chosen configuration in a bordered panel."""
    lines = [f"source     {menu.source_label}"]
    if menu.detection:
        enabled = sorted(r.value for r in (menu.rules or frozenset()))
        lines.append("detection  on")
        lines.append(f"rules      {', '.join(enabled) if enabled else 'none'}")
        lines.append(f"metrics    {'on' if menu.metrics else 'off'}")
    else:
        lines.append("detection  off")
    console.print(Panel("\n".join(lines), title="run configuration", border_style="green"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Vigil: phishing-infrastructure detection from Certificate Transparency logs."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    if ctx.invoked_subcommand is not None:
        return
    menu = _prompt_menu()
    _print_recap(menu)
    digit_exceptions: frozenset[str] = frozenset()
    if menu.detection:
        if not DEFAULT_WATCHLIST_PATH.exists():
            logger.warning(
                "watchlist file not found: %s (continuing without it)", DEFAULT_WATCHLIST_PATH
            )
        digit_exceptions = _load_digit_exceptions(DEFAULT_WATCHLIST_PATH)
    _run_stream(
        menu.src, True, menu.detection, digit_exceptions, menu.rules, menu.metrics
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
    metrics: bool = typer.Option(
        False,
        "--metrics/--no-metrics",
        help="Print live throughput/timing metrics to stderr; hides individual detections",
    ),
    metrics_interval: float = typer.Option(
        10.0, "--metrics-interval", help="Seconds between metrics snapshots"
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
    if detection:
        digit_exceptions = _load_digit_exceptions(watchlist)

    _run_stream(
        src,
        skip_wildcards,
        detection,
        digit_exceptions,
        metrics=metrics,
        metrics_interval=metrics_interval,
    )


if __name__ == "__main__":
    app()
