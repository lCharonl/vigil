"""Tranco top-sites list: ranked domains that are never reported."""

import csv
from pathlib import Path


def load_tranco(path: Path | str) -> frozenset[str]:
    """Registrable domains from a Tranco `rank,domain` CSV, empty if the file is missing."""
    path = Path(path)
    if not path.exists():
        return frozenset()
    with path.open(newline="", encoding="utf-8") as f:
        return frozenset(row[1].strip().lower() for row in csv.reader(f) if len(row) >= 2)
