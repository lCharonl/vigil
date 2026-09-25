"""Shared-hosting / PaaS suffixes whose subdomains are never a tenant's own brand."""

from pathlib import Path

import yaml

DEFAULT_SHARED_HOSTING_PATH = Path("data/shared_hosting_suffixes.yml")


def load_shared_hosting_suffixes(
    path: Path | str = DEFAULT_SHARED_HOSTING_PATH,
) -> frozenset[str]:
    """Suffixes to suppress like an allowlisted domain, empty if the file is missing."""
    path = Path(path)
    if not path.exists():
        return frozenset()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(s.strip().lower() for s in data.get("suffixes") or [])
