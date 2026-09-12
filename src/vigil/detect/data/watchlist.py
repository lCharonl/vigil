"""Minimal watchlist reader shared by detection."""

from pathlib import Path

import yaml


def load_legitimate_domains(path: Path | str) -> list[str]:
    """Return every legitimate_domain listed in the watchlist YAML."""
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    domains: list[str] = []
    for brand in data.get("brands") or []:
        domains.extend(brand.get("legitimate_domains") or [])
    return domains
