#!/usr/bin/env python3
"""Tails a vigil results JSONL file and pretty-prints each new line.

Usage:
    python3 scripts/tail_results.py data/output/results.jsonl
    python3 scripts/tail_results.py --from-start data/output/results.jsonl
"""

import argparse
import json
import os
import time
from collections.abc import Iterator
from pathlib import Path

from rich.console import Console
from rich.text import Text

POLL_INTERVAL_SECONDS = 0.5


def follow(path: Path, from_start: bool, poll_interval: float) -> Iterator[str]:
    """Yields each new complete line appended to path, blocking as needed."""
    while not path.exists():
        time.sleep(poll_interval)
    with path.open(encoding="utf-8") as f:
        if not from_start:
            f.seek(0, os.SEEK_END)
        buffer = ""
        while True:
            chunk = f.read()
            if not chunk:
                time.sleep(poll_interval)
                continue
            buffer += chunk
            *complete, buffer = buffer.split("\n")
            yield from (line for line in complete if line.strip())


def render(record: dict, console: Console) -> None:
    """Prints one result record with vigil's former console color scheme."""
    timestamp = record.get("detected_at", "")
    source = record.get("source", "")
    serial = record.get("serial_number", "")
    if "rules" in record:
        families = ",".join(record.get("families", []))
        rules = ",".join(record.get("rules", []))
        text = Text.assemble(
            (f"{timestamp} ", "dim"),
            ("DETECT ", "bold red"),
            ("source=", "dim"),
            (f"{source} ", "white"),
            ("serial=", "dim"),
            (f"{serial} ", "white"),
            ("domain=", "dim"),
            (f"{record.get('domain', '')} ", "bold yellow"),
            ("families=", "dim"),
            (f"{families} ", "cyan"),
            ("rules=", "dim"),
            (rules, "magenta"),
        )
    else:
        text = Text.assemble(
            (f"{timestamp} ", "dim"),
            ("source=", "dim"),
            (f"{source} ", "white"),
            ("serial=", "dim"),
            (f"{serial} ", "white"),
            ("domains=", "dim"),
            (str(record.get("domains", [])), "dim"),
        )
    console.print(text, soft_wrap=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSONL results file to tail")
    parser.add_argument(
        "--from-start",
        action="store_true",
        help="Replay the whole file first, not just new lines",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=POLL_INTERVAL_SECONDS,
        help="Seconds between polls",
    )
    args = parser.parse_args()

    console = Console()
    try:
        for line in follow(args.path, args.from_start, args.poll_interval):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            render(record, console)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
