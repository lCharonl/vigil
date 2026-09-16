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


def load_brand_names(path: Path | str, tiers: frozenset[str] | None = None) -> frozenset[str]:
    """Return every watchlist brand name, lowercased, optionally filtered by tier."""
    path = Path(path)
    if not path.exists():
        return frozenset()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names: set[str] = set()
    for brand in data.get("brands") or []:
        if tiers is not None and brand.get("tier") not in tiers:
            continue
        name = brand.get("name")
        if name:
            names.add(name.strip().lower())
    return frozenset(names)
