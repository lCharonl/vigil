"""Validate the generated data/watchlist.yml."""

from pathlib import Path

import pytest
import yaml

WATCHLIST = Path(__file__).resolve().parent.parent / "data" / "watchlist.yml"

SECTORS = {"banking", "health", "insurance", "it_services"}
REGIONS = {"us", "eu", "global"}
TIERS = {"core", "extended"}
MAX_ENTRIES = 10_000


@pytest.fixture(scope="module")
def brands() -> list[dict]:
    data = yaml.safe_load(WATCHLIST.read_text(encoding="utf-8"))
    return data["brands"]


def test_watchlist_parses_and_is_non_empty(brands: list[dict]) -> None:
    assert isinstance(brands, list)
    assert len(brands) > 0


def test_within_cap(brands: list[dict]) -> None:
    assert len(brands) <= MAX_ENTRIES


def test_entry_schema(brands: list[dict]) -> None:
    for entry in brands:
        assert set(entry) == {"name", "sector", "region", "tier", "legitimate_domains"}
        assert entry["sector"] in SECTORS
        assert entry["region"] in REGIONS
        assert entry["tier"] in TIERS
        assert isinstance(entry["legitimate_domains"], list)
        assert entry["legitimate_domains"], f"{entry['name']} has no legitimate domain"


def test_names_unique(brands: list[dict]) -> None:
    names = [e["name"] for e in brands]
    assert len(names) == len(set(names))


def test_domains_unique_across_brands(brands: list[dict]) -> None:
    # a domain must not appear under two different brands
    seen: dict[str, str] = {}
    for entry in brands:
        for domain in entry["legitimate_domains"]:
            assert domain not in seen, f"{domain} shared by {seen.get(domain)} and {entry['name']}"
            seen[domain] = entry["name"]


def test_core_tier_present(brands: list[dict]) -> None:
    # a few well-known core brands must be present with the right sector
    core = {e["name"]: e for e in brands if e["tier"] == "core"}
    for name, sector in [
        ("paypal", "banking"),
        ("chase", "banking"),
        ("axa", "insurance"),
        ("microsoft", "it_services"),
        ("unitedhealthcare", "health"),
    ]:
        assert name in core, f"expected core brand missing: {name}"
        assert core[name]["sector"] == sector
