"""Interactive menu: collects the run configuration before streaming starts."""

from dataclasses import dataclass
from pathlib import Path

import questionary
import typer
from questionary import Choice
from rich.console import Console
from rich.panel import Panel

from vigil.cli.defaults import DEFAULT_FIXTURES_PATH
from vigil.detect.data import thresholds
from vigil.detect.pipeline import IMPLEMENTED_FAMILIES
from vigil.detect.registry import RULE_FAMILY, Rule
from vigil.ingest.base import Source
from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource
from vigil.ingest.fixtures import FixtureSource

console = Console()

RULE_LABELS: dict[Rule, str] = {
    Rule.M_01: f"{thresholds.MIN_HYPHENS}+ hyphens in hostname",
    Rule.M_02: f"registrable domain > {thresholds.MAX_REGISTRABLE_LENGTH} chars",
    Rule.M_03: f"{thresholds.MIN_LABELS}+ labels in hostname",
    Rule.M_04: f"{thresholds.MIN_CONSECUTIVE_DIGITS}+ consecutive digits",
}


@dataclass
class MenuConfig:
    """Choices collected by the interactive menu."""

    src: Source
    source_label: str
    detection: bool
    rules: frozenset[Rule] | None = None
    metrics: bool = False


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
